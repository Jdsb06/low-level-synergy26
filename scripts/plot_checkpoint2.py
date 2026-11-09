"""Plot only recorded checkpoint-2 results."""
import csv
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "build/matplotlib-cache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

with (ROOT / "results/checkpoint2-final-2026-11-09/summary.csv").open() as handle:
    rows = list(csv.DictReader(handle))


def value(variant, workload, workers):
    return float(next(r["median"] for r in rows if r["variant"] == variant and
                      r["workload"] == workload and int(r["workers"]) == workers))


fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.6), constrained_layout=True)
memory = [value(name, "fragmentation", 8) / 1024 for name in ("checkpoint1", "compact_growth")]
bars = axes[0].bar(["Checkpoint 1", "Checkpoint 2"], memory, color=["#64748b", "#087f8c"])
axes[0].bar_label(bars, labels=[f"{n:.2f} MiB" for n in memory], padding=4)
axes[0].set_ylim(0, memory[0] * 1.2)
axes[0].set_ylabel("Virtual-memory growth above warmed idle (MiB)")
axes[0].set_title("Sparse live objects: 85.9% less VM\n512 live allocations; 5.25 MiB requested")
cases = [("small", 1), ("small", 8), ("mixed", 1), ("mixed", 8)]
ratios = [value("compact_growth", workload, workers) / value("checkpoint1", workload, workers)
          for workload, workers in cases]
bars = axes[1].bar(range(4), ratios, color=["#087f8c" if r >= 1 else "#d18b37" for r in ratios])
axes[1].bar_label(bars, labels=[f"{n:.3f}×" for n in ratios], padding=4)
axes[1].axhline(1, color="#64748b", linestyle="--", linewidth=1)
axes[1].set_xticks(range(4), ["Small\n1 thread", "Small\n8 threads", "Mixed\n1 thread", "Mixed\n8 threads"])
axes[1].set_ylim(0, 1.35)
axes[1].set_ylabel("Throughput / checkpoint-1 throughput")
axes[1].set_title("Throughput trade-offs\nRatios of five-process medians")
for axis in axes:
    axis.spines[["top", "right"]].set_visible(False)
    axis.set_axisbelow(True)
    axis.grid(axis="y", alpha=0.15)
fig.suptitle("libmemctl • checkpoint 2", fontsize=15, weight="bold")
fig.supxlabel("Local shared laptop; no fixed frequency or official score. Raw ranges are in the report.", fontsize=9)
path = ROOT / "results/checkpoint2.png"
fig.savefig(path, dpi=160)
plt.close(fig)
print(path)
