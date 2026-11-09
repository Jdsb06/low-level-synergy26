# Initial engineering report — 9 November 2026

## Result

A working original C11 allocator passes the six unchanged official SYSPROG10
public tests plus the independently authored suite. The latter also passed under
ASan/UBSan and ThreadSanitizer. This is a tested initial milestone with a measured
sharding improvement; it is not a final competitive score or submission package.

## Environment and method

Local Ubuntu/Linux x86-64, Intel i3-1315U, six physical cores/eight visible logical
CPUs; GCC 15.2.0. Both reference and candidates used `-O2 -g -std=c11`, identical
strict warning flags and pthreads. The one-shard build differs only in
`-DMEMCTL_SHARDS=1`. No dependencies or cloud services were installed/used.

The runner restricts each process to a declared CPU set, choosing one hardware
thread per physical core before SMT siblings. Workers may migrate within that
set. It does not enforce a performance governor, fixed clock, thermal state or
desktop isolation. These limits make the results local development evidence.

The initial sweep ran 180 timing processes: three algorithms × four thread counts
× three workloads × five repetitions. Each worker performed 20,000 measured API
calls after 2,000 warmup calls. Some fast-candidate cells lasted less than one
millisecond, so their speedup ratios are exploratory and are not headline claims.

A follow-up ran 20 timing processes using 500,000 calls per worker, two shard
counts, one/eight threads and five repetitions. The workload selects mixed sizes
from 1 byte through 16,385 bytes, holds up to 128 objects per worker and uses malloc,
free and realloc. Calls per second count public API invocations, including realloc
as one call. Init/warmup/thread creation/final cleanup are excluded; start/finish
barrier overhead is included. Endpoint checks run identically in each benchmark;
separate correctness tests verify complete payloads. Workload order is randomized
with a fixed recorded seed; runs have identical traces and fresh processes.

## Longer sharding comparison

Million API calls per second; median of five processes, min–max in parentheses:

| Workers | One shard | Eight shards | Eight/one throughput |
| --- | ---: | ---: | ---: |
| 1 | 33.156 (32.432–33.211) | 32.192 (31.759–32.965) | 0.971×, about 3% lower |
| 8 | 15.962 (15.855–16.422) | 54.134 (53.105–64.431) | 3.391× |

This supports eight shards for this concurrent development trace. It does not
establish universal superiority, linear scaling, or performance versus libc.
The API and region policy remain identical between these two variants.

## Space experiment

25 separate space experiments were also recorded across the two sweeps. Each
holds 4,096 allocations with identical requested sizes and fully touches all
requested bytes (14,504,946 bytes total). It samples `/proc/self/status` before,
while all objects are held, after free and after optional trim. Five-process
medians from the initial sweep:

| Metric | Supplied reference | Eight-shard allocator |
| --- | ---: | ---: |
| VmSize growth while objects are held | 29,124 KiB | 18,332 KiB |
| VmRSS growth while objects are held | 29,124 KiB | 17,604 KiB |
| VmSize retained after free | 0 KiB | 320 KiB |
| VmSize retained after trim | 0 KiB | 0 KiB |

Virtual-memory growth is about **37.1% lower** on this trace. Counter sampling
includes process/runtime noise and is not a universal peak-space score. The
retention/trim distinction is deliberate: caching buys reuse speed at a memory
cost. Dedicated large mappings and excess empty regions are returned immediately.
Mapping interception in the independent tests separately confirms no allocator
mappings remain after trim, while the main tests require the cache to stay within
2 MiB before trim.

## Verification actually executed

- Strict warning-clean native build; forbidden-symbol checker, with a negative
  control object that calls malloc correctly rejected.
- Six official tests against both supplied reference and candidate; both 6/6.
- Independent suite on eight-shard and one-shard builds: zero-size uniqueness,
  class/large boundaries, alignment, calloc zeroing, overflow, mapping failures,
  failed-realloc preservation, cross-thread ownership and 240,000 mixed operations.
- Same independent suite under ASan/UBSan and TSan: exited 0, no diagnostics.
  LeakSanitizer was explicitly disabled because of the host tracing limitation;
  ASan sub-block-boundary coverage is limited without allocator annotations.
- GCC `-fanalyzer`: compilation exited 0 with strict warnings and no diagnostics.
- All 200 timed development runs exited 0 with endpoint checks reporting correct;
  this is not a substitute for the full correctness suites or hidden tests.

The official Makefile initially built successfully but could not execute its
test when given an absolute BUILD_DIR: it prepended `./`. We preserved the source
and invoked the generated binary directly with a timeout; all six tests passed.
The first official-kit clone failed because restricted shell DNS was unavailable;
the authorized network retry succeeded. These failures are retained in the log.

## Remaining work

Longer adversarial fragmentation and ownership-transfer workloads, per-block
debug annotations, clean Ubuntu/second-machine reproduction, clearer measurements
of allocator-attributable peak memory and workload-dependent contention remain.
Final normalization baselines/targets and registered team details are not verified.
The final demo recording, submission form review, local packaging and authorized
repository publication/submission have not happened. No NHPC performance run or
MPI/InfiniBand result is claimed.

Raw evidence and exact commands: `results/*/raw.json`, `results/*/summary.csv`,
and the competition experiment log. The public kit is pinned in
`../docs/PROBLEM_SELECTION.md`. Figure generation reads those real measurements.
