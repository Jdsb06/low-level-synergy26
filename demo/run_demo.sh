#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
export LC_ALL=C
printf '\nlibmemctl | SYSPROG10 | Jashandeep Singh | solo | IMT2024022\n'
printf 'Reproducible C11 allocator - actual independent test run\n\n'
printf '$ sha256sum src/allocator.c\n'
sha256sum src/allocator.c
sleep 2
printf '\n$ make --silent CC=%s BUILD_DIR=build-demo check\n' "${CC:-cc}"
make --silent CC="${CC:-cc}" BUILD_DIR=build-demo check
sleep 3
printf '\nDesign: 8 shards, 64 small size classes, reusable private anonymous mappings.\n'
printf 'Large reuse: >64 KiB through 1 MiB; all empty caches share a 2 MiB cap.\n'
printf 'Cross-thread frees use immutable region ownership; trim touches no live object.\n'
sleep 3
printf '\nRecorded five-process comparison (shared laptop; not official scores):\n'
python3 - <<'PY'
import csv
from pathlib import Path
main = list(csv.DictReader(Path('results/benchmarks/cache-reuse/summary.csv').open()))
long = list(csv.DictReader(Path('results/benchmarks/common-workloads/summary.csv').open()))
for rows, workload, metric, label, scale in [
    (main, 'throughput_large', 'api_calls_per_second', 'Large throughput, 8 threads (calls/s)', 1),
    (main, 'latency_large', 'p99_ns', 'Large malloc p99, 8 threads (us)', 1000),
    (long, 'throughput_mixed', 'api_calls_per_second', 'Mixed throughput, 8 threads (M calls/s)', 1000000)]:
    values=[]
    baseline = next(row['variant'] for row in rows if row['variant'] != 'capped_cache')
    for variant in (baseline, 'capped_cache'):
        row=next(r for r in rows if r['variant']==variant and r['workload']==workload
                 and r['threads']=='8' and r['metric']==metric
                 and r['api_or_phase']==('malloc' if workload.startswith('latency') else 'all'))
        values.append(float(row['median'])/scale)
    print('{}: {:.3f} -> {:.3f}'.format(label,*values))
PY
printf 'Cost: large burst VM rose 34.7%%; mixed throughput median fell 11.1%%.\n'
printf 'Limits: sparse survivors still pin regions; cache misses still have long tails.\n'
sleep 4
printf '\nReview: docs/architecture.md, docs/report.md and raw results.\n'
printf 'AI assistance disclosed in docs/author.md; permission is user-reported SPOC approval.\n'
printf 'See docs/review-guide.md for the rubric and reproducible evaluation.\n'
