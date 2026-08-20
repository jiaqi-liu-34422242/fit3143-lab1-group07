# FIT3143 Lab 1 - Group 07

Parallel prime-search implementations in C using:

- a serial baseline;
- POSIX Threads; and
- OpenMP.

The repository also contains the presentation, raw benchmark measurements,
the eight required performance figures, and the scripts used for experiment
automation and plotting.

## Build

Run these commands in the course Linux environment:

```bash
gcc -std=c11 -O2 -Wall -Wextra -Wpedantic task1.c -lm -o task1
gcc -std=c11 -O2 -Wall -Wextra -Wpedantic -pthread task2.c -lm -o task2
gcc -std=c11 -O2 -Wall -Wextra -Wpedantic -fopenmp task3.c -lm -o task3
```

## Interactive use

```bash
./task1
./task2
./task3
```

## Results

- `benchmark_raw.csv` contains the raw timing and correctness records.
- `figures/` contains the eight graphs required for the presentation.
- `lab1_ppt.pptx` contains the presentation slides.

The repository is intended to remain private while the course assessment is
active.
