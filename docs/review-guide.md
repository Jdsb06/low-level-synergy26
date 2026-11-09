# Review libmemctl

**SYSPROG10 · Systems Programming · Jashandeep Singh · solo · IMT2024022.**
Run all commands from the project root, the directory containing Makefile.

## Recommended review order

1. [Project overview](../README.md): purpose, quick start and the measured trade-off.
2. [Example](../examples/basic.c) and [public API](../include/libmemctl.h): use the library.
3. [Architecture](architecture.md): layout, immutable ownership, locking and reclamation.
4. [Report](report.md): methods, raw data, validation coverage and limitations.
5. [Three-page PDF](../output/pdf/libmemctl-review.pdf) and [terminal replay](../demo/terminal-replay.mp4).

## Execute the selected implementation

```bash
python3 scripts/verify_submission.py
make check
make sanitize
bash demo/run_demo.sh
```

The default build selects only `src/allocator.c`. No official kit or network is
needed. The independent suite checks the API contract, failure handling, cache
accounting, complete reclamation and synchronized ownership transfer. Sanitizer
controls require 25 valid accesses to succeed and 34 deliberate errors to be detected.

[Prebuilt output](../prebuilt/README.md) provides the verified GCC9/Linux library
and executable tests. [Reproduction](reproduction.md) includes the official-suite
path, optional stress/profiles and exact offline comparison commands. For extracted
archives also run `sha256sum -c MANIFEST.sha256` before execution.

## Evidence and attribution

The [report](report.md) describes the selected implementation. [History](history/README.md)
contains earlier results and rejected trials; those are retained for traceability,
not additional required reading or alternate submission candidates. The original
recording has not been edited; older printed document names map to the reorganized
docs/history locations. Its allocator hash still matches the selected source.

AI assistance and its participant-reported SPOC permission are disclosed in
[attribution](author.md). [Sources](sources.md) pins the official statement; official
kit copies are not redistributed. No official score or private-test result is claimed.

See [the submission guide](submission.md) for the deliverable map and final owner
steps. Public visibility and form submission remain owner actions; neither is
changed by a build, a package check or a Git push.
