"""Compare the pinned baseline allocator against bounded large-object reuse."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import random
import statistics
import subprocess

from profile_workloads import validate_latency, validate_lifetimes, summarize
from run_benchmarks import cpu_order

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "521932e19106be195857014b44c2531e137c2b6e54cd33927f93cb138952e9a0"


def validate_large_lifetimes(data):
    assert data["correct"] is True and data["workers"] == 8
    snapshots = data["snapshots"]
    assert len(snapshots) == 16 and snapshots[0]["live_bytes"] == 0
    burst = sum(65537 + i * 1024 for i in range(64)) * 8
    sparse = sum(65537 + i * 1024 for i in range(64) if i % 8 == 0) * 8
    refill = sum(65537 + (i if i % 8 == 0 else (i + 17) % 64) * 1024 for i in range(64)) * 8
    for cycle in range(1, 4):
        group = snapshots[1 + (cycle - 1) * 5:1 + cycle * 5]
        assert [s["cycle"] for s in group] == [cycle] * 5
        assert [s["phase"] for s in group] == ["burst", "sparse", "refill", "freed", "trimmed"]
        assert [s["live_objects"] for s in group] == [512, 64, 512, 0, 0]
        assert [s["live_bytes"] for s in group] == [burst, sparse, refill, 0, 0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    if not __debug__:
        parser.error("run without Python optimization to retain result checks")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--latency-operations", type=int, default=10000)
    parser.add_argument("--throughput-operations", type=int, default=500000)
    parser.add_argument("--large-operations", type=int, default=25000)
    parser.add_argument("--common-throughput-only", action="store_true",
                        help="longer confirmation of small/mixed throughput only")
    args = parser.parse_args()
    if (not 1 <= args.repetitions <= 100 or not 1 <= args.latency_operations <= 1000000
            or any(not 1 <= n <= 10000000 for n in [args.throughput_operations, args.large_operations])):
        parser.error("repetitions 1..100; latency operations 1..1000000; throughput operations 1..10000000")
    cpus = cpu_order()
    if len(cpus) < 8:
        parser.error("eight available logical CPUs required")
    baseline = ROOT / "build-baseline/allocator.c"
    if hashlib.sha256(baseline.read_bytes()).hexdigest() != BASELINE_SHA:
        parser.error("baseline source must match the pinned baseline hash")
    variants = {"baseline": "build-baseline", "capped_cache": "build"}
    binaries = ["latency", "benchmark_candidate", "lifetimes", "large_lifetimes"]
    source_files = ["src/allocator.c", "build-baseline/allocator.c", "bench/latency.c",
                    "bench/benchmark.c", "bench/lifetimes.c", "bench/profile.h", "Makefile",
                    "scripts/compare_large_cache.py", "scripts/profile_workloads.py",
                    "scripts/run_benchmarks.py"]
    versions = {}
    for name, cmd in {"compiler": ["cc", "--version"], "libc": ["getconf", "GNU_LIBC_VERSION"],
                      "cpu": ["lscpu", "--json"]}.items():
        versions[name] = subprocess.check_output(cmd, text=True)
    record = dict(started_utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(),
                  versions=versions, cpu_order=cpus, trace_seed=12345, order_seed=130363,
                  options=vars(args) | {"output": str(args.output)},
                  flags="Both: -O2 -g, C11 strict warnings, eight shards; allocation builtins disabled in allocator and latency/space harnesses. Throughput uses existing benchmark target flags. Candidate uses MEMCTL_LARGE_CACHE=1 default.",
                  source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source_files},
                  binary_sha256={str(Path(d) / b): hashlib.sha256((ROOT / d / b).read_bytes()).hexdigest()
                                 for d in variants.values() for b in binaries},
                  limitations=["Shared local laptop; same cpuset per worker count; no fixed worker affinity, clock or thermal isolation.",
                               "Latency: 2000 warmup calls/worker; nearest-rank process quantiles include timer and scheduling costs. Summary medians are not pooled quantiles.",
                               "Throughput: existing benchmark with endpoint checks and barrier overhead; 2000 warmup calls/worker. Large throughput uses 65537..196608 bytes; latency large uses 65537..131072.",
                               "Space: pre-allocation idle, all workers alive, all requested bytes touched. Phase samples are not exact transient peaks; high-water values are whole-process counters.",
                               "Small/class lifetimes use the same baseline trace; the large lifetime trace has 512 burst objects, 64 sparse survivors and three cycles.",
                               "No official score, hidden trace, cluster timing, libc comparison or general speed guarantee."], runs=[])
    jobs = [(repeat, v, "latency", w, n) for repeat in range(args.repetitions)
            for v in variants for w in ("hot", "mixed", "large") for n in (1, 8)]
    jobs += [(repeat, v, "throughput", w, n) for repeat in range(args.repetitions)
             for v in variants for w in ("small", "mixed", "large") for n in (1, 8)]
    jobs += [(repeat, v, "space", w, 8) for repeat in range(args.repetitions)
             for v in variants for w in ("lifetimes", "large_lifetimes")]
    if args.common_throughput_only:
        jobs = [job for job in jobs if job[2] == "throughput" and job[3] != "large"]
    random.Random(record["order_seed"]).shuffle(jobs)
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        for index, (repeat, variant, kind, workload, threads) in enumerate(jobs):
            directory = variants[variant]
            executable = "latency" if kind == "latency" else "benchmark_candidate" if kind == "throughput" else workload
            command = ["taskset", "-c", ",".join(map(str, cpus[:threads])), str(ROOT / directory / executable)]
            operations = args.latency_operations if kind == "latency" else args.large_operations if workload == "large" else args.throughput_operations
            if kind != "space":
                command += [str(threads), str(operations), "12345", workload]
            row = dict(repeat=repeat, variant=variant, kind=kind, workload=workload,
                       threads=threads, command=command, valid=False)
            try:
                run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90)
                row.update(exit=run.returncode, stdout=run.stdout, stderr=run.stderr)
                assert run.returncode == 0 and not run.stderr
                data = json.loads(run.stdout)
                row["metrics"] = data
                if kind == "latency":
                    validate_latency(data, threads, operations)
                elif kind == "space":
                    (validate_lifetimes if workload == "lifetimes" else validate_large_lifetimes)(data)
                else:
                    assert data["correct"] is True and data["operations"] == threads * operations
                    assert data["seconds"] > 0 and data["ops_per_second"] > 0
                row["valid"] = True
            except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, AssertionError) as exc:
                row["error"] = repr(exc)
            record["runs"].append(row)
            if (index + 1) % 8 == 0:
                print("Captured {}/{}; failures={}".format(index + 1, len(jobs),
                      sum(not r["valid"] for r in record["runs"])), flush=True)
    finally:
        record["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (args.output / "raw.json").write_text(json.dumps(record, indent=2) + "\n")
    # Reuse the existing latency/phase summary; keep kind in the workload name.
    rows = []
    for row in record["runs"]:
        if not row["valid"]:
            continue
        if row["kind"] == "throughput":
            continue
        normalized = dict(row, workload="lifetimes" if row["kind"] == "space" else row["workload"])
        for summary in summarize([normalized]):
            summary["workload"] = row["kind"] + "_" + row["workload"]
            rows.append(summary)
    grouped = {}
    for row in rows:
        key = tuple(row[k] for k in ("variant", "workload", "threads", "api_or_phase", "metric"))
        grouped.setdefault(key, []).append(row["median"])
    for row in record["runs"]:
        if row["valid"] and row["kind"] == "throughput":
            key = (row["variant"], "throughput_" + row["workload"], row["threads"], "all", "api_calls_per_second")
            grouped.setdefault(key, []).append(row["metrics"]["ops_per_second"])
    summary = [dict(variant=k[0], workload=k[1], threads=k[2], api_or_phase=k[3], metric=k[4],
                    repetitions=len(v), median=statistics.median(v), min=min(v), max=max(v))
               for k, v in sorted(grouped.items())]
    if summary:
        with (args.output / "summary.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(summary[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(summary)
    failures = sum(not r["valid"] for r in record["runs"])
    print("Comparison: {}/{} valid".format(len(jobs) - failures, len(jobs)))
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
