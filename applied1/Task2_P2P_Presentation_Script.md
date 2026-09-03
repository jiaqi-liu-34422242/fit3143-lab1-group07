# Task 2 Presentation Script — Hybrid MPI/OpenMP with Point-to-Point Protocol

**Target duration:** about 6.5–7 minutes.  
**Speaker:** Jiaqi.  
**Language:** English, matching the slides.

## Required slide wording updates before presenting

The current `Task2_P2P_Presentation.pptx` was produced before the confirmed OpenMP decision. Make these factual substitutions so that the visible slides and this script agree:

| Slide | Replace | With |
|---|---|---|
| 1 | “pure MPI” and “point-to-point only” | “hybrid MPI/OpenMP” and “point-to-point operational protocol; `MPI_Bcast` and `MPI_Barrier` only for setup/synchronisation” |
| 2 | “OpenMP is not required” | “Each base rank uses four OpenMP threads for its local regional-candidate search.” |
| 2 | “all traffic point-to-point” | “All operational traffic is point-to-point; configuration and round synchronisation use the two shown collectives.” |
| 3 | `68 active cores`, `17 active / 32` | `80 active cores`, `20 active / 32`; add “4 OpenMP threads” beside each base. |
| 5 | “nine rules” | “ten rules”; add the `MPI_THREAD_FUNNELED` rule to the right panel. |
| 8 | `MPI_Init` under Used; `MPI_Init_thread` under Not used | `MPI_Init_thread (FUNNELED)` under Used; remove it from Not used. |
| 9 | `68 active cores` | `80 active cores`.

The message types, point-to-point exchange protocol and bandwidth result do **not** change. OpenMP only accelerates local candidate search inside a base process.

---

## Slide 1 — Task 2: Architecture Design (20 seconds)

> Good morning. I will present Task 2, our architecture for the distributed EV charging navigation system.  
> 
> Our final design is a hybrid MPI and OpenMP simulation. The operational protocol is point-to-point: charging nodes communicate with logical neighbours and their assigned base, while bases coordinate through explicitly designed point-to-point exchanges. We use `MPI_Bcast` once for configuration and `MPI_Barrier` once at the end of each round.

Transition: *First, I will explain how the architecture separates the three different communication needs.*

## Slide 2 — Architecture decision (55 seconds)

> We use one MPI rank for each charging station and one MPI rank for each base station. There are three communication planes.  
> 
> The first is local sensing. A charging node exchanges load information only with its logical mesh neighbours. The second is regional reporting: each node reports directly to its assigned base, giving a regional star. The third is global control: bases exchange only the information needed to find a suitable station when an alert occurs.  
> 
> The mesh is logical rather than a claim that physical charging stations form a perfect grid. We compute the neighbour relation using rank arithmetic, so we do not need Cartesian-topology helper APIs.  
> 
> For hybrid parallelism, node ranks are single-threaded. Each base rank uses four OpenMP threads to search its own regional status cache. The search is local shared-memory work. After it finishes, the master thread alone performs MPI communication. This is the `MPI_THREAD_FUNNELED` model.

Transition: *Next is the concrete rank allocation and physical deployment.*

## Slide 3 — Rank layout and cluster deployment (55 seconds)

> We use one flat `MPI_COMM_WORLD`. Ranks zero to S minus one are bases, and ranks S to S plus N minus one are charging nodes.  
> 
> For a node rank, we subtract S to obtain `nodeIndex`. Then integer division by the column count gives the logical row, and modulo gives the logical column. Boundary checks identify north, south, east and west neighbours. This reproduces a non-periodic two-dimensional mesh without `MPI_Cart_create` or `MPI_Cart_shift`.  
> 
> Our baseline has 64 nodes and 4 bases. We map each 4-by-4 region to one 32-core host. Each host runs 16 node ranks and one base rank with four OpenMP threads: 20 active cores per host, or 80 active cores in total.  
> 
> This mapping keeps status reports, alert decisions and redirects inside the same host. The external network is therefore mainly used for mesh edges crossing regions and for base-to-base coordination.

Transition: *Now I will show the software objects represented by these processes.*

## Slide 4 — Static software structure (45 seconds)

> This is our static structure diagram. `SimulationConfig` holds the configurable parameters, including the threshold and mesh dimensions. `Topology` computes logical neighbours and regional ownership, while `DistancePolicy` makes nearest-station selection deterministic using Manhattan distance and node ID as a tie-breaker.  
> 
> A `ChargingNode` has ports, utilisation, one assigned base and up to four neighbour ranks. Importantly, `ChargingPort` is a local object inside its charging node. It is not an MPI rank.  
> 
> A `BaseStation` owns a regional cache and event log. It receives reports, exchanges alert information with other bases, searches its local cache using OpenMP, and sends the final redirect.

Transition: *The next diagram shows exactly what happens in one simulation round.*

## Slide 5 — Communication sequence for one round (70 seconds)

> At startup, rank zero broadcasts the common configuration once. During each round, every charging node updates its local ports and sends a `STATUS_REPORT` to its assigned base.  
> 
> For neighbour sensing, each node exchanges a fixed small `QUERY` record with every valid neighbour. The record includes an active flag. If the sender is heavily utilised, the flag is true and the neighbour returns a `NEIGHBOUR_REPLY`. Sending the fixed query record even when inactive is deliberate: every process knows exactly how many receives to post, so it cannot wait indefinitely for a conditional message.  
> 
> Every heavy node then sends exactly one `ALERT_DECISION`, true or false. A true decision is the specification’s real alert: the node and all valid neighbours are heavily utilised. A false decision still completes the protocol safely, because the base knows exactly how many heavy nodes exist from the status phase.  
> 
> Bases next exchange alert counts, then variable-sized alert batches. Count-before-batch means each base can allocate the exact receive buffer size. Each base runs its local candidate search using OpenMP, sends candidate batches to the owner of each alert, and the owner selects the globally best candidate before returning `REDIRECT`. Finally, all ranks enter one barrier before the next round.

Transition: *This table maps each of those business messages to an MPI operation.*

## Slide 6 — Message catalogue and MPI mapping (75 seconds)

> This table separates business messages from MPI primitives.  
> 
> `STATUS_REPORT`, `QUERY`, `NEIGHBOUR_REPLY`, `ALERT_DECISION`, and all base exchange records use non-blocking point-to-point communication: `MPI_Isend`, `MPI_Irecv`, and `MPI_Waitall`. `REDIRECT` uses a simple send and receive because the source node must wait for its decision.  
> 
> There are only two collective exceptions. `CONFIG_BCAST` uses `MPI_Bcast` once at startup, and `ROUND_SYNC` uses `MPI_Barrier` once per round. Therefore, it is more precise to call this a point-to-point **operational** protocol, rather than saying every single operation is point-to-point.  
> 
> The scaling column is important for Task 3. For example, there are N status reports per round, exactly two times the mesh-edge count query records, and A times S minus one records for alert batches and candidate batches. These counts become the input to our communication-delay analysis.

Transition: *The next slide explains why these non-blocking exchanges do not deadlock.*

## Slide 7 — Why the protocol cannot deadlock (45 seconds)

> The protocol is safe because every phase has a finite and known completion condition. Wherever the message set is known, receives are posted before matching sends, and every non-blocking request completes through `MPI_Wait` or `MPI_Waitall` before its buffer is reused. Tags distinguish all message categories, and round IDs reject stale data.  
> 
> For variable-size base data, bases exchange counts before batches. For alert completion, every heavy node sends one decision, including false, so the base knows precisely how many decisions it must receive. Finally, bases sort alerts identically before candidate exchange.  
> 
> With OpenMP, worker threads only search local cache partitions. They finish before the master thread starts candidate communication, so no OpenMP worker calls MPI. This is exactly why `MPI_THREAD_FUNNELED` is sufficient.

Transition: *We also made the API scope explicit.*

## Slide 8 — API compliance (30 seconds)

> The point-to-point communication protocol relies on the MPI operations taught in Applied Week 5: non-blocking send and receive, completion using wait or wait-all, broadcast, barrier and timing.  
> 
> The hybrid initialisation additionally requests `MPI_THREAD_FUNNELED`. This does not add a new communication protocol; it formally guarantees that only the master thread interacts with MPI. We deliberately do not need communicator splitting, Cartesian helper functions, `Allgatherv`, or `MINLOC`, because rank arithmetic and two-phase point-to-point exchange implement the same required behaviour.

Transition: *To conclude, I will summarise the required resources and the design result.*

## Slide 9 — Takeaway (25 seconds)

> To conclude, the selected deployment uses 80 active cores across four hosts: 16 node ranks and four base-search threads per host. Under the worst case of 64 active alerts at one round per second, the aggregate external bandwidth estimate is only 0.10544 megabits per second.  
> 
> The key result is a safe, scalable architecture: logical mesh sensing, direct regional reporting, explicit point-to-point base coordination, and OpenMP acceleration where shared memory is actually useful. Task 3 will use this exact message catalogue to analyse transmission delay and scaling. Thank you.

---

## Short answers for likely questions

**Why use OpenMP only at bases?**  
Candidate search is an independent scan of a base’s regional cache, so it benefits from shared memory without adding network traffic. A node’s small local port list does not justify thread-management overhead in the baseline.

**Does OpenMP change the MPI message types?**  
No. It changes only local computation time. All inter-process business messages and their payloads remain exactly as listed on Slide 6.

**Why do inactive nodes still send `QUERY` records?**  
The record is a fixed protocol-intent message with `active=false`; it gives every neighbour a known receive count. Only `active=true` represents a real business query and causes a reply.

**Why does a heavy node send `ALERT_DECISION(false)`?**  
It is not a false alert. It tells the base that the node has completed its neighbour check but the all-neighbours-heavy condition was not met. This gives the base an exact completion count.

**Why not use `MPI_Cart_create`?**  
It is optional. The same non-periodic 2-D mesh relationship is obtained deterministically from the rank, row/column calculation and boundary checks.

**Why are base alert batches exchanged in two phases?**  
Counts are exchanged first so every base knows the exact size of every incoming variable-length batch before it posts the receives.
