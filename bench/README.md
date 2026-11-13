# Measurement harnesses

These are authored measurement programs, not the official grader. Run commands
from the repository root; build with `make benchmark profiles`.

| File | Measures |
| --- | --- |
| [benchmark.c](benchmark.c) | Mixed API-call throughput for small/mixed/large sizes, plus a fully touched memory sample |
| [latency.c](latency.c) | Per-API latency distributions, including clock-bracketing overhead |
| [lifetimes.c](lifetimes.c) | Three burst/sparse/refill/free/trim cycles with workers kept alive and payloads touched |
| [fragmentation.c](fragmentation.c) | Sparse survivors across size classes and the cost of pinned regions |
| [profile.h](profile.h) | Shared workload and memory-accounting helpers |

`large_lifetimes` is a separately compiled configuration of `lifetimes.c`, covering
requests above 64 KiB. Its RSS probe uses smaps_rollup where available and a checked
smaps sum on older kernels. Memory counters include process/harness noise; phase
samples are not exact transient peaks.

The [reproduction guide](../docs/reproduction.md) gives exact comparison commands,
operation counts and CPU requirements. The [results index](../results/README.md#benchmarks)
links the selected raw runs and summaries. Timings must be compared on identical
traces and environments; no official score or universal speedup is implied.
