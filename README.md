# libmemctl — SYSPROG10

A C11 memory allocator for the Synergy '26 Low-Level Hackathon, Systems Programming
track. **Jashandeep Singh · solo · IMT2024022.** It implements `my_malloc`, `my_free`,
`my_realloc` and `my_calloc` using private anonymous Linux mappings and pthread
mutexes. The allocator never forwards to the system heap allocator.

The repository contains the complete source, independent tests, measured design
trade-offs, a report, an actual terminal demonstration and verified Linux binaries.
Start with [the submission guide](SUBMISSION.md) or [the current technical report](TECHNICAL_REPORT.md).

## Build and verify

Linux x86-64; GCC or another C11 compiler, Make, binutils, pthreads, coreutils and
Python 3.9+ for all verification scripts. The core build and tests need no downloads
or third-party Python packages. GCC 9.3.1 and 13.4 builds have been executed on
Linux 3.10/glibc 2.17 and Ubuntu 26.04.1/glibc 2.43 respectively.

```bash
python3 scripts/verify_submission.py
make check
make sanitize
make soak profiles benchmark
bash demo/run_demo.sh
```

`make check` checks forbidden allocator symbols and exercises alignment, zero-size
semantics, overflow, failed mapping/reallocation, reuse, cross-thread ownership,
240,000 seeded mixed operations, the 2 MiB empty-cache limit and complete reclamation.
`make sanitize` runs ASan/UBSan plus 59 positive/negative annotation controls;
LeakSanitizer is disabled. These tests do not require the official kit.

For a testable precompiled build:

```bash
sha256sum -c prebuilt/SHA256SUMS
prebuilt/bin/test_allocator
prebuilt/bin/soak 12500 20261109 128
prebuilt/bin/large_lifetimes
```

See [prebuilt provenance and compatibility](prebuilt/README.md). Rebuild from source
for another target. The library is `build/libmemctl.a` (or `prebuilt/lib/libmemctl.a`)
and its public header is [include/libmemctl.h](include/libmemctl.h). Compile callers
with `-Iinclude`, the library path and `-pthread`; there is no libc symbol interposition.

The unchanged official test suite is deliberately obtained separately:

```bash
make public-test OFFICIAL_DIR='/path/to/LLH-26/Systems Programming/SYSPROG10'
```

## Design and measured result

Eight shards reduce lock contention. Small size classes use compact starter regions
and grow after demand; larger requests use dedicated mappings, with bounded reuse
above 64 KiB through 1 MiB. Small and large empty caches share an exact 2 MiB mapping
budget. `memctl_trim()` releases empty mappings; live allocations remain valid.
See [architecture and invariants](ARCHITECTURE.md).

Compared with the exact previous authored implementation on identical laptop traces,
eight-thread large-object throughput rose **69.6%** and malloc p99 fell **38.1%**.
The cost was **34.7% more virtual memory** during the large burst and an **11.1%
lower median** on the longer eight-thread mixed trace. These are local measurements,
with overlapping mixed-workload ranges, rather than an official score or universal
speedup. [Current report](TECHNICAL_REPORT.md) explains methods, raw data and limits.

To reproduce that comparison without an official kit or Git history:

```bash
make profiles benchmark
mkdir -p build-checkpoint4
cp baselines/checkpoint4_allocator.c build-checkpoint4/allocator.c
make BUILD_DIR=build-checkpoint4 ALLOCATOR_SRC=build-checkpoint4/allocator.c profiles benchmark
python3 scripts/compare_large_cache.py --repetitions 5 --output results/new-cache-comparison
python3 scripts/compare_large_cache.py --repetitions 5 --throughput-operations 5000000 --common-throughput-only --output results/new-common-confirmation
```

These comparisons require eight available logical CPUs. Disable large reuse with
`make BUILD_DIR=build-no-large-cache CPPFLAGS='-D_GNU_SOURCE -Iinclude -DMEMCTL_LARGE_CACHE=0' check`.
The historical experiments, including rejected trials, remain in `results/` and
[checkpoint reports](CHECKPOINT5.md). [INITIAL_REPORT.md](INITIAL_REPORT.md) describes
the first implementation and is retained as history.

## Report, demo and package

- [Current technical report](TECHNICAL_REPORT.md) and [three-page PDF](output/pdf/libmemctl-review.pdf).
- [Terminal replay video](demo/terminal-replay.mp4), [original event recording](demo/terminal.cast)
  and [speaker notes](demo/SPEAKER_NOTES.md). The video replays a real successful test
  run; it is not a desktop screen recording.
- [Participant and AI attribution](AUTHOR.md), [sources](SOURCES.md) and
  [delivery checklist](SUBMISSION_CHECKLIST.md).

```bash
python3 scripts/package_review.py
```

This verifies the deliverables and creates reproducible ZIP/tar archives in `dist/`,
including the committed prebuilt library/executables, per-file manifests and outer
checksums. No official kit, credentials or other competitions are included. Optional
report/plot/video regeneration dependencies are pinned separately in
`requirements-review.txt` and `requirements-plots.txt`; they are unnecessary for use.

Invalid/double frees and simultaneous unsynchronized access to one object are outside
the API contract. Signal safety, fork-time lock repair, arbitrary-platform support
and general-purpose malloc replacement are not provided. The exact selected source
and artifact provenance are recorded in [SUBMISSION.json](SUBMISSION.json).
