"""Plot recorded five-process quantiles and final-cycle phase samples only."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
ROWS = list(csv.DictReader((ROOT / "results/checkpoint4-2026-11-09/summary.csv").open()))
VARIANTS = [("eight_shards", "Eight shards", "#2563eb"),
            ("one_shard", "One shard", "#ea580c"), ("libc", "glibc", "#15803d")]


def value(variant, workload, threads, api, metric):
    return next(r for r in ROWS if (r["variant"], r["workload"], r["threads"],
                r["api_or_phase"], r["metric"]) == (variant, workload, str(threads), api, metric))


def main():
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    cases = [(w, n) for w in ("hot", "mixed", "large") for n in (1, 8)]
    for ax, api in zip(axes[0], ("malloc", "free")):
        for offset, (name, label, color) in enumerate(VARIANTS):
            rows = [value(name, w, n, api, "p99_ns") for w, n in cases]
            y = [float(r["median"]) / 1000 for r in rows]
            errors = [[m - float(r["min"]) / 1000 for m, r in zip(y, rows)],
                      [float(r["max"]) / 1000 - m for m, r in zip(y, rows)]]
            ax.errorbar([i + (offset - 1) * .16 for i in range(6)], y, yerr=errors,
                        fmt="o", markersize=4, capsize=3, label=label, color=color)
        ax.set(yscale="log", ylabel="p99 latency (µs, log scale)",
               title=api + ": median p99 and min–max across five processes",
               xticks=range(6), xticklabels=[w + "\n" + str(n) + " thread(s)" for w, n in cases])
        ax.grid(axis="y", alpha=.2)
    phases = ["burst", "sparse", "refill", "freed", "trimmed"]
    for ax, metric, label in [(axes[1, 0], "delta_vm_kib", "Virtual memory"),
                              (axes[1, 1], "delta_rss_rollup_kib", "Resident memory (smaps_rollup)")]:
        for name, variant_label, color in VARIANTS:
            rows = [value(name, "lifetimes", 8, "cycle3_" + p, metric) for p in phases]
            ax.plot(range(5), [float(r["median"]) / 1024 for r in rows],
                    marker="o", markersize=4, label=variant_label, color=color)
        ax.plot(range(5), [44007424 / 1048576, 5500928 / 1048576, 44007424 / 1048576, 0, 0],
                "k--", label="Live requested payload", linewidth=1)
        ax.set(title=label + ": third burst/drain cycle", ylabel="Growth above pre-allocation idle (MiB)",
               xticks=range(5), xticklabels=phases)
        ax.grid(axis="y", alpha=.2)
    axes[0, 0].legend(fontsize=8)
    axes[1, 0].legend(fontsize=8)
    fig.suptitle("Checkpoint 4 · Local laptop profiles, not official scores\n"
                 "Unadjusted latency includes clock/scheduling costs; memory is sampled at phase barriers",
                 fontsize=12)
    fig.savefig(ROOT / "results/checkpoint4.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
