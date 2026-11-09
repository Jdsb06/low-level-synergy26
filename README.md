# libmemctl — SYSPROG10

An original C11 memory allocator for the released Synergy '26 problem. It implements
`my_malloc`, `my_free`, `my_realloc` and `my_calloc` using Linux anonymous private
mappings, reusable size-class regions and POSIX mutexes. No standard heap allocator
is called by the implementation. The optional `memctl_trim()` releases cached empty
regions. **Checkpoint 2 is complete:** sparse-region growth, multi-million-operation
stress tests and a GCC 9 build/compute-node execution on NHPC are verified. Read
[CHECKPOINT2.md](CHECKPOINT2.md) for current evidence and trade-offs. This remains
a development checkpoint, not a final submission.

## Build, tests and demo

On Linux with a C11 compiler, Make, binutils, pthreads and Python 3.6+ for symbol
checks (Python 3.9+ for the full benchmark evidence runner):

```bash
make
make check
make sanitize
make soak fragmentation
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
of bugs. Suballocation boundaries are not automatically visible to ASan.

See [ARCHITECTURE.md](ARCHITECTURE.md), [submission checklist](SUBMISSION_CHECKLIST.md)
and [source attribution](SOURCES.md). Cluster validation is separate from the local
performance measurements. Official submission still requires approval and an actual
receipt; publishing a development checkpoint is not submitting an entry.
