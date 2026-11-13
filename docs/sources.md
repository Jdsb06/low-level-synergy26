# Sources and provenance

## Problem contract

Selected challenge: **SYSPROG10 - libmemctl: High-Throughput Thread-Safe Memory
Allocator**, Synergy '26 Low-Level Hackathon, Systems Programming.

- [Official repository](https://github.com/rudra-shroff06/LLH-26).
- [Pinned statement](https://github.com/rudra-shroff06/LLH-26/blob/d23ac1d865df4cdacf7ad8e9fff3e1d560761c46/Systems%20Programming/SYSPROG10/PROBLEM.md), retrieved 9 November 2026 after release, before implementation.
- Pinned commit: `d23ac1d865df4cdacf7ad8e9fff3e1d560761c46`.
- Statement SHA-256: `9786389183b8088fb8d8066e6153a05201ea93d721365317099a1ce2fd838220`.
- Public-runner SHA-256: `37febda4b4a693c4fb5d315f27276aa12be8677c1e8576e2571c5ab31bf7a03c`.

On 10 November, official main was rechecked at
`05b1aa7445770408bb4307c7f8c8999b502c0a6f`. All six selected SYSPROG10 files were
byte-identical to the pinned kit. This is the recorded verification date, not a
claim about later organizer changes.

The four API declarations and semantics come from the official kit. The statement's
discussion of regions, size classes, contention and reclamation informed the design.
The allocator, independent tests, workload harnesses and documentation were authored
for the event. No third-party allocator implementation was copied. C/POSIX/Linux
mapping, synchronization and non-allocating utility interfaces are used.

## Validation and measurements

Official public tests were executed unchanged from the separately obtained kit.
Official PDFs, starter copies and test-runner source are not redistributed. Authored
checks run offline; `--official-dir` adds the separately obtained public tests.

[Recorded results](../results/README.md) preserve exact invocations, dates, toolchains,
seeds, source/binary hashes, repetitions, ranges and limitations. The selected
[comparison baseline](../baselines/README.md) is our authored implementation with a
pinned hash, not the official one-mapping-per-allocation starter. Raw captures are
unchanged; display labels and repository paths are explained by the results index.

## Sanitizer interface

Allocator-aware annotations use the public ASan poison/unpoison interface, reviewed
9 November 2026 in the installed GCC15 header and primary documentation:
[LLVM interface](https://github.com/llvm/llvm-project/blob/main/compiler-rt/include/sanitizer/asan_interface.h),
[Clang ASan documentation](https://clang.llvm.org/docs/AddressSanitizer.html).
Their alignment and overlapping-region restrictions informed the guarded stride
and locking design. Annotation tests and allocator code are authored here.

## AI assistance

AI assistance was used for implementation, debugging, testing, analysis and
writing. The participant reports that the event SPOC permitted this by phone;
permission is not attributed to a published AI-code clause. See [attribution](author.md).
No organizer endorsement, official score or hidden-test result is claimed.
