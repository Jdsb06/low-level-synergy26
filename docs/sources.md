# Problem provenance and attribution

Selected challenge: **SYSPROG10 — libmemctl: High-Throughput Thread-Safe Memory
Allocator**, Synergy '26 Low-Level Hackathon. Official materials were retrieved
9 November 2026 after release, before implementation.

- [Official repository](https://github.com/rudra-shroff06/LLH-26)
- [Pinned selected statement](https://github.com/rudra-shroff06/LLH-26/blob/d23ac1d865df4cdacf7ad8e9fff3e1d560761c46/Systems%20Programming/SYSPROG10/PROBLEM.md)
- Official commit: `d23ac1d865df4cdacf7ad8e9fff3e1d560761c46`.
- Statement SHA-256: `9786389183b8088fb8d8066e6153a05201ea93d721365317099a1ce2fd838220`.

The four API declarations/semantics come from the official starter. The allocator,
additional tests, benchmark workloads and project documentation were authored
during the permitted window. The statement's discussion of regions, size classes
and contention informed the design. No third-party allocator implementation or
optimizer framework was copied. Standard C/POSIX/Linux interfaces are used.

The unchanged official reference and public runner were used locally for comparison.
Official PDFs, starter source/test copies, private attachments and datasets are not
redistributed in this repository. Obtain the participant kit separately to run
`make public-test` or the reference comparison. Independent checks work offline
without it.

AI assistance was used for implementation, debugging, tests, analysis and
documentation. The participant reports that the event SPOC explicitly permitted
AI assistance by phone; this permission is not attributed to published statement
text. The participant must be able to explain the submitted design and results.

The coding window is 9 Nov 2026, 09:00 IST through 13 Nov, 23:59 IST in the event
listing and released common OS kit. Check subsequent organizer updates before
submission. Final normalization targets and submission/demo details remain subject
to final review; no official score or winning probability is claimed.

Allocator-aware sanitizer annotations use the public ASan poisoning interface,
reviewed 9 November 2026 in the installed GCC 15 header and the primary references:
[LLVM interface](https://github.com/llvm/llvm-project/blob/main/compiler-rt/include/sanitizer/asan_interface.h)
and [Clang ASan documentation](https://clang.llvm.org/docs/AddressSanitizer.html).
Their alignment and overlapping-region restrictions informed the guarded stride
and locking design. The implementation and annotation-control tests are authored
here; no third-party allocator implementation was copied.


Delivery recheck, 9 November 2026: official repository main remains d23ac1d above.
The expanded Unstop listing still states 13 Nov23:59 IST (subject to change), and
calls for build instructions, testable output where applicable, documentation,
benchmarks and functional demonstration. The official form linked from the kickoff
PDF is https://forms.cloud.microsoft/r/WDNMEiRVUG ; read-only inspection found its
YouTube demo field explicitly optional. No form was filled and no OS-specific
video/Docker/ranking rule is inferred for Systems Programming.
Participant confirmed solo identity as Jashandeep Singh, IMT2024022 in chat;
contact details and a portal receipt are not supplied or published.


Delivery recheck, **10 November 2026**: official main advanced to
`05b1aa7445770408bb4307c7f8c8999b502c0a6f` (commit-ID0003). A separate ignored clone
was compared with the pinned kit: all six SYSPROG10 files are byte-identical,
including statement SHA above and public runner SHA
`37febda4b4a693c4fb5d315f27276aa12be8677c1e8576e2571c5ab31bf7a03c`.
Original implementation provenance remains pinned; no changed track rule was ignored.
The expanded organizer listing still gives 13 Nov23:59 IST, subject to change.
The official form was open and still asks for name/institute/phone/email, track,
question ID and a GitHub link, with optional YouTube and no file-upload field.
No form interaction or organizer communication occurred. Signed-out GitHub returned
404; the owner must establish public judge access before submitting. GitHub CLI
was unauthenticated, while existing authorized SSH read access continued to work.
