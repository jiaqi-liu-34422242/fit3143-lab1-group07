# Task 2 — Final MPI Simulation Architecture

> **Owner:** Jiaqi — Task 2  
> **Status:** Final collective-protocol design for submission and presentation. This document specifies a proposed simulator; it does not claim that code has been implemented.

## 1. Architecture decision

The simulation is designed for a cluster of multi-core machines and uses both distributed-memory and shared-memory parallelism:

- **MPI** represents charging nodes and base stations as distributed processes and carries all inter-process messages.
- **OpenMP** accelerates each base station's regional candidate search within a multi-core host.
- Only the master thread calls MPI, following `MPI_THREAD_FUNNELED`.

The logical communication architecture contains three planes:

| Plane | Participants | Logical topology | Purpose |
|---|---|---|---|
| Local sensing | charging node ↔ charging node | non-periodic 2-D logical mesh | Confirm whether the source node and all valid immediate neighbours are heavily utilised. |
| Regional reporting | charging nodes ↔ assigned base | forest of regional stars | Send status and alerts to the base responsible for the source region. |
| Global control | base ↔ base | logically complete control overlay | Share alerts and select the globally closest available candidate. |

The logical topology does not prescribe the physical placement of EV stations or the physical wiring of the cluster.

## 2. Baseline parameters

| Parameter | Baseline value | Meaning |
|---|---:|---|
| `R × C` | `8 × 8` | Non-periodic logical node mesh. |
| `N = RC` | 64 | Charging-node MPI ranks. |
| `S` | 4 | Base-station MPI ranks. |
| `P` | 16 | Charging ports stored locally by each node. |
| `threshold` | user-configurable | Heavy-utilisation threshold; the condition is `utilisation > threshold`. |
| `f` | 1 round/s | Baseline update frequency. |
| `C_host` | 32 cores | Usable physical cores per host. |
| `B` | 1 Gbps | External cluster-link rate. |
| `A` | `0 ≤ A ≤ N` | Active alerts in one round. |

## 3. Software components

| Component | Important state | Responsibility |
|---|---|---|
| `SimulationConfig` | `R`, `C`, `S`, `P`, threshold, rounds, frequency | Validate and distribute immutable configuration. |
| `ChargingPort` | port id, free/busy status | Represent one local charging port; it is not an MPI rank. |
| `ChargingNode` | node id, logical coordinate, `ports[P]`, utilisation, neighbour ranks, assigned base rank | Update ports, report status, query neighbours and produce an alert decision. |
| `BaseStation` | base id, owned region, regional status cache, event log | Receive and log regional data, share alerts, compute candidates and issue redirects. |
| `Topology` | mesh dimensions, Cartesian neighbours, regional ownership | Create the non-periodic node mesh and assign each node to one base. |
| `DistancePolicy` | distance function and tie-break rule | Make nearest-candidate selection deterministic. |

![Required static structure diagram](figures/task2-class-diagram.svg)

### Why a charging port is not an MPI rank

Ports belong to one charging station and share its local state. Modelling each port as a rank would increase the process count from `N+S` to approximately `NP+S` without adding useful distributed communication. A `ChargingNode` therefore owns a local `ports[P]` array and reports aggregate counts and utilisation.

## 4. MPI ranks and communicators

World ranks are assigned as follows:

```text
base-station ranks:  0 ... S-1
charging-node ranks: S ... S+N-1
total MPI ranks:     N+S
```

The communicator hierarchy is:

```text
MPI_COMM_WORLD
├── base_comm: all S base-station ranks
└── node_comm: all N charging-node ranks
    └── cart_comm: non-periodic R × C Cartesian topology
```

Initialisation proceeds as follows:

1. Call `MPI_Init_thread` requesting `MPI_THREAD_FUNNELED` and verify the provided support level.
2. Rank 0 validates `SimulationConfig`; all ranks receive it through `MPI_Bcast` on `MPI_COMM_WORLD`.
3. `MPI_Comm_split` separates base and node roles into `base_comm` and `node_comm`.
4. Node ranks call `MPI_Cart_create(node_comm, ..., periods={false,false}, reorder=false, ...)` to create `cart_comm`.
5. `MPI_Cart_shift` identifies valid north, south, west and east neighbour ranks. Boundaries return `MPI_PROC_NULL` and create no wrap-around neighbour.
6. `node_comm` may be collectively freed by its node members after `cart_comm` has been created successfully.

`reorder=false` keeps the Cartesian rank compatible with the configured node indexing. If reordering were enabled, explicit rank translation would be required before node-to-base communication.

| Communicator | Operations and data |
|---|---|
| `MPI_COMM_WORLD` | configuration `MPI_Bcast`; direct `STATUS_REPORT`, `ALERT_DECISION` and `REDIRECT`; round-end `MPI_Barrier`. |
| `cart_comm` | `QUERY` and `NEIGHBOUR_REPLY` between valid logical neighbours. |
| `base_comm` | alert-count `MPI_Allgather`; alert-batch `MPI_Allgatherv`; candidate-vector `MPI_Allreduce(MPI_MINLOC)`. |
| `node_comm` | Intermediate communicator used to construct `cart_comm`; no steady-state message. |

![Communicator hierarchy and cluster deployment](figures/task2-communicators-deployment.svg)

## 5. Business messages and MPI mapping

Payload sizes are explicit analytical assumptions excluding MPI and network headers.

| Business/control data | Sender → receiver | Trigger/frequency | Payload | MPI operation | Communicator |
|---|---|---|---:|---|---|
| `CONFIG` | coordinator base 0 → all ranks | Once at startup | 64 B | `MPI_Bcast` | `MPI_COMM_WORLD` |
| `STATUS_REPORT` | node → assigned base | Once per round | 32 B | `MPI_Isend`, `MPI_Irecv`, `MPI_Waitall` | `MPI_COMM_WORLD` |
| `QUERY` | node → each valid neighbour | One intent record per edge direction per round; `active=true` only when source is heavy | 16 B | `MPI_Isend`, `MPI_Irecv`, `MPI_Waitall` | `cart_comm` |
| `NEIGHBOUR_REPLY` | neighbour → active requester | For each active query | 24 B | `MPI_Isend`, `MPI_Irecv`, `MPI_Waitall` | `cart_comm` |
| `ALERT_DECISION` | heavy node → assigned base | Once per heavy node after neighbour evaluation | 32 B | `MPI_Isend`, `MPI_Irecv`, `MPI_Waitall` | `MPI_COMM_WORLD` |
| Alert count | every base ↔ every base | Once per round | 4 B per base | `MPI_Allgather` | `base_comm` |
| Alert batch | every base ↔ every base | Once per round, including zero-count participation | 32 B per active alert | `MPI_Allgatherv` | `base_comm` |
| Candidate vector | every base ↔ every base | Once when global alert count is non-zero | 16 B per alert per base | vector `MPI_Allreduce(MPI_MINLOC)` | `base_comm` |
| `REDIRECT` | alert-owning base → source node | After global winner selection | 24 B | `MPI_Send`, `MPI_Recv` | `MPI_COMM_WORLD` |
| Round synchronisation | all ranks | Once after each complete round | 0 B | `MPI_Barrier` | `MPI_COMM_WORLD` |

The names `CONFIG`, `STATUS_REPORT` and `ALERT_DECISION` describe business data. `MPI_Bcast`, `MPI_Allgather` and `MPI_Allreduce` describe how MPI transports or combines that data. `MPI_Waitall` is a completion operation rather than a business message.

## 6. One simulation round

![Required communication sequence diagram](figures/task2-sequence-diagram.svg)

### Phase 1 — port update and regional status

1. Each node updates its local `ports[P]` and calculates `utilisation = busyPorts/P`.
2. Each base posts one non-blocking receive for every assigned node.
3. Every node sends one `STATUS_REPORT` to its assigned base.
4. The base completes all receives with `MPI_Waitall`, updates its regional cache and logs the records.
5. The status records identify the `H_s` heavy nodes in region `s`.

### Phase 2 — deadlock-safe neighbour query

Conditional messages require a known completion rule. Each node therefore sends one fixed query-intent record to every valid logical neighbour:

```text
QUERY.active = localUtilisation > threshold
```

Only `active=true` is a business-level query and triggers a reply. The fixed intent exchange allows each node to post a known number of receives:

1. Post one `MPI_Irecv` for each valid neighbour.
2. Send one query-intent record to each valid neighbour with `MPI_Isend`.
3. Call `MPI_Waitall` for all intent records.
4. A heavy requester posts one reply receive for each valid neighbour.
5. Every neighbour that received `active=true` sends `NEIGHBOUR_REPLY`.
6. The requester completes all replies with `MPI_Waitall` and checks their `roundId`.

The baseline assumes reliable MPI processes. A stale round identifier produces an incomplete assessment and therefore no active alert. Process-failure timeout handling is future work.

### Phase 3 — finite regional alert phase

The base knows `H_s` from the completed status phase. Every heavy node sends exactly one `ALERT_DECISION`:

```text
active = self is heavy
         AND every valid neighbour reply is current
         AND every valid neighbour is heavy
```

- `active=true` is the specification's actual `ALERT`.
- `active=false` explicitly completes the heavy node's decision without raising an alert.

The base posts exactly `H_s` receives and calls `MPI_Waitall`. This is safer than treating an unsuccessful `MPI_Iprobe` as proof that no later alert will arrive.

### Phase 4 — batched collective alert exchange

Every base participates once per round, including bases with zero local alerts:

1. `MPI_Allgather` collects one `localAlertCount` from each base.
2. Each base computes identical receive counts and displacement arrays.
3. `MPI_Allgatherv` exchanges the variable-length regional alert batches.
4. Every base sorts the resulting alert list by `(roundId, sourceNodeId)`.

This batching prevents independently received alerts from triggering collectives in different orders.

### Phase 5 — regional OpenMP search and global reduction

Every base has the same ordered list of `A` alerts. For each alert, a base searches only its regional cache.

An eligible candidate must have:

```text
freePorts > 0
utilisation <= threshold
current STATUS_REPORT data
```

The logical Manhattan distance is:

```text
d = abs(sourceRow - candidateRow)
  + abs(sourceColumn - candidateColumn)
```

Each base uses four OpenMP threads to scan disjoint portions of its regional cache. Threads produce thread-local candidates and merge them deterministically. No worker thread calls MPI.

For each alert, the base contributes a pair:

```text
(distance, nodeId)
```

If no regional candidate exists, it contributes:

```text
(INT_MAX, INT_MAX)
```

All bases call one vector `MPI_Allreduce` with `MPI_MINLOC`. The operation is element-wise across the `A` pairs, so one collective chooses a winner for every alert. Smaller distance wins; on equal distance, the smaller node id wins.

All bases can consistently skip the vector reduction only when the alert count obtained from `MPI_Allgather` is zero.

### Phase 6 — redirect and synchronisation

The base that owns each source node sends `REDIRECT` containing the selected node id, logical distance and availability status. The source performs a blocking receive because it requires the result to finish its alert workflow.

All ranks enter one `MPI_Barrier` after the complete round. The barrier does not replace `MPI_Waitall`; every non-blocking request must already be complete before its buffer is reused.

## 7. Deadlock and collective-correctness rules

1. Post known non-blocking receives before matching sends.
2. Complete every `MPI_Isend` and `MPI_Irecv` with `MPI_Wait`, `MPI_Waitall` or an equivalent completion routine.
3. Do not reuse a non-blocking send buffer before completion.
4. Use distinct message tags and include `roundId` in point-to-point payloads.
5. Every heavy node sends one positive or negative alert decision, giving the base an exact expected receive count.
6. Every base calls `Allgather` and `Allgatherv` exactly once per round and in the same order, including zero-count bases.
7. All bases derive the same total alert count and sorted alert order before vector reduction.
8. If `A>0`, every base calls the same `Allreduce` with the same vector length and datatype.
9. OpenMP workers never call MPI; the master thread performs collectives after the shared-memory search completes.
10. The round barrier is used once, not after every message.

## 8. Machine and core allocation

Let `t_node` be cores used by one node rank and `t_base` the number of OpenMP threads/cores used by one base rank:

```text
machines_min = ceil((N t_node + S t_base) / C_host)
```

For the baseline:

```text
t_node = 1
t_base = 4

total cores = 64(1) + 4(4) = 80
machines_min = ceil(80/32) = 3
```

The selected mapping deliberately uses four hosts, one per region:

| Host | MPI ranks | Active cores | Responsibility |
|---|---|---:|---|
| 0 | base 0 + 16 node ranks | 20 | top-left `4 × 4` tile |
| 1 | base 1 + 16 node ranks | 20 | top-right `4 × 4` tile |
| 2 | base 2 + 16 node ranks | 20 | bottom-left `4 × 4` tile |
| 3 | base 3 + 16 node ranks | 20 | bottom-right `4 × 4` tile |

Three machines are the packed mathematical minimum. Four machines are the selected locality-aware deployment: it keeps node-to-base communication within a host, reduces cross-host mesh traffic, aligns one host with one region and avoids oversubscription. Each host has 12 spare cores for MPI progress, operating-system work and growth.

## 9. Required external bandwidth

For the `8 × 8` mesh:

```text
E_mesh = 8(7) + 8(7) = 112 undirected edges
```

Four `4 × 4` tiles create 16 cross-host logical edges: eight across the vertical split and eight across the horizontal split.

Let the worst case have all nodes heavy and `A=N=64` active alerts.

### Cross-host query/reply traffic

```text
D_neighbour
= 2 E_cross (L_query + L_reply)
= 2(16)(16 + 24)
= 1,280 B/round
```

### Alert-count Allgather logical volume

```text
D_count
= S(S-1)L_count
= 4(3)(4)
= 48 B/round
```

### Alert-batch Allgatherv logical volume

```text
D_alertBatch
= A(S-1)L_alert
= 64(3)(32)
= 6,144 B/round
```

### Candidate-vector Allreduce estimate

Assuming recursive doubling and one full candidate vector per stage:

```text
D_candidate
= S log2(S) A L_candidate
= 4(2)(64)(16)
= 8,192 B/round
```

The resulting aggregate external payload estimate is:

```text
D_external
= 1,280 + 48 + 6,144 + 8,192
= 15,664 B/round
```

With a stated 25% protocol and modelling margin:

```text
BW_required = 1.25 × 8 × f × D_external
```

At `f=1 round/s`:

```text
BW_required
= 156,640 bit/s
= 0.15664 Mbps
```

At `f=10 rounds/s`:

```text
BW_required = 1.5664 Mbps
```

This is an aggregate offered-payload estimate, not measured per-link throughput. `STATUS_REPORT`, `ALERT_DECISION` and `REDIRECT` remain intra-host under the selected mapping and are excluded from external traffic. Actual MPI startup, framing, collective algorithms, switch contention and per-host NIC load require measurement. Nevertheless, the entire stated baseline aggregate remains far below the available 1 Gbps link rate.

## 10. Task 2 conclusion

The architecture represents every charging station and base as an MPI process while keeping charging ports as local state. A non-periodic Cartesian communicator provides bounded neighbour communication, regional stars provide direct status and alert reporting, and a base-only communicator batches global coordination safely. Count collection, variable-size alert exchange and one vector `MINLOC` reduction give every base a consistent global result without per-alert collective ordering hazards. OpenMP accelerates regional candidate search while `MPI_THREAD_FUNNELED` keeps MPI calls on the master thread. The four-host baseline uses 80 active cores and requires an estimated `0.15664 Mbps` of aggregate external bandwidth at one round per second under the stated worst-case assumptions.

