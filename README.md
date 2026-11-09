# libmemctl — SYSPROG10

An original C11 memory allocator for the released Synergy '26 problem. It implements
`my_malloc`, `my_free`, `my_realloc` and `my_calloc` using Linux anonymous private
mappings, reusable size-class regions and POSIX mutexes. No standard heap allocator
is called by the implementation. The optional `memctl_trim()` releases cached empty
regions. **Checkpoint 6 is complete:** current-source GCC 9/NHPC and
Ubuntu/GCC 13 execution, a three-page report, an actual terminal demo and reproducible
review packaging. Start with [REVIEW_GUIDE.md](REVIEW_GUIDE.md) and
[CHECKPOINT6.md](CHECKPOINT6.md). [CHECKPOINT5.md](CHECKPOINT5.md) documents the
current cache policy, measured gains and costs.
[CHECKPOINT4.md](CHECKPOINT4.md) established the earlier latency/lifetime baseline.
[CHECKPOINT3.md](CHECKPOINT3.md) records allocator-aware ASan guards and 51 controls;
[CHECKPOINT2.md](CHECKPOINT2.md) records region-policy measurements and NHPC validation. This remains
a development checkpoint, not a final submission.

## Build, tests and demo

On Linux with a C11 compiler, Make, binutils, pthreads and Python 3.6+ for symbol
checks (Python 3.9+ for the full benchmark evidence runner):

```bash
make
make check
make sanitize  # Python 3.9+ for the annotation-control runner
make soak fragmentation
make profiles build/latency_libc build/lifetimes_libc
```

`make check` runs the forbidden-symbol check and independent tests, with a timeout.
The tests include mapping-failure injection, overflow, alignment, size boundaries,
cross-thread realloc/free after producer exit, 240,000 seeded mixed operations,
bounded cache retention, and complete mapping reclamation after trim.

From this directory, with the unchanged official kit at the default sibling path:

```bash
make public-test
make benchmark reference
./build/benchmark_candidate 8 500000 12345 mixed
./build/benchmark_candidate space
```

Override `OFFICIAL_DIR` if the official SYSPROG10 directory is elsewhere. Its path
may contain spaces. Official statements/tests stay outside this project and are
not included in a submission. Ordinary `make` and independent checks do not need
the kit or network access.

The above benchmark has 2,000 warmup calls per worker, then counts API calls in
the measured loop. It is an authored development workload, not the official grader.
See [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for a short live demonstration.

## Reproduce comparisons

```bash
make benchmark reference
make BUILD_DIR=build-single CPPFLAGS='-D_GNU_SOURCE -Iinclude -DMEMCTL_SHARDS=1' check benchmark
python3 scripts/run_benchmarks.py --repetitions 5 --operations 20000 --output results/new-sweep
python3 scripts/run_benchmarks.py --repetitions 5 --operations 500000 --algorithms one_shard eight_shards --threads 1 8 --workloads mixed --output results/new-confirmation
```

Each run uses a new process. The runner records exact invocations, binary/source
hashes, seeds, affinity, environment, outputs, failures and medians. The plot is
optional; only it needs matplotlib (`requirements-plots.txt` records the version
used). No packages were installed during this milestone.

```bash
python3 scripts/plot_results.py
```

Recorded local results: [report](TECHNICAL_REPORT.md),
[longer comparison](results/sharding-confirmation-2026-11-09/summary.csv),
[exploratory sweep](results/local-2026-11-09/summary.csv).
The checkpoint-1 comparison found 3.39× the throughput of the one-shard variant at eight
threads, with about a 3% loss at one thread. These are laptop development results;
no official score or advantage over libc is claimed.

## Latency and lifetime profiles

```bash
make profiles build/latency_libc build/lifetimes_libc
make BUILD_DIR=build-single CPPFLAGS='-D_GNU_SOURCE -Iinclude -DMEMCTL_SHARDS=1' profiles
python3 scripts/profile_workloads.py --repetitions 5 --operations 10000 --output results/new-profile
```

The runner compares the same traces in fresh processes, preserves failures and
records per-API percentiles, calibration, source/binary hashes and phase memory
samples. The eight-thread hot trace benefits from sharding; mixed/large tails are
substantially higher than glibc here. After prior bursts, sparse survivors pin
large regions. Read checkpoint 4 before generalizing earlier cold sparse results.
Optional plot: `MPLCONFIGDIR=/tmp/libmemctl-matplotlib python3 scripts/plot_checkpoint4.py`.
The user authorized regular reviewed development pushes; official upload remains
separate.

## Capped large-object reuse comparison

Requests above 64 KiB through 1 MiB can reuse dedicated mappings; the shared empty
cache remains capped at 2 MiB. The current large trace is faster with more held VM;
eight-thread mixed throughput has a lower median. See checkpoint 5 for complete
ranges, short-run variability and the longer confirmation. Disable reuse with:

```bash
make BUILD_DIR=build-no-large-cache CPPFLAGS='-D_GNU_SOURCE -Iinclude -DMEMCTL_LARGE_CACHE=0' check
```

The `ALLOCATOR_SRC` build variable supports reproducing an earlier authored source
in a separate build directory. Checkpoint 5 gives exact baseline and comparison
commands; historical benchmark numbers are not automatically current scores.

## Review package and demonstration

Participant: Jashandeep Singh, solo, IMT2024022; see [AUTHOR.md](AUTHOR.md).

```bash
python3 scripts/package_review.py
bash demo/run_demo.sh
```

The explicit `PACKAGE_CONTENTS.json` allowlist produces content-addressed ZIP/tar
archives with per-file checksums under ignored `dist/`. A separately verified
prebuilt input can be included with `--prebuilt PATH`; see checkpoint 6.
The PDF report is [here](output/pdf/libmemctl-review.pdf); the preserved actual
terminal run and its replay video are in [demo](demo/SPEAKER_NOTES.md).
Report/video regeneration uses optional dependencies in `requirements-review.txt`,
DejaVu fonts and ffmpeg; core builds and tests do not require them.
The earlier authored baseline in `baselines/` enables offline comparisons.

## Contract and boundaries

Zero-size calls return distinct freeable pointers. Failed realloc leaves the old
object intact. All public pointers meet `_Alignof(max_align_t)`. The implementation
supports the selected Linux x86-64 target, rejects arithmetic overflow and does not
interpose libc symbols. Different objects may be used concurrently; callers must
synchronize ownership and access to the same object.

Invalid/double frees and accesses beyond requested bounds are outside the official
contract. This allocator is not async-signal-safe, does not provide fork-time lock
repair, and is not a general production malloc replacement. ASan/UBSan and TSan
were executed successfully on independent tests, but that does not prove absence
of bugs. ASan builds explicitly protect suballocation boundaries and cached freed
blocks; address reuse and unmapped-memory faults retain the limits in checkpoint 3.

See [ARCHITECTURE.md](ARCHITECTURE.md), [submission checklist](SUBMISSION_CHECKLIST.md)
and [source attribution](SOURCES.md). Cluster validation is separate from the local
performance measurements. Official submission still requires approval and an actual
receipt; publishing a development checkpoint is not submitting an entry.
