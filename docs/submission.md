# Submit libmemctl — SYSPROG10

**Delivery method:** enter the GitHub repository URL in the
[official Low Level Hackathon Submission form](https://forms.cloud.microsoft/r/WDNMEiRVUG).
The live form was rechecked read-only on **10 November 2026**: it has a repository-link
field and an optional YouTube field, with no file-upload/ZIP field. Source, report,
benchmarks, demo and executables are already part of this repository.

## Exact form values

| Form field | Enter |
| --- | --- |
| Your Full Name | Jashandeep Singh |
| Your Institute Name | Your registered institute |
| Phone No. | Your working contact number |
| Email Id. | Your working contact email |
| Track | **Systems Programming** |
| Question ID | **SYSPROG10** — all caps; this is not the roll number |
| GitHub Repo Link | `https://github.com/Jdsb06/low-level-synergy26` |
| YouTube Demo Link (optional) | Leave blank unless publishing your own YouTube demo |

The participant is a solo entrant, roll IMT2024022. Private contact details are
entered by the participant in the form and are not published in the source repo.
Only Track showed an explicit required marker; supply correct contact/identity
information rather than interpreting other missing markers as permission to omit it.

## Before pressing Submit

1. Make the repository public from its **Settings → General → Danger Zone → Change
   repository visibility**, when ready to share it. A signed-out check on 10 November
   still returned 404. Publication remains the owner's action.
2. Open the repository in a private/incognito window and confirm the README, PDF,
   demo and source are accessible. Use the repository URL above in the form.
3. Review the [judge guide](review-guide.md), reproduce the example, and rehearse
   the [speaker notes](../demo/SPEAKER_NOTES.md) so you can explain the invariants
   and performance/space trade-off in a live demonstration.
4. Fill the official form, review its values, submit once, and save the confirmation
   or receipt. Only that receipt confirms official submission.

The [organizer listing](https://unstop.com/hackathons/low-level-hackathon-synergy-26-international-institute-of-information-technology-iiit-bangalore-1762854)
was expanded/read on 10 November and still gives **13 November 2026, 23:59 IST**,
subject to change. Its “registration closed” notice concerns new registration,
not that later submission deadline. The form itself was open; no fields were filled.
Recheck organizer announcements before delivery. This project never auto-submits.

## Required deliverables are in the repository

| Deliverable | Location |
| --- | --- |
| Complete C11 source and four-function header | [Allocator](../src/allocator.c), [public header](../include/libmemctl.h) |
| Build and run instructions | [README](../README.md), [Makefile](../Makefile), [one-command evaluation](../scripts/evaluate.py) |
| Architecture and implementation details | [Design note](architecture.md) |
| Single/multithread performance, space and trade-off | [Current report](report.md), [raw comparison](../results/checkpoint5-2026-11-09/raw.json), [longer confirmation](../results/checkpoint5-common-confirmation-2026-11-09/raw.json), [current thread scaling](../results/current-scaling-common-2026-11-10/raw.json) |
| Concise report | [Three-page PDF](../output/pdf/libmemctl-review.pdf) |
| Precompiled testable output | [Verified library/executables](../prebuilt/README.md) |
| Functional demonstration | [Replay MP4](../demo/terminal-replay.mp4), [original cast](../demo/terminal.cast), [live demo](../demo/LIVE_DEMO.md) |
| Attribution and reproducibility | [Participant/AI disclosure](author.md), [sources](sources.md), [source manifest](submission.json), [reproduction](reproduction.md) |

A ZIP can be generated with `python3 scripts/package_review.py` as a reproducible
backup; it is not a separate upload demanded by the current form. Official material
and private contacts are excluded. Historical trials are marked and never selected
by the default Makefile. Required source/build/design/benchmark/trade-off contents
match the selected SYSPROG10 statement; the general listing also asks for testable
output and functional demonstration, both included here.

The official repository advanced to `05b1aa7445770408bb4307c7f8c8999b502c0a6f`.
All six SYSPROG10 files, including statement/header/starter/Makefile/public tests,
are byte-identical to our pinned kit; [provenance](sources.md) records that recheck.
No final normalization constants are provided, so no official score is invented.
AI-code permission is attributed to the participant's SPOC phone report.
