# libmemctl review candidate

Participant: Jashandeep Singh, solo, IMT2024022. Problem: SYSPROG10, Systems Programming.
This is a review candidate. Its archives, report and test recording are not a
submission receipt. The allocator policy is the tested checkpoint-5 implementation.

## Review order

1. README.md: build and independent checks, without the official kit.
2. ARCHITECTURE.md: region ownership, locks, cache accounting and reclamation.
3. CHECKPOINT5.md: current measured improvement and its costs, with raw evidence.
4. CHECKPOINT6.md: current-source compatibility and package verification.
5. output/pdf/libmemctl-review.pdf: concise reviewer-facing report.
6. demo/: executable CLI walk-through, actual terminal recording and speaker notes.
7. AUTHOR.md, SOURCES.md and SUBMISSION_CHECKLIST.md: attribution and delivery limits.

The initial TECHNICAL_REPORT.md and earlier checkpoint reports are historical.
Do not present their old measurements as newly measured current-source results.

## Verify the downloaded package

First check the supplied outer `.SHA256SUMS` file in the archive directory.
After extracting an archive and entering its libmemctl-review directory:

```bash
sha256sum -c MANIFEST.sha256
make check
make sanitize
bash demo/run_demo.sh
```

Only the separately obtained official kit is needed for `make public-test`.
The package contains complete authored source/headers, independent tests, build
instructions, architecture note, benchmark evidence and reproducible comparison
scripts. Intermediate build products, official material, credentials and other competitions
are excluded. When built with the explicit --prebuilt input, a labeled prebuilt/
folder contains the verified GCC 9 Linux x86-64 library and testable executables;
the source and each executable are covered by the package manifest. Old authored trial sources are evidence, not the selected build input;
the default Makefile compiles only src/allocator.c.

## Delivery review still required

Official form: https://forms.cloud.microsoft/r/WDNMEiRVUG . Read-only inspection
on 9 November 2026 showed full name, institute, phone, email, track, question ID,
GitHub repository and optional YouTube demo fields. Only Track was explicitly
marked required in the inspected accessibility tree; do not infer completion rules
for other fields. Correct known selections: Systems Programming, SYSPROG10,
https://github.com/Jdsb06/low-level-synergy26 . No fields were filled.

The YouTube demo is explicitly optional in that form. OS-track-specific video,
Docker and scoring rules are not automatically applied to Systems Programming.
The selected statement requires source, build instructions, design note and
benchmark results. Final normalization values remain unpublished in the reviewed
statement; no calculated official score is supplied. Recheck organizer changes
and final deadline before approving a concrete upload. No organizer was contacted.

The terminal recording is an actual run of authored independent tests. Any rendered
video of it is a terminal replay, not a claim of an unedited desktop screen capture.
Narration/presentation and an optional public video link remain the participant's
choice. Publishing development checkpoints does not authorize official submission.

Signed-out GitHub access was checked on 9 November and returned 404 despite
working authenticated Git access. Establish judge access before submission;
repository visibility/sharing has not been changed automatically.
