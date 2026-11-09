"""Plot measured cache trade-offs; common throughput uses the longer confirmation."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
MAIN = list(csv.DictReader((ROOT / "results/checkpoint5-2026-11-09/summary.csv").open()))
LONG = list(csv.DictReader((ROOT / "results/checkpoint5-common-confirmation-2026-11-09/summary.csv").open()))
VARIANTS = [("checkpoint4", "Checkpoint 4", "#64748b"), ("capped_cache", "Capped cache", "#2563eb")]


def get(rows, variant, workload, threads, api, metric):
    return next(r for r in rows if (r["variant"], r["workload"], r["threads"], r["api_or_phase"], r["metric"])
                == (variant, workload, str(threads), api, metric))


def points(ax, cases, getter, scale):
    for offset, (variant, label, color) in enumerate(VARIANTS):
        rows = [getter(variant, case) for case in cases]
        medians = [float(r["median"]) / scale for r in rows]
        errors = [[m - float(r["min"]) / scale for m, r in zip(medians, rows)],
                  [float(r["max"]) / scale - m for m, r in zip(medians, rows)]]
        ax.errorbar([i + (offset - .5) * .18 for i in range(len(cases))], medians,
                    yerr=errors, fmt="o", capsize=3, label=label, color=color)
    ax.grid(axis="y", alpha=.2)


def main():
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    cases = [(w, n) for w in ("small", "mixed", "large") for n in (1, 8)]
    points(axes[0, 0], cases, lambda v, c: get(MAIN if c[0] == "large" else LONG, v,
           "throughput_" + c[0], c[1], "all", "api_calls_per_second"), 1000000)
    axes[0, 0].set(yscale="log", ylabel="Million API calls/s (log scale; higher is better)",
                   title="Throughput: medians and five-process min–max", xticks=range(6),
                   xticklabels=[w + "\n" + str(n) + " thread(s)" for w, n in cases])
    axes[0, 0].legend(fontsize=8)
    cases = [(n, metric) for n in (1, 8) for metric in ("p50_ns", "p99_ns")]
    points(axes[0, 1], cases, lambda v, c: get(MAIN, v, "latency_large", c[0], "malloc", c[1]), 1000)
    axes[0, 1].set(yscale="log", ylabel="µs (log scale; lower is better)",
                   title="Large malloc latency: clock overhead included", xticks=range(4),
                   xticklabels=[str(n) + " thread(s)\n" + m.split("_")[0] for n, m in cases])
    phases = ["burst", "sparse", "freed", "trimmed"]
    for ax, metric, label in [(axes[1, 0], "delta_vm_kib", "Virtual memory"),
                              (axes[1, 1], "delta_rss_rollup_kib", "Resident memory (smaps_rollup)")]:
        for v, name, color in VARIANTS:
            y = [float(get(MAIN, v, "space_large_lifetimes", 8, "cycle3_" + p, metric)["median"]) / 1024
                 for p in phases]
            ax.plot(range(4), y, marker="o", markersize=4, color=color, label=name)
        ax.plot(range(4), [50070016 / 1048576, 6029376 / 1048576, 0, 0], "k--", label="Requested payload")
        ax.set(title=label + ": third large-object cycle", ylabel="Growth above idle (MiB)",
               xticks=range(4), xticklabels=phases)
        ax.grid(axis="y", alpha=.2)
    axes[1, 0].legend(fontsize=8)
    fig.suptitle("Checkpoint 5 · Measured cache trade-off on a shared laptop\n"
                 "Five runs/case; throughput calls per worker: 5M small/mixed, 25k large; not official scores", fontsize=12)
    fig.savefig(ROOT / "results/checkpoint5.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
