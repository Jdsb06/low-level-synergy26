"""Compare checkpoint-1 binaries against the current region policy, without synthetic data."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=5)
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("positive repetitions required")
    cpus = sorted(os.sched_getaffinity(0))
    if len(cpus) < 8:
        parser.error("recorded comparison requires eight available logical CPUs")
    variants = {"checkpoint1": "build-checkpoint1", "compact_growth": "build"}
    record = {"started_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "local development comparison, shared laptop, no fixed clock",
              "baseline_source_sha256": "1ae80e8c7eafe120799baea261af29714dcb05da063cb16c908bc959095af3fd",
              "candidate_source_sha256": hashlib.sha256((ROOT / "src/allocator.c").read_bytes()).hexdigest(),
              "binaries": {}, "runs": [], "order_seed": 7919}
    for name, directory in variants.items():
        record["binaries"][name] = {binary: hashlib.sha256((ROOT / directory / binary).read_bytes()).hexdigest()
                                    for binary in ("fragmentation", "benchmark_candidate")}
    jobs = [(repeat, name, workload, workers) for repeat in range(args.repetitions)
            for name in variants for workload in ("small", "mixed") for workers in (1, 8)]
    jobs += [(repeat, name, "fragmentation", 8) for repeat in range(args.repetitions) for name in variants]
    random.Random(record["order_seed"]).shuffle(jobs)
    failed = False
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        for repeat, name, workload, workers in jobs:
            directory = variants[name]
            command = ["taskset", "-c", ",".join(map(str, cpus[:workers]))]
            if workload == "fragmentation":
                command += [f"{directory}/fragmentation"]
            else:
                command += [f"{directory}/benchmark_candidate", str(workers), "500000", "12345", workload]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
            row = {"repeat": repeat, "variant": name, "workload": workload,
                   "workers": workers, "command": command, "returncode": result.returncode,
                   "stdout": result.stdout, "stderr": result.stderr}
            try:
                row["metrics"] = json.loads(result.stdout)
                failed |= result.returncode != 0 or not row["metrics"]["correct"]
            except (ValueError, KeyError):
                failed = True
            record["runs"].append(row)
    finally:
        record["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (args.output / "raw.json").write_text(json.dumps(record, indent=2) + "\n")
    rows = []
    for name in variants:
        for workload, workers in [("small", 1), ("small", 8), ("mixed", 1), ("mixed", 8), ("fragmentation", 8)]:
            matches = [r for r in record["runs"] if r["variant"] == name and
                       r["workload"] == workload and r["workers"] == workers]
            if len(matches) != args.repetitions or any(r["returncode"] != 0 for r in matches):
                continue
            if workload == "fragmentation":
                values = [r["metrics"]["held_vm_kib"] - r["metrics"]["idle_vm_kib"] for r in matches]
                unit = "held_vm_growth_kib"
            else:
                values = [r["metrics"]["ops_per_second"] for r in matches]
                unit = "api_calls_per_second"
            rows.append({"variant": name, "workload": workload, "workers": workers,
                         "repetitions": len(values), "metric": unit,
                         "median": statistics.median(values), "min": min(values), "max": max(values)})
    with (args.output / "summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(row)
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
