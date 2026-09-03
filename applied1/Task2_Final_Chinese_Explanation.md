# Task 2 最终设计思路讲解

## 1. 我们最终做了什么选择

最终方案保留原来的三层逻辑架构：

1. charging node 之间仍然是 non-periodic 2-D logical mesh；
2. charging node 到 assigned base 仍然是 regional star；
3. bases 之间仍然是 logically complete control overlay。

改变的不是业务架构，而是 MPI 的具体实现方法。最终版本只使用 Applied Week 5 明确讲过的 MPI API，不再依赖：

```text
MPI_Cart_create
MPI_Cart_shift
MPI_Comm_split
MPI_Allgatherv
MPI_MINLOC
MPI_Init_thread
```

这使得报告和 Q&A 更容易解释，同时仍然能够得到全局正确的 redirect 结果。

## 2. 为什么不用 Cartesian API 也不会破坏 mesh

2-D logical mesh 是“哪些节点互为逻辑邻居”的设计，不是必须使用某个 MPI 函数。

假设 base ranks 是 `0 ... S-1`，node ranks 是 `S ... S+N-1`：

```text
nodeIndex = worldRank - S
row       = nodeIndex / C
column    = nodeIndex % C
```

然后通过边界判断得到 north、south、west、east。corner 有两个邻居，edge 有三个，interior 有四个，没有 wrap-around。

因此，用 rank arithmetic 和用 `MPI_Cart_shift` 得到的是相同的逻辑关系。我们只是选择了教程范围内、更直接的实现。

## 3. 为什么统一使用 MPI_COMM_WORLD

程序提前知道 rank 的角色和编号：

```text
0 ... S-1       = bases
S ... S+N-1     = charging nodes
```

因此 base 可以直接向另一个 base rank 发消息，node 也可以直接向 assigned base 或 neighbour rank 发消息。不同业务消息用不同 tag 区分。

虽然 communicator 是 `MPI_COMM_WORLD`，但这不代表所有 ranks 都接收所有消息。point-to-point 消息仍然只发生在指定 sender 和 receiver 之间，所以三层业务架构没有变化。

## 4. 每一轮的完整逻辑

### 第一步：端口更新与状态报告

每个 charging node 更新本地 `ports[P]`，计算 utilisation，然后发送 `STATUS_REPORT` 给 assigned base。

base 知道自己管理多少节点，所以可以提前为每个 regional node 发布一个 `MPI_Irecv`，最后通过 `MPI_Waitall` 得到完整区域快照。

base 从 status 中知道本区域哪些节点超过 threshold，假设一共有 `H_s` 个 heavy nodes。

### 第二步：邻居查询

如果只有 heavy nodes 才发送 QUERY，receiver 不知道自己这一轮会不会收到消息，直接 `Waitall` 可能永远等不到。

最终设计让每个节点给所有有效邻居发送一个很小的 QUERY record：

```text
active = utilisation > threshold
```

- `active=true` 才是业务意义上的真正 QUERY；
- `active=false` 只是帮助邻居完成这一轮通信；
- receiver 知道每轮固定从每个邻居收到一个 record，因此不会无限等待。

随后，收到 active QUERY 的邻居发送 `NEIGHBOUR_REPLY`。heavy requester 已经知道自己向几个邻居发出了 active query，所以可以发布相同数量的 `MPI_Irecv`，最后调用 `MPI_Waitall`。

### 第三步：alert decision

真正困难的地方不是发送 ALERT，而是 base 怎么知道这一轮不会再有新的 ALERT。

因为 base 已经从 `STATUS_REPORT` 知道有 `H_s` 个 heavy nodes，所以每个 heavy node 都必须返回一个 `ALERT_DECISION`：

```text
active=true  → 自己和所有有效邻居都超过 threshold
active=false → 不满足 alert 条件，或者回复数据 stale
```

这样 base 固定等待 `H_s` 个 decision。收到全部 decision 后，base 才进入 base-to-base 阶段。

`active=true` 的 decision 就是 specification 中真正的 ALERT；false decision 只是阶段完成信息，不会产生 redirect。

## 5. bases 如何交换不同数量的 alerts

我们不再使用没有在 Applied 05 讲过的 `MPI_Allgatherv`，而是用两阶段 point-to-point exchange。

### 阶段一：交换 alert counts

每个 base 向其他 `S-1` 个 bases 发送 `localAlertCount`：

```text
先发布 S-1 个 MPI_Irecv
再执行 S-1 个 MPI_Isend
最后 MPI_Waitall
```

完成后，每个 base 都知道其他 base 将发送多少 alerts，可以准确分配 buffer。

### 阶段二：交换 alert batches

每个 base 根据刚才收到的 count 发布不同大小的 `MPI_Irecv`，然后把自己的 alert array 发给其他 bases。

point-to-point 的 `count` 可以不同，所以不需要 `MPI_Allgatherv`。

完成后，每个 base 都拥有相同的 global alert list，并按 `(roundId, sourceNodeId)` 排序。

## 6. 如何不用 MINLOC 选择全局最近站点

对于每一个 alert，每个 base 只搜索自己的 regional cache，得到一个 regional candidate：

```text
candidate = {
    alertId,
    available,
    distance,
    nodeId
}
```

距离使用 logical Manhattan distance：

```text
d = |sourceRow-candidateRow|
  + |sourceColumn-candidateColumn|
```

然后，每个 base 把 candidate 发给拥有该 alert source 的 owner base。

owner base 收到其他 `S-1` 个 candidates，加上自己的 candidate，然后本地比较：

1. available 优先；
2. distance 更小优先；
3. 距离相同时 nodeId 更小优先。

这与 `MPI_MINLOC` 的业务结果相同，但只用了教程中的 `MPI_Isend`、`MPI_Irecv` 和 `MPI_Waitall`。

## 7. 为什么不会 deadlock

最终设计遵循几个固定规则：

1. 已知通信双方时，先发布 `MPI_Irecv`，再调用 `MPI_Isend`；
2. 所有 non-blocking request 最终都调用 `MPI_Wait` 或 `MPI_Waitall`；
3. send buffer 在 request 完成前不复用；
4. 每类消息使用不同 tag；
5. payload 包含 `roundId`，防止相邻轮次混淆；
6. variable-size batch 总是先交换 count；
7. 每个 heavy node 都返回一个 alert decision，所以 base 知道什么时候完成；
8. 每轮只在全部业务完成后使用一次 `MPI_Barrier`，最后一轮的 barrier 同时完成最终同步。

## 8. 为什么选择四台机器

最终 baseline 是 pure MPI：

```text
64 node ranks + 4 base ranks = 68 ranks/cores
```

每台 32 cores 时，数学下界是：

```text
ceil(68/32) = 3 machines
```

但最终选择四台，每台负责一个 `4 × 4` region：

```text
16 node ranks + 1 base rank = 17 active cores/host
```

原因不是三台不能运行，而是四台可以让：

- node 到 assigned base 的消息留在同一台机器；
- 大部分 neighbour communication 留在本地；
- 只有 region boundary 和 base-to-base 消息使用外部网络；
- 部署结构与四个 region 对齐，更容易分析和展示。

## 9. 新带宽结果如何得到

四个 `4 × 4` regions 之间有 16 条 cross-host mesh edges。

最坏情况下邻居查询与回复：

```text
2×16×(16+24) = 1,280 B/round
```

base alert-count exchange：

```text
4×3×4 = 48 B/round
```

64 个 alerts 被发送给其他三个 bases：

```text
64×3×32 = 6,144 B/round
```

每个 alert 从其他三个 bases 收到 candidate：

```text
64×3×16 = 3,072 B/round
```

所以总 external aggregate payload：

```text
1,280 + 48 + 6,144 + 3,072
= 10,544 B/round
```

加入明确声明的 25% margin：

```text
BW = 1.25 × 8 × f × 10,544
```

当 `f=1`：

```text
BW = 105,440 bit/s = 0.10544 Mbps
```

当 `f=10`：

```text
BW = 1.0544 Mbps
```

这是 aggregate offered-load estimate，不是某一条物理链路的实测吞吐。但因为整个 aggregate 都远低于 1 Gbps，所以 baseline 下带宽足够。

## 10. 展示时最重要的说法

可以用下面这段作为 Task 2 的核心总结：

> We preserve the logical mesh, regional stars and complete base-control overlay, but implement them only with MPI operations introduced in Applied Week 5. Logical neighbours are calculated from ranks. Neighbour and regional communication use non-blocking point-to-point operations. Bases first exchange alert counts, then variable-size alert batches, and finally send regional candidates to the alert-owning base for deterministic local minimum selection. This avoids Cartesian, Allgatherv and MINLOC APIs without changing the required system behaviour.

如果老师问“为什么不用 collective”，回答：

> The number of bases is deliberately small. Pairwise batched communication is therefore manageable, remains consistent with the logically complete base overlay, supports variable message sizes using only taught APIs, and is easier to schedule safely in this assessment model.
