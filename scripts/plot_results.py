"""Plot recorded local results; never generate synthetic measurements."""

import argparse
import csv
import json
import os
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "build/matplotlib-cache"))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=ROOT / "results/sharding-confirmation-2026-11-09")
    parser.add_argument("--space-results", type=Path, default=ROOT / "results/local-2026-11-09")
    parser.add_argument("--output", type=Path, default=ROOT / "results/performance.png")
    args = parser.parse_args()
    with (args.results / "summary.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    space = json.loads((args.space_results / "raw.json").read_text())["space_runs"]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.7), constrained_layout=True)
    colors = {"one_shard": "#64748b", "eight_shards": "#087f8c"}
    for name, shift, label in [("one_shard", -0.18, "One shard"),
                               ("eight_shards", 0.18, "Eight shards")]:
        matches = sorted((r for r in rows if r["algorithm"] == name and r["workload"] == "mixed"),
                         key=lambda r: int(r["threads"]))
        median = [float(r["median_ops_per_second"]) / 1e6 for r in matches]
        low = [m - float(r["min_ops_per_second"]) / 1e6 for m, r in zip(median, matches)]
        high = [float(r["max_ops_per_second"]) / 1e6 - m for m, r in zip(median, matches)]
        bars = axes[0].bar([i + shift for i in range(len(matches))], median, width=0.34,
                           color=colors[name], label=label, yerr=[low, high], capsize=3)
        axes[0].bar_label(bars, labels=[f"{value:.2f}" for value in median], padding=3)
    axes[0].set_xticks([0, 1], ["1 thread", "8 threads"])
    axes[0].set_ylabel("Million public API calls / second")
    axes[0].set_title("Mixed workload: median and min–max\n500,000 calls per worker, five processes")
    axes[0].legend(frameon=False)
    labels = []
    values = []
    for name, label in [("reference", "Supplied reference"), ("eight_shards", "Our allocator")]:
        items = [r["metrics"] for r in space if r["algorithm"] == name]
        values.append(statistics.median(r["held_vm_kib"] - r["before_vm_kib"] for r in items) / 1024)
        labels.append(label)
    bars = axes[1].bar(labels, values, color=["#64748b", "#087f8c"], width=0.55)
    axes[1].bar_label(bars, labels=[f"{value:.2f} MiB" for value in values], padding=4)
    axes[1].set_ylim(0, max(values) * 1.22)
    axes[1].set_ylabel("Virtual-memory growth above idle (MiB)")
    axes[1].set_title("4,096 live allocations, five-process median\n13.83 MiB requested; fully touched")
    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
        axis.set_axisbelow(True)
        axis.grid(axis="y", alpha=0.18)
    fig.suptitle("libmemctl • local development evidence", fontsize=15, weight="bold")
    fig.supxlabel("Laptop measurements; timing/frequency not isolated. These are not official scores.", fontsize=9)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=160)
    plt.close(fig)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
