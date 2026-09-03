# FIT3143 Applied #1 - Assessment Gap Analysis

## 1. Purpose

This document evaluates the original `EVCSN_Design_Architecture_and_Analysis.md` against the Applied #1 assessment specification and HD marking criteria. It records the issues found before revision and explains what must be completed before final submission.

The separate `EVCSN_Design_Architecture_and_Analysis_Revised.md` contains the revised Tasks 1-3 design.

## 2. Overall assessment

The original document was a strong design draft but was not yet an HD-level submission. Its main strengths were the three-plane hybrid topology, coverage of all nine Week 5 topology families, separation of physical and logical topology, two architecture-diagram sources, explicit MPI communicators, and complexity discussion.

The principal weaknesses were incomplete Task 3 deliverables, no required bandwidth calculation, an inconsistent machine/core formula, an unsafe or underspecified collective protocol, and several smaller accuracy and submission issues.

Estimated Tasks 1-3 content result before revision:

| Rubric item | Estimated mark | Indicative band | Main reason |
|---|---:|---|---|
| Task 1 - Network topology | 8.5-9.5 / 10 | HD borderline | All topology families were compared and the hybrid choice was justified, but some definitions remained vague and the star link cost was inaccurate. |
| Task 2 - Architecture design | 9-11 / 15 | C-D | Core components and two diagram sources were present, but required bandwidth, consistent resource sizing, distance policy, and safe collective scheduling were missing. |
| Task 3 - Analysis | 7-9 / 15 | C | Useful asymptotic analysis was present, but there were no actual graphs and no per-message numerical delay calculations. |
| **Tasks 1-3 subtotal** | **25-29 / 40** | **C-D** | The content was promising but incomplete against explicit HD requirements. |

Presentation quality and Q&A account for the remaining 60% and cannot be reliably graded from the design document alone.

## 3. Critical gaps

### 3.1 Required Task 3 graphs were not produced

The original document only listed the graphs that should be created. It did not contain graph images, plotted data, or generated result files.

For HD, the presentation must include:

1. transmission-delay analysis as the number of charging nodes increases;
2. transmission-delay analysis as the number of base stations increases;
3. another growth factor, such as ports per node, alert fraction, EV arrival rate, or update frequency; and
4. convincing graphs with abundant data points and clearly stated assumptions.

This was the largest gap and directly prevented an HD result for Task 3.

### 3.2 Required network bandwidth was not calculated

Task 2 explicitly requires an explanation of required network bandwidth. The original document stated that the cluster uses 1 Gbps links but did not calculate:

- bytes generated per round;
- messages crossing machine boundaries;
- required bit/s at the chosen update frequency;
- MPI/protocol overhead; or
- whether 1 Gbps is sufficient under a defined workload.

The revised document addresses this with explicit payload sizes, a cross-host traffic model, a 25% overhead margin, and a worked baseline result.

### 3.3 Machine and core sizing was internally inconsistent

The original formula was:

```text
machines = ceil((N + S) / C)
```

This is valid only when every MPI rank uses one core. The same document later allowed multiple OpenMP threads per rank, so the formula could underestimate the number of required cores and machines.

A consistent hybrid formula is:

```text
machines_min = ceil((N t_node + S t_base) / C_host)
```

The final design must also state an actual baseline allocation rather than only an abstract lower bound.

### 3.4 Per-alert collectives could be called in inconsistent order

The original protocol proposed one `MPI_Bcast` and `MPI_Allreduce` for every alert. This is unsafe or incomplete when several base stations receive alerts concurrently:

- every rank in a communicator must call collectives in the same order;
- every rank must agree on the `MPI_Bcast` root;
- bases with no local alert must still participate; and
- independently initiated alerts could cause mismatched collective calls or deadlock.

The revised protocol batches alerts by simulation round:

1. `MPI_Allgather` exchanges regional alert counts;
2. one `MPI_Allgatherv` creates a common ordered alert list;
3. every base computes regional candidates in that order; and
4. one vector `MPI_Allreduce(MINLOC)` chooses all global winners.

### 3.5 The meaning of “closest available station” was undefined

The original document used `MPI_MINLOC` but did not define the distance being minimised. Possible interpretations included physical Euclidean distance, road distance, logical mesh distance, or cluster-network distance.

The selected baseline requires a deterministic rule. The revised design uses logical Manhattan distance:

```text
d = abs(sourceRow - targetRow) + abs(sourceColumn - targetColumn)
```

An eligible candidate must have at least one free port and utilisation at or below the threshold. Equal-distance candidates are resolved by the smaller node id.

### 3.6 Transmission analysis was generic rather than per-message

The original analysis used one generic payload length `L`. It did not assign sizes or compute serialisation delay for:

- `STATUS_REPORT`;
- `QUERY`;
- `NEIGHBOUR_REPLY`;
- `ALERT`;
- alert-count exchange;
- alert-batch exchange;
- candidate reduction; or
- `REDIRECT`.

The HD criterion requires communication analysis for all message types. Each message therefore needs a payload assumption, count, scaling result, and transmission-delay calculation.

### 3.7 Raw transmission delay and system-level delay needed clearer separation

For a bounded payload on a fixed 1 Gbps link:

```text
T_serialisation = 8L / B = Theta(1)
```

Increasing `N` does not change this raw delay for one fixed-size message. It increases total traffic, per-base ingress, processing, contention, queueing, and round-completion time. Similarly, increasing `S` mainly reduces regional load toward `N/S`; it does not make the bits of one direct message serialise faster.

Graphs must not label aggregate or queueing effects as raw serialisation delay.

## 4. Task-specific observations

### 4.1 Task 1

Strengths:

- all nine Week 5 topology families were included;
- topology was selected according to communication scope rather than forcing one topology everywhere;
- the document correctly distinguished logical adjacency from physical EV-station placement; and
- the rejection of torus wrap-around and all-to-all charging-node communication was well motivated.

Issues:

- star link cost was written as `N` instead of `N-1`;
- the inter-base “small control overlay” was not named as a specific logical topology;
- bisection width and arc connectivity were omitted from the comparison; and
- some geographical arguments needed to be reconciled with the statement that adjacency is logical.

### 4.2 Task 2

Strengths:

- `ChargingPort`, `ChargingNode`, `BaseStation`, and `Topology` were represented;
- both a static class diagram and a dynamic sequence diagram were supplied as Mermaid source;
- MPI ranks and `node_comm`, `cart_comm`, and `base_comm` were introduced;
- stale or missing neighbour responses were handled conservatively; and
- `MPI_THREAD_FUNNELED` showed awareness of MPI thread-safety requirements.

Issues:

- required bandwidth and a concrete machine/core deployment were incomplete;
- OpenMP use was conditional and not tied to a concrete core allocation;
- the class multiplicity `N/S` was not a valid UML multiplicity;
- region assignment and nearest-candidate distance were not fully specified;
- concurrent-alert collective ordering was unsafe or ambiguous; and
- raw Mermaid blocks still needed to be rendered and visually checked for submission.

### 4.3 Task 3

Strengths:

- local mesh edges and worst-case query/reply counts were derived correctly;
- the analysis distinguished individual-message cost from aggregate traffic;
- per-base ingress was related to `N/S`;
- inter-base collective critical path was related to `log S`; and
- the `S = 1` boundary case was considered.

Issues:

- no actual graphs were included;
- no numerical payload or delay table was supplied;
- required external bandwidth was not calculated;
- collective message volume was not quantified; and
- the generic `8LH/B` model required clearer assumptions about startup latency, physical hops, and switching behaviour.

## 5. Presentation and submission risks

- The detailed original document contained approximately 2,885 words and should not be read verbatim in a 6-7 minute presentation.
- A separate concise presentation or clearly selected presentation path is required.
- Mermaid sources should be rendered into legible diagrams before submission.
- The presentation conclusion should explicitly discuss limitations and future work.
- Team names, student IDs, and Monash email addresses must replace placeholders.
- Generative-AI use must be declared, and prompt records must be uploaded in PDF format as required.
- Task 3 graphs and their underlying data must be submitted with the detailed design materials.

## 6. Recommended completion order

1. Confirm the revised topology, distance policy, payload sizes, and baseline parameters as team-owned assumptions.
2. Render and visually verify the static and communication diagrams.
3. Generate the required `N`, `S`, and third-factor graphs with abundant data points.
4. Check graph equations and units against the revised message and bandwidth model.
5. Create a concise 6-7 minute presentation with limitations and future work.
6. Replace all identity placeholders and add the AI declaration and prompt PDF.
7. Practise Q&A without external tools, especially logical versus physical topology, `N/S` scaling, collective ordering, and raw versus aggregate delay.

## 7. Status after revision

The separate revised design document resolves the textual and analytical gaps concerning topology accuracy, collective scheduling, distance policy, per-message payloads, numerical serialisation delays, hybrid core sizing, concrete host allocation, and required bandwidth.

The following work intentionally remains incomplete:

- generating the required Task 3 graphs;
- rendering the two Mermaid architecture diagrams;
- inserting final team identity details;
- producing the final presentation; and
- exporting the AI prompt record to PDF.
