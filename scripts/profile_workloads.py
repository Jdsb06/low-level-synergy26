"""Fresh-process API latency and burst/sparse/refill space profiles; no official score."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess

from run_benchmarks import cpu_order

ROOT = Path(__file__).resolve().parents[1]


def validate_latency(metrics, threads, operations):
    assert metrics["correct"] is True and metrics["threads"] == threads
    assert metrics["samples"] == threads * operations
    assert sum(v["count"] for v in metrics["apis"].values()) == metrics["samples"]
    assert set(metrics["apis"]) <= {"malloc", "free", "realloc", "calloc"}
    for values in metrics["apis"].values():
        assert values["count"] > 0
        quantiles = [values[k] for k in ("p50_ns", "p95_ns", "p99_ns", "p999_ns", "max_ns")]
        assert all(v >= 0 for v in quantiles) and quantiles == sorted(quantiles)


def validate_lifetimes(metrics):
    assert metrics["correct"] is True and metrics["workers"] == 8
    samples = metrics["snapshots"]
    assert len(samples) == 16 and samples[0]["phase"] == "idle"
    assert samples[0]["live_bytes"] == samples[0]["live_objects"] == 0
    for cycle in range(1, 4):
        group = samples[1 + (cycle - 1) * 5:1 + cycle * 5]
        assert [s["phase"] for s in group] == ["burst", "sparse", "refill", "freed", "trimmed"]
        assert all(s["cycle"] == cycle for s in group)
        assert [s["live_objects"] for s in group] == [4096, 512, 4096, 0, 0]
        assert [s["live_bytes"] for s in group] == [44007424, 5500928, 44007424, 0, 0]


def summarize(runs):
    series = {}
    for row in runs:
        if not row.get("valid"):
            continue
        variant, workload, threads = row["variant"], row["workload"], row["threads"]
        data = row["metrics"]
        if workload != "lifetimes":
            for api, values in data["apis"].items():
                for metric, value in values.items():
                    series.setdefault((variant, workload, threads, api, metric), []).append(value)
            for key in ("clock_pair_p50_ns", "clock_pair_p99_ns"):
                series.setdefault((variant, workload, threads, "calibration", key), []).append(data[key])
        else:
            idle = data["snapshots"][0]
            for sample in data["snapshots"][1:]:
                label = "cycle{}_{}".format(sample["cycle"], sample["phase"])
                for metric in ("vm_kib", "rss_kib", "rss_rollup_kib"):
                    series.setdefault((variant, workload, threads, label, "delta_" + metric), []).append(
                        sample[metric] - idle[metric])
    return [dict(variant=key[0], workload=key[1], threads=key[2], api_or_phase=key[3],
                 metric=key[4], repetitions=len(values), median=statistics.median(values),
                 min=min(values), max=max(values)) for key, values in sorted(series.items())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    if not __debug__:
        parser.error("run without Python optimization so result validation stays enabled")
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--operations", type=int, default=10000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.repetitions <= 100 or not 1 <= args.operations <= 1000000:
        parser.error("repetitions 1..100 and operations 1..1000000 required")
    cpus = cpu_order()
    if len(cpus) < 8:
        parser.error("this comparison requires eight available logical CPUs")
    variants = {"eight_shards": ("build/latency", "build/lifetimes"),
                "one_shard": ("build-single/latency", "build-single/lifetimes"),
                "libc": ("build/latency_libc", "build/lifetimes_libc")}
    args.output.mkdir(parents=True, exist_ok=True)
    sources = ["src/allocator.c", "Makefile", "bench/profile.h", "bench/latency.c", "bench/lifetimes.c",
               "scripts/profile_workloads.py", "scripts/run_benchmarks.py"]
    versions = {}
    for name, command in {"compiler": ["cc", "--version"], "libc": ["getconf", "GNU_LIBC_VERSION"],
                          "cpu": ["lscpu", "--json"]}.items():
        run = subprocess.run(command, capture_output=True, text=True, timeout=10, check=True)
        versions[name] = dict(command=command, stdout=run.stdout)
    record = dict(started_utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(),
                  versions=versions, cpu_order=cpus, trace_seed=12345, order_seed=104729,
                  warmup_per_worker=2000, operations_per_worker=args.operations,
                  flags="-O2 -g -std=c11 with strict warnings and -fno-builtin allocation family; one_shard adds -DMEMCTL_SHARDS=1; libc adds -DMEMCTL_LIBC",
                  environment={k: os.environ.get(k) for k in ("GLIBC_TUNABLES", "MALLOC_ARENA_MAX",
                               "MALLOC_MMAP_THRESHOLD_", "MALLOC_TRIM_THRESHOLD_")},
                  source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources},
                  binary_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                                 for pair in variants.values() for p in pair},
                  limitations=["Local shared laptop; no fixed clock/governor or thermal isolation.",
                               "Common cpuset: physical cores first, then SMT; workers may migrate within it.",
                               "Each call has two clock reads; unadjusted quantiles include timing overhead and scheduling. Calibration is separate, never subtracted.",
                               "Samples pooled across workers; per-process quantiles use nearest rank. CSV takes medians of those quantiles, not a global percentile.",
                               "Latency payload endpoint/prefix checks are outside measured intervals. calloc includes its own zeroing; warmup/cleanup excluded.",
                               "Space snapshots are at phase barriers with all workers alive. smaps_rollup RSS complements approximate VmRSS; phase samples are not exact transient peaks.",
                               "VmPeak/VmHWM in raw data are whole-process high-water counters, not resettable per-phase allocator statistics.",
                               "Space idle includes worker stacks and warmed harness parsers, with no worker allocation or allocator trim yet; first-use arenas count above idle. Residual runtime noise remains. Trim policies differ (memctl_trim vs malloc_trim); libc tcache is not flushed.",
                               "No official normalization, hidden trace, score or universal libc advantage is claimed."], runs=[])
    jobs = [(repeat, name, workload, threads) for repeat in range(args.repetitions)
            for name in variants for workload in ("hot", "mixed", "large") for threads in (1, 8)]
    jobs += [(repeat, name, "lifetimes", 8) for repeat in range(args.repetitions) for name in variants]
    random.Random(record["order_seed"]).shuffle(jobs)
    failed = False
    try:
        for index, (repeat, name, workload, threads) in enumerate(jobs):
            binary = variants[name][workload == "lifetimes"]
            command = ["taskset", "-c", ",".join(map(str, cpus[:threads])), str(ROOT / binary)]
            if workload != "lifetimes":
                command += [str(threads), str(args.operations), "12345", workload]
            row = dict(repeat=repeat, variant=name, workload=workload, threads=threads,
                       command=command, valid=False)
            try:
                run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90)
                row.update(exit=run.returncode, stdout=run.stdout, stderr=run.stderr)
                assert run.returncode == 0 and not run.stderr
                row["metrics"] = json.loads(run.stdout)
                if workload == "lifetimes":
                    validate_lifetimes(row["metrics"])
                else:
                    validate_latency(row["metrics"], threads, args.operations)
                row["valid"] = True
            except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, AssertionError) as exc:
                row["error"] = repr(exc)
                failed = True
            record["runs"].append(row)
            if (index + 1) % 6 == 0:
                print("Captured {}/{} profiles; failures={}".format(index + 1, len(jobs),
                      sum(not r["valid"] for r in record["runs"])), flush=True)
    finally:
        record["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (args.output / "raw.json").write_text(json.dumps(record, indent=2) + "\n")
    rows = summarize(record["runs"])
    if rows:
        with (args.output / "summary.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    print("Profiles: {}/{} valid".format(sum(r["valid"] for r in record["runs"]), len(jobs)))
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
