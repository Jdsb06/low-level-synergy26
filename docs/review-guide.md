# Review libmemctl

**SYSPROG10 · Systems Programming · Jashandeep Singh · solo · IMT2024022.**

## One-command evaluation

From the project root, with the dependencies listed in README:

```bash
python3 scripts/evaluate.py
```

This verifies every selected artifact and local document link, builds the allocator
in a fresh directory, checks forbidden symbols, executes independent correctness
checks, and compiles/runs the public-API example. It saves exact invocations, compiler
version, stdout/stderr, exit codes and source hash in `build-evaluate-*/evaluation.json`.
Each run has separate build directories; an earlier build cannot satisfy its checks.

For the sanitizer controls and the separately obtained public suite:

```bash
python3 scripts/evaluate.py --sanitizers --official-dir '/path/to/LLH-26/Systems Programming/SYSPROG10'
```

The official kit is not bundled. `--sanitizers` runs ASan/UBSan, the independent
suite and all 59 annotation controls: 25 valid accesses must succeed and 34 deliberate
errors must be detected. LeakSanitizer is disabled. The default command needs no
account, network or official files. This does not run hidden tests or assign a score.

## Evidence against the official rubric

| Category | Official weight | What to inspect |
| --- | ---: | --- |
| Correctness and API compliance | 40 | [Four-function header](../include/libmemctl.h), [allocator](../src/allocator.c), [failure/reuse/overflow/concurrency tests](../tests/test_allocator.c), [annotation controls](../tests/test_annotations.c) |
| Throughput and scalability | 25 | [Report methodology and results](report.md#throughput-and-latency), [raw five-process comparison](../results/benchmarks/cache-reuse/raw.json), [longer common confirmation](../results/benchmarks/common-workloads/raw.json), [current 1/2/4/8-thread scaling](report.md) |
| Space efficiency | 20 | [Space/reclamation measurements and costs](report.md#space-and-adoption-decision), [full-touch lifetime harness](../bench/lifetimes.c), bounded-cache and trim assertions in the independent suite |
| Architecture and engineering quality | 15 | [Ownership, locks and invariants](architecture.md), [reproduction guide](reproduction.md), [working example](../examples/basic.c), [sources and attribution](sources.md) |

Weights are from the [pinned official statement](https://github.com/rudra-shroff06/LLH-26/blob/d23ac1d865df4cdacf7ad8e9fff3e1d560761c46/Systems%20Programming/SYSPROG10/PROBLEM.md).
Correctness gates performance credit. Organizer normalization values and hidden
traces are unavailable; the table maps evidence and does not award points.

## Recommended reading order

1. [Project overview](../README.md): purpose, quick start and balanced results.
2. [Architecture](architecture.md): layout, immutable ownership, locks and reclamation.
3. [Report](report.md): methods, raw data, test coverage and known limitations.
4. [Three-page PDF](../output/pdf/libmemctl-review.pdf) and [actual terminal replay](../demo/terminal-replay.mp4).

The default Makefile compiles only `src/allocator.c`. The [results index](../results/README.md)
organizes the selected benchmark datasets, correctness runs and compatibility checks.
Original capture logs are preserved byte-for-byte; their recorded paths and identifiers
reflect the capture environment. [Prebuilt output](../prebuilt/README.md) includes the
verified Linux x86-64 library and test executables for a quick independent run.

The principal trade-off is explicit: bounded large reuse improves the recorded
large trace, while raising burst VM and lowering the mixed-throughput median.
Sparse live objects can pin regions. See the report for ranges, environmental
limits and sanitizer coverage; no universal speedup or official score is claimed.

AI assistance and participant-reported SPOC permission are disclosed in
[attribution](author.md). The [deliverable map](deliverables.md) provides direct links to every artifact.
