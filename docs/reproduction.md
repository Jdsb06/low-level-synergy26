# Build, verify and reproduce

Run every command below from the project root, the directory containing Makefile.
Core builds need Linux x86-64, a C11 compiler, Make, binutils, pthreads, coreutils
and Python 3.9+ for the complete verification/comparison tooling. GCC9/Linux3.10/
glibc2.17 and GCC13/Ubuntu26.04.1/glibc2.43 are executed compatibility results,
not a guarantee for every architecture or runtime.

## Build and example

For a fresh isolated check with recorded commands and results:

```bash
python3 scripts/evaluate.py
python3 scripts/evaluate.py --sanitizers --official-dir '/path/to/LLH-26/Systems Programming/SYSPROG10'
```

The default run checks authored tests and the example offline. Official tests and
sanitizers are explicit additions; the official kit is obtained separately. Build
outputs and `evaluation.json` stay in unique ignored `build-evaluate-*` directories.
For manual builds instead:

```bash
make check
cc -std=c11 -Wall -Wextra -Werror -Iinclude examples/basic.c build/libmemctl.a -pthread -o build/example
./build/example
python3 scripts/verify_submission.py
```

Link other callers against `build/libmemctl.a` with `-Iinclude -pthread`. The public
header declares the four required `my_*` functions and optional `memctl_trim()`.
There is no libc symbol interposition. The example handles allocation failures and
checks zeroing/preservation before freeing its storage.

For the previously built GCC9 output:

```bash
sha256sum -c prebuilt/SHA256SUMS
sha256sum -c prebuilt/BUILD_INPUTS.sha256
prebuilt/bin/test_allocator
prebuilt/bin/soak 12500 20261109 128
prebuilt/bin/large_lifetimes
```

See [prebuilt provenance](../prebuilt/README.md).

## Tests, stress and official suite

```bash
make sanitize
make soak fragmentation
make profiles benchmark
bash demo/run_demo.sh
```

Sanitizer controls run both valid and deliberately invalid accesses in subprocesses.
All 59 controls should pass; the 34 deliberate errors must be detected. LeakSanitizer
is disabled for the documented host limitation. The live demo prints real independent
checks and reads recorded benchmark summaries; it does not create a new timing claim.
The [demo guide](../demo/README.md) links the actual MP4/cast/log and their provenance.

Obtain the unchanged official kit separately; no kit files are bundled:

```bash
make public-test OFFICIAL_DIR='/path/to/LLH-26/Systems Programming/SYSPROG10'
```

The Makefile's default sibling location also works if the kit is installed there.
The kit is required only for official public tests or reference comparisons, not
for the authored tests, library, example or current-vs-previous comparison below.
See [sources and pinned statement](sources.md).

## Reproduce the selected measured trade-off

```bash
make profiles benchmark
mkdir -p build-baseline
cp baselines/allocator.c build-baseline/allocator.c
make BUILD_DIR=build-baseline ALLOCATOR_SRC=build-baseline/allocator.c profiles benchmark
python3 scripts/compare_large_cache.py --repetitions 5 --output results/new-cache-comparison
python3 scripts/compare_large_cache.py --repetitions 5 --throughput-operations 5000000 --common-throughput-only --output results/new-common-confirmation
```

This needs eight available logical CPUs. It compares the exact authored baseline
with the selected implementation in separate executables. Runners record invocations,
environment, source/binary hashes, affinity, seeds, failures and medians. Measurements
are workload- and machine-dependent; [the report](report.md) retains costs and ranges.
For a short execution check, lower repetitions/operation counts using the runner's
`--help` options; do not treat a short check as a reproduction of the headline timing.

To disable large-object reuse without changing the selected source:

```bash
make BUILD_DIR=build-no-large-cache CPPFLAGS='-D_GNU_SOURCE -Iinclude -DMEMCTL_LARGE_CACHE=0' check
```

The additional cached-large sanitizer controls target the default enabled build.

## Current-source thread scaling

This separate check covers 1/2/4/8 threads on the selected source without an
alternate allocator or official kit. It needs eight available logical CPUs:

```bash
make benchmark
python3 scripts/run_benchmarks.py --algorithms eight_shards --threads 1 2 4 8 --repetitions 5 --operations 5000000 --workloads small mixed --output results/new-current-common
python3 scripts/run_benchmarks.py --algorithms eight_shards --threads 1 2 4 8 --repetitions 5 --operations 25000 --workloads large --output results/new-current-large
```

Use a fresh checkout/build for measurement. These runs include60 timing processes
and10 space samples; read the limits and ranges in the report. The different traces
and durations must not be combined with the earlier comparison to invent a score.



## Generate an archive

```bash
python3 scripts/package_review.py
```

The explicit inventory is `scripts/package-contents.json`. Output in `dist/`
contains source, docs, media and the verified prebuilt output, with normalized
ZIP/tar metadata, per-file `MANIFEST.sha256` and outer `.SHA256SUMS`. Identical inputs
produce identical archives. Verify the outer checksum, extract, then run from the
extracted `libmemctl-review/` directory:

```bash
sha256sum -c MANIFEST.sha256
python3 scripts/verify_submission.py
make check
```

## Optional report / video / plot regeneration

These are unnecessary for build, tests or reading the included deliverables.
Versions used are recorded in `scripts/requirements-review.txt` and
`scripts/requirements-plots.txt`; the report/video scripts also use DejaVu fonts
and ffmpeg. Figure scripts read the preserved real measurements. Keep generated
artifacts separate and update manifests if intentionally replacing a selected
report, recording, source or shipped binary.
