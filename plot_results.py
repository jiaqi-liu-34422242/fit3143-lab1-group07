#!/usr/bin/env python3

"""
Jiaqi Liu — 34422242
Shengyuan Jin — 344172573
"""

import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


SERIES = {
    "serial": ("Serial", "#30343b", "o"),
    "pthread": ("POSIX Threads", "#276fbf", "s"),
    "openmp": ("OpenMP", "#e07a1f", "^"),
}


def read_rows(path):
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                {
                    "experiment": row["experiment"],
                    "method": row["method"],
                    "n": int(row["n"]),
                    "threads": int(row["threads"]),
                    "repeat": int(row["repeat"]),
                    "seconds": float(row["seconds"]),
                    "prime_count": int(row["prime_count"]),
                }
            )
    if not rows:
        raise ValueError("The benchmark CSV is empty.")
    return rows


def aggregate(rows, key_name):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["method"], row[key_name])].append(row["seconds"])

    result = {}
    for key, values in grouped.items():
        result[key] = {
            "median": statistics.median(values),
            "minimum": min(values),
            "maximum": max(values),
            "runs": len(values),
        }
    return result


def setup_axes(title, xlabel, ylabel):
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.set_title(title, fontweight="bold", pad=12)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, color="#d7dbe0", linewidth=0.7, alpha=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    return fig, ax


def plot_runtime(ax, aggregate_data, x_values, key_name, methods):
    for method in methods:
        label, color, marker = SERIES[method]
        medians = [aggregate_data[(method, x)]["median"] for x in x_values]
        minima = [aggregate_data[(method, x)]["minimum"] for x in x_values]
        maxima = [aggregate_data[(method, x)]["maximum"] for x in x_values]
        mark_every = max(1, len(x_values) // 10)
        ax.fill_between(x_values, minima, maxima, color=color, alpha=0.12)
        ax.plot(
            x_values,
            medians,
            label=label,
            color=color,
            marker=marker,
            markevery=mark_every,
            markersize=4.5,
            linewidth=2,
        )
    ax.legend(frameon=False)


def save(fig, output_dir, filename):
    fig.tight_layout()
    path = output_dir / filename
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(path)


def main():
    parser = argparse.ArgumentParser(description="Generate the eight Task 4 graphs.")
    parser.add_argument(
        "--input", default="results/benchmark_raw.csv", type=Path
    )
    parser.add_argument(
        "--output-dir", default="results/figures", type=Path
    )
    args = parser.parse_args()

    rows = read_rows(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    size_rows = [row for row in rows if row["experiment"] == "size"]
    thread_rows = [row for row in rows if row["experiment"] == "threads"]
    n_values = sorted({row["n"] for row in size_rows})
    thread_values = sorted(
        {row["threads"] for row in thread_rows if row["method"] != "serial"}
    )

    if len(n_values) < 30:
        raise ValueError(
            f"Task 4 requires at least 30 different n values; found {len(n_values)}."
        )
    if not thread_values:
        raise ValueError("No thread-sweep results were found.")

    size_agg = aggregate(size_rows, "n")
    thread_agg = aggregate(thread_rows, "threads")
    fixed_threads = sorted(
        {row["threads"] for row in size_rows if row["method"] == "pthread"}
    )
    fixed_threads_label = fixed_threads[0] if len(fixed_threads) == 1 else "multiple"
    repeat_count = max(row["repeat"] for row in rows)
    thread_n = next(row["n"] for row in thread_rows if row["method"] == "serial")

    fig, ax = setup_axes(
        f"Serial vs POSIX Threads by n ({fixed_threads_label} threads)",
        "Upper bound n (millions)",
        "Computation time (seconds)",
    )
    x_millions = [n / 1_000_000 for n in n_values]
    remapped = {}
    for method in SERIES:
        for n, x in zip(n_values, x_millions):
            remapped[(method, x)] = size_agg[(method, n)]
    plot_runtime(ax, remapped, x_millions, "n", ["serial", "pthread"])
    save(fig, args.output_dir, "01_serial_vs_pthreads_by_n.png")

    fig, ax = setup_axes(
        f"POSIX Threads Speedup by n ({fixed_threads_label} threads)",
        "Upper bound n (millions)",
        "Speedup (serial / parallel)",
    )
    pthread_speedup = [
        size_agg[("serial", n)]["median"]
        / size_agg[("pthread", n)]["median"]
        for n in n_values
    ]
    ax.axhline(1.0, color="#6f7782", linestyle="--", linewidth=1, label="No speedup")
    ax.plot(x_millions, pthread_speedup, color=SERIES["pthread"][1], linewidth=2,
            marker="s", markevery=max(1, len(n_values) // 10), markersize=4.5,
            label="POSIX Threads")
    ax.legend(frameon=False)
    save(fig, args.output_dir, "02_pthreads_speedup_by_n.png")

    serial_thread_values = [
        row["seconds"] for row in thread_rows if row["method"] == "serial"
    ]
    serial_stats = {
        "median": statistics.median(serial_thread_values),
        "minimum": min(serial_thread_values),
        "maximum": max(serial_thread_values),
        "runs": len(serial_thread_values),
    }
    thread_plot_agg = dict(thread_agg)
    for threads in thread_values:
        thread_plot_agg[("serial", threads)] = serial_stats

    fig, ax = setup_axes(
        f"Serial vs POSIX Threads by Thread Count (n={thread_n:,})",
        "Number of threads",
        "Computation time (seconds)",
    )
    plot_runtime(ax, thread_plot_agg, thread_values, "threads", ["serial", "pthread"])
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    save(fig, args.output_dir, "03_serial_vs_pthreads_by_threads.png")

    fig, ax = setup_axes(
        f"POSIX Threads Speedup by Thread Count (n={thread_n:,})",
        "Number of threads",
        "Speedup (serial / parallel)",
    )
    pthread_thread_speedup = [
        serial_stats["median"] / thread_agg[("pthread", threads)]["median"]
        for threads in thread_values
    ]
    ax.plot(thread_values, thread_values, color="#6f7782", linestyle="--",
            linewidth=1, label="Ideal linear speedup")
    ax.plot(thread_values, pthread_thread_speedup, color=SERIES["pthread"][1],
            marker="s", linewidth=2, label="Measured speedup")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend(frameon=False)
    save(fig, args.output_dir, "04_pthreads_speedup_by_threads.png")

    fig, ax = setup_axes(
        f"Serial vs OpenMP by n ({fixed_threads_label} threads)",
        "Upper bound n (millions)",
        "Computation time (seconds)",
    )
    plot_runtime(ax, remapped, x_millions, "n", ["serial", "openmp"])
    save(fig, args.output_dir, "05_serial_vs_openmp_by_n.png")

    fig, ax = setup_axes(
        f"OpenMP Speedup by n ({fixed_threads_label} threads)",
        "Upper bound n (millions)",
        "Speedup (serial / parallel)",
    )
    openmp_speedup = [
        size_agg[("serial", n)]["median"]
        / size_agg[("openmp", n)]["median"]
        for n in n_values
    ]
    ax.axhline(1.0, color="#6f7782", linestyle="--", linewidth=1, label="No speedup")
    ax.plot(x_millions, openmp_speedup, color=SERIES["openmp"][1], linewidth=2,
            marker="^", markevery=max(1, len(n_values) // 10), markersize=4.5,
            label="OpenMP")
    ax.legend(frameon=False)
    save(fig, args.output_dir, "06_openmp_speedup_by_n.png")

    fig, ax = setup_axes(
        f"POSIX Threads vs OpenMP by n ({fixed_threads_label} threads)",
        "Upper bound n (millions)",
        "Computation time (seconds)",
    )
    plot_runtime(ax, remapped, x_millions, "n", ["pthread", "openmp"])
    save(fig, args.output_dir, "07_pthreads_vs_openmp_by_n.png")

    fig, ax = setup_axes(
        f"POSIX Threads vs OpenMP by Thread Count (n={thread_n:,})",
        "Number of threads",
        "Computation time (seconds)",
    )
    plot_runtime(ax, thread_agg, thread_values, "threads", ["pthread", "openmp"])
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    save(fig, args.output_dir, "08_pthreads_vs_openmp_by_threads.png")

    print(
        f"Generated 8 figures from {len(n_values)} n values, "
        f"{len(thread_values)} thread counts, and up to {repeat_count} repeats."
    )


if __name__ == "__main__":
    main()
