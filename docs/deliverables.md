# Submission deliverables

**libmemctl - SYSPROG10 - Systems Programming**
Jashandeep Singh - solo participant - IMT2024022.

| Required artifact | Review here |
| --- | --- |
| Complete C11 allocator | [Source](../src/allocator.c) and [four-function header](../include/libmemctl.h) |
| Build and execution instructions | [README](../README.md), [Makefile](../Makefile), [one-command evaluator](../scripts/evaluate.py) |
| Architecture and invariants | [Design note](architecture.md) |
| Performance, memory and measured trade-off | [Technical report](report.md) and [results index](../results/README.md) |
| Concise report | [PDF](../output/pdf/libmemctl-review.pdf) |
| Precompiled testable output | [Library, tests and provenance](../prebuilt/README.md) |
| Functional demonstration | [Terminal replay](../demo/terminal-replay.mp4), [run instructions and recording provenance](../demo/README.md) |
| Provenance and reproduction | [Sources](sources.md), [attribution](author.md), [reproduction guide](reproduction.md) |

Run `python3 scripts/evaluate.py` from the project root for an isolated build,
correctness tests, integrity verification and the working API example. Add
`--sanitizers` for ASan/UBSan and 59 annotation controls; `--official-dir` supplies
the separately obtained public test suite. The default check works offline.

The selected implementation is `src/allocator.c`. The baseline under `baselines/`
is provided only for a reproducible comparison and is not compiled by the default
build. Benchmark raw records, commands, hashes and limitations are included;
no official score or hidden-test result is claimed. Official kit files are obtained
separately; authored checks work offline.
