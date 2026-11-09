"""Fresh-process local measurements, with randomized order and complete raw evidence."""

import argparse
import csv
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def command_text(argv):
    result = subprocess.run(argv, text=True, capture_output=True, check=False, timeout=10)
    return {"argv": argv, "returncode": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr}


def cpu_order():
    allowed = sorted(os.sched_getaffinity(0))
    first = []
    extra = []
    seen = set()
    for cpu in allowed:
        topology = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        key = ((topology / "physical_package_id").read_text().strip(),
               (topology / "core_id").read_text().strip())
        if key in seen:
            extra.append(cpu)
        else:
            first.append(cpu)
            seen.add(key)
    return first + extra


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--operations", type=int, default=20000)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--algorithms", nargs="+", choices=["reference", "one_shard", "eight_shards"],
                        default=["reference", "one_shard", "eight_shards"])
    parser.add_argument("--threads", nargs="+", type=int, choices=[1, 2, 4, 8], default=[1, 2, 4, 8])
    parser.add_argument("--workloads", nargs="+", choices=["small", "mixed", "large"],
                        default=["small", "mixed", "large"])
    args = parser.parse_args()
    if args.repetitions < 1 or not 1 <= args.operations <= 10000000:
        parser.error("positive repetitions and 1..10000000 operations required")
    args.output.mkdir(parents=True, exist_ok=True)
    binaries = {
        "reference": ROOT / "build/benchmark_reference",
        "one_shard": ROOT / "build-single/benchmark_candidate",
        "eight_shards": ROOT / "build/benchmark_candidate",
    }
    binaries = {name: path for name, path in binaries.items() if name in args.algorithms}
    cpus = cpu_order()
    thread_counts = [n for n in args.threads if n <= len(cpus)]
    evidence = {
        "started_ist": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
        "scope": "local development benchmark; not official score or cluster result",
        "platform": platform.platform(), "python": platform.python_version(),
        "cpu_order": cpus,
        "placement": "first hardware thread of each physical core first, then siblings; shared cpuset, no fixed worker pinning",
        "versions": [command_text(["cc", "--version"]), command_text(["lscpu", "--json"])],
        "binary_sha256": {name: hashlib.sha256(path.read_bytes()).hexdigest()
                          for name, path in binaries.items()},
        "source_sha256": hashlib.sha256((ROOT / "src/allocator.c").read_bytes()).hexdigest(),
        "flags": "-O2 -g -std=c11 with strict warnings; one_shard additionally -DMEMCTL_SHARDS=1",
        "trace_seed": 12345, "order_seed": 20261109,
        "warmup_operations_per_worker": 2000,
        "limitations": [
            "Laptop shared with desktop workloads; governor, fixed frequency and thermal isolation not controlled.",
            "Eight threads include SMT siblings on this six-core/eight-logical-CPU host.",
            "Timed loop checks payload endpoints; independent tests check complete payloads.",
            "Timing includes start/finish barrier overhead, excludes thread creation, warmup and final live-object cleanup.",
            "Reported maxrss is whole-process high-water RSS, not allocator-attributable memory.",
            "No libc allocator comparison, official normalization target or hidden test score.",
        ],
        "runs": [], "space_runs": [],
    }
    rng = random.Random(evidence["order_seed"])
    failed = False
    jobs = [(repeat, name, threads, workload)
            for repeat in range(args.repetitions)
            for name in binaries for threads in thread_counts
            for workload in args.workloads]
    rng.shuffle(jobs)
    try:
        for index, (repeat, name, threads, workload) in enumerate(jobs):
            argv = ["taskset", "-c", ",".join(map(str, cpus[:threads])),
                    str(binaries[name]), str(threads), str(args.operations), "12345", workload]
            started = time.monotonic()
            row = {"repeat": repeat, "algorithm": name, "workload": workload,
                   "threads": threads, "argv": argv}
            try:
                result = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=False)
                row.update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
                row["metrics"] = json.loads(result.stdout)
                if result.returncode != 0 or not row["metrics"]["correct"]:
                    failed = True
            except (OSError, subprocess.TimeoutExpired, ValueError, KeyError) as exc:
                row["error"] = str(exc)
                failed = True
            row["wall_seconds_including_startup"] = time.monotonic() - started
            evidence["runs"].append(row)
            if (index + 1) % 12 == 0:
                print(f"Captured {index + 1}/{len(jobs)} timing runs", flush=True)
        for repeat in range(args.repetitions):
            for name, binary in binaries.items():
                argv = ["taskset", "-c", str(cpus[0]), str(binary), "space"]
                result = subprocess.run(argv, capture_output=True, text=True, timeout=30, check=False)
                row = {"repeat": repeat, "algorithm": name, "argv": argv,
                       "returncode": result.returncode, "stdout": result.stdout,
                       "stderr": result.stderr, "metrics": json.loads(result.stdout)}
                evidence["space_runs"].append(row)
                failed |= result.returncode != 0
    finally:
        evidence["finished_ist"] = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
        (args.output / "raw.json").write_text(json.dumps(evidence, indent=2) + "\n")
    summary = []
    for name in binaries:
        for threads in thread_counts:
            for workload in args.workloads:
                matches = [r for r in evidence["runs"] if r["algorithm"] == name
                           and r["threads"] == threads and r["workload"] == workload]
                if len(matches) != args.repetitions or any(
                    r.get("returncode") != 0 or not r.get("metrics", {}).get("correct") for r in matches
                ):
                    continue
                rates = [r["metrics"]["ops_per_second"] for r in matches]
                summary.append({"algorithm": name, "threads": threads, "workload": workload,
                                "repetitions": len(rates), "median_ops_per_second": statistics.median(rates),
                                "min_ops_per_second": min(rates), "max_ops_per_second": max(rates)})
    if summary:
        with (args.output / "summary.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(summary[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(summary)
        for threads in thread_counts:
            for workload in args.workloads:
                rates = {r["algorithm"]: r["median_ops_per_second"] for r in summary
                         if r["threads"] == threads and r["workload"] == workload}
                if len(rates) == len(binaries):
                    print(f"{threads} threads {workload}: " + ", ".join(
                        f"{name} {rate / 1e6:.3f} Mops/s" for name, rate in rates.items()))
    print(f"Evidence: {args.output.resolve()}")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
