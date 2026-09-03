# Jiaqi — Task 2 deliverables

This directory contains the final Task 2 architecture based on the collective MPI protocol.

## Files

- `JIAQI_Task2_Final_Design.md` — submission-ready English design document.
- `figures/task2-class-diagram.svg` — required static UML-style structure diagram.
- `figures/task2-sequence-diagram.svg` — required communication sequence diagram.
- `figures/task2-communicators-deployment.svg` — supporting communicator and cluster-deployment diagram.
- PNG versions of all figures for direct insertion into presentation slides.
- `tools/render-diagrams.mjs` — reproducible SVG and PNG generator.

## Final protocol

```text
MPI_COMM_WORLD
├── base_comm
└── node_comm
    └── cart_comm

base_comm per round:
Allgather alert counts
→ Allgatherv alert batches
→ vector Allreduce(MINLOC)
```

The design retains fixed neighbour query-intent records and one alert decision from every heavy node so that all conditional communication phases have a known completion condition.

