#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RESULT_DIR="results"
RAW_FILE="$RESULT_DIR/benchmark_raw.csv"

REPEATS="${REPEATS:-3}"
SIZE_POINTS="${SIZE_POINTS:-30}"
MIN_N="${MIN_N:-11000000}"
N_STEP="${N_STEP:-1000000}"
THREAD_N="${THREAD_N:-40000000}"
CORES="$(nproc)"
FIXED_THREADS="${FIXED_THREADS:-$CORES}"
OVERSUB_THREADS="${OVERSUB_THREADS:-$((CORES * 2))}"

for value in "$REPEATS" "$SIZE_POINTS" "$MIN_N" "$N_STEP" \
             "$THREAD_N" "$FIXED_THREADS" "$OVERSUB_THREADS"; do
    if ! [[ "$value" =~ ^[1-9][0-9]*$ ]]; then
        echo "Benchmark settings must be positive integers." >&2
        exit 1
    fi
done

mkdir -p "$RESULT_DIR"

echo "Compiling Task 1-3 with matching -O2 optimisation..."
gcc -std=c11 -O2 -Wall -Wextra -Wpedantic task1.c -lm -o task1
gcc -std=c11 -O2 -Wall -Wextra -Wpedantic -pthread task2.c -lm -o task2
gcc -std=c11 -O2 -Wall -Wextra -Wpedantic -fopenmp task3.c -lm -o task3

echo "Warming up executables..."
./task1 1000000 --benchmark >/dev/null
./task2 1000000 "$FIXED_THREADS" --benchmark >/dev/null
./task3 1000000 "$FIXED_THREADS" --benchmark >/dev/null

printf '%s\n' \
    'experiment,method,n,threads,repeat,seconds,prime_count' >"$RAW_FILE"

append_result()
{
    local experiment="$1"
    local repeat="$2"
    local result="$3"
    local marker method n threads seconds count

    IFS=',' read -r marker method n threads seconds count <<<"$result"
    if [[ "$marker" != "RESULT" || -z "$count" ]]; then
        echo "Unexpected program output: $result" >&2
        exit 1
    fi

    printf '%s,%s,%s,%s,%s,%s,%s\n' \
        "$experiment" "$method" "$n" "$threads" \
        "$repeat" "$seconds" "$count" >>"$RAW_FILE"
}

echo "Running size sweep: $SIZE_POINTS n values, $REPEATS repeats, $FIXED_THREADS threads..."
for ((index = 0; index < SIZE_POINTS; ++index)); do
    n=$((MIN_N + index * N_STEP))
    echo "  n=$n ($((index + 1))/$SIZE_POINTS)"

    for ((repeat = 1; repeat <= REPEATS; ++repeat)); do
        serial_result="$(./task1 "$n" --benchmark)"
        pthread_result="$(./task2 "$n" "$FIXED_THREADS" --benchmark)"
        openmp_result="$(./task3 "$n" "$FIXED_THREADS" --benchmark)"

        serial_count="${serial_result##*,}"
        pthread_count="${pthread_result##*,}"
        openmp_count="${openmp_result##*,}"
        if [[ "$serial_count" != "$pthread_count" ||
              "$serial_count" != "$openmp_count" ]]; then
            echo "Correctness check failed for n=$n, repeat=$repeat." >&2
            exit 1
        fi

        append_result size "$repeat" "$serial_result"
        append_result size "$repeat" "$pthread_result"
        append_result size "$repeat" "$openmp_result"
    done
done

echo "Running thread sweep at n=$THREAD_N: 1-$CORES and $OVERSUB_THREADS threads..."
for ((repeat = 1; repeat <= REPEATS; ++repeat)); do
    serial_result="$(./task1 "$THREAD_N" --benchmark)"
    serial_count="${serial_result##*,}"
    append_result threads "$repeat" "$serial_result"

    thread_values=()
    for ((threads = 1; threads <= CORES; ++threads)); do
        thread_values+=("$threads")
    done
    if ((OVERSUB_THREADS > CORES)); then
        thread_values+=("$OVERSUB_THREADS")
    fi

    for threads in "${thread_values[@]}"; do
        echo "  repeat=$repeat, threads=$threads"
        pthread_result="$(./task2 "$THREAD_N" "$threads" --benchmark)"
        openmp_result="$(./task3 "$THREAD_N" "$threads" --benchmark)"

        pthread_count="${pthread_result##*,}"
        openmp_count="${openmp_result##*,}"
        if [[ "$serial_count" != "$pthread_count" ||
              "$serial_count" != "$openmp_count" ]]; then
            echo "Correctness check failed for threads=$threads, repeat=$repeat." >&2
            exit 1
        fi

        append_result threads "$repeat" "$pthread_result"
        append_result threads "$repeat" "$openmp_result"
    done
done

echo "Benchmark complete: $RAW_FILE"
echo "CPU cores: $CORES"
echo "Size sweep threads: $FIXED_THREADS"
echo "Thread sweep n: $THREAD_N"
