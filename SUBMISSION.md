# Submission guide — SYSPROG10

**Participant:** Jashandeep Singh, solo, IMT2024022.
**Track:** Systems Programming. **Question ID:** SYSPROG10.
**Repository:** https://github.com/Jdsb06/low-level-synergy26

## Reviewer entry points

| Deliverable | Location |
| --- | --- |
| Implementation and four-function interface | [src/allocator.c](src/allocator.c), [include/libmemctl.h](include/libmemctl.h) |
| Build and run instructions | [README.md](README.md), [Makefile](Makefile) |
| Design note and invariants | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Current measurements, trade-offs and coverage | [TECHNICAL_REPORT.md](TECHNICAL_REPORT.md) |
| Concise report | [Three-page PDF](output/pdf/libmemctl-review.pdf) |
| Testable Linux output | [Prebuilt library/executables and provenance](prebuilt/README.md) |
| Actual demonstration | [Replay MP4](demo/terminal-replay.mp4), [original terminal cast](demo/terminal.cast), [speaker notes](demo/SPEAKER_NOTES.md) |
| Raw single/multithread benchmark evidence | [Main comparison](results/checkpoint5-2026-11-09/raw.json), [longer common confirmation](results/checkpoint5-common-confirmation-2026-11-09/raw.json) |
| Attribution and selected source identity | [AUTHOR.md](AUTHOR.md), [SOURCES.md](SOURCES.md), [SUBMISSION.json](SUBMISSION.json) |

The selected build input is `src/allocator.c`. Historical baseline/trial sources
are evidence and are never compiled by the default build. Earlier checkpoint
reports preserve what was known then; the current report above is authoritative
for the selected implementation's measurements and limitations.

## Five-minute local review

```bash
python3 scripts/verify_submission.py
make check
make sanitize
bash demo/run_demo.sh
```

No official kit, account or network is needed. The sanitizer run deliberately
launches invalid accesses in child processes; success means every expected error
was detected and every valid-access control passed. See README for the separately
obtained official public tests and for longer stress/comparison commands.

For an archive rather than Git, run `python3 scripts/package_review.py`. Verify the
generated outer checksums, extract the ZIP or tar, then run `sha256sum -c MANIFEST.sha256`
from its `libmemctl-review/` directory. All source, documentation, recorded media
and labeled prebuilt files are included by the explicit `PACKAGE_CONTENTS.json`.

## Owner's final delivery steps

The repository remains private at the participant's request. Once the participant
has reviewed this version, make it public and confirm the repository link opens
while signed out. Visibility is an owner action, not a missing implementation task.

The [official submission form](https://forms.cloud.microsoft/r/WDNMEiRVUG) was
inspected read-only on 9 November 2026. Use the identity/track/question/repository
above and enter the participant's own institute, phone and email. Private contact
details are deliberately absent from this public-ready project. The form labels
the YouTube demo link **optional**; the included replay remains available in the
repository. Rehearse the explanation using the speaker notes before a live demo.

The reviewed organizer listing gives 13 November 2026, 23:59 IST, subject to change;
recheck announcements immediately before delivery. No final scoring normalization
constants are available in the reviewed statement, so no official score is invented.
The participant reports SPOC permission for AI-assisted coding; see AUTHOR.md.

Only after the participant submits the form and receives a receipt can official
submission be marked complete. No form has been filled/submitted by this project,
and repository preparation or a Git push is not an official submission receipt.
