# Checkpoint 6 - compatibility and review delivery

> Archived development record. For the selected submission, start with
> [the current report](../report.md) and [the project overview](../../README.md).

9 November 2026. Participant-confirmed author: **Jashandeep Singh**, solo, IMT2024022.
The allocator is unchanged from checkpoint 5, SHA-256
`ce2e34f557608c4c1cd4277a12dc85fa88cdcc343e6540d74924ddd31024d267`.
This milestone prepares a review candidate; it does not submit the competition form.

## Current-source compatibility

On native Ubuntu 26.04.1/glibc 2.43, **GCC 13.4.0** built and executed the independent
suite, all six unchanged official tests, a one-million-operation soak with 65,536
handoffs, the full-touch large lifetime probe and all **59 ASan/UBSan controls**.
Existing GCC 15.2.0/TSan evidence is scoped to the identical allocator source.
The GCC 13 runs use separate build directories so cached GCC 15 objects cannot
masquerade as a compiler-version check.

The identical current source also built with **GCC 9.3.1** on the NHPC login host.
PBS job **30373.master.local** then executed the compiled independent suite,
**1,000,000 mixed operations + 131,072 ownership handoffs**, and the full-touch
large-object lifetime probe in an allocated eight-CPU compute job. Runtime:
Linux 3.10.0-693.el7.x86_64, glibc 2.17. Input and executable checksums were verified
before execution. The captured job output reports success with empty program stderr.
This is compatibility/correctness evidence, not cluster speedup or official grading.

The existing student3 routing wrapper was explicitly approved by the user. Project
inputs, working directory, compiler outputs and test files stayed in the isolated
`/home/student4/IMT2024022/libmemctl-cp6-20261109-rLXzpj` directory; the approved
wrapper used its normal staging exception. No other student's files or global
software/startup configuration were changed. The job-created success-marker file
has restricted permissions; success is established from captured stdout plus
matching source/input/binary manifests, rather than claiming that marker was read.

The downloaded GCC 9 executables were also run on Ubuntu 26.04.1: independent
checks, 100,000 additional mixed operations/65,536 handoffs and the lifetime probe
passed. A separately labeled optional prebuilt package component contains that
static library and those testable Linux x86-64 executables. It bundles no system
runtime or official kit and makes no claim about every architecture/distribution.

Evidence: [Ubuntu GCC 13](../../results/checkpoint6-compatibility-2026-11-09/ubuntu-gcc13.json),
[NHPC validation](../../results/checkpoint6-compatibility-2026-11-09/nhpc-validation.txt),
[NHPC provenance](../../results/checkpoint6-compatibility-2026-11-09/nhpc-verification.json),
and [prebuilt execution on Ubuntu](../../results/checkpoint6-compatibility-2026-11-09/prebuilt-on-ubuntu.json).

## Compatibility issue found and resolved

Linux 3.10 does not expose `/proc/self/smaps_rollup`. The lifetime benchmark now
falls back to summing `Rss:` from `/proc/self/smaps` when rollup is absent, checking
the sum for overflow. JSON reports `rss_source: smaps_rollup` or `smaps_sum`.
The existing `rss_rollup_kib` numeric field is retained for consumers; its source
must be read from that tag. Both paths executed: rollup on Ubuntu, sum on NHPC.
The allocator/API and prior policy measurements are unchanged.

The first login setup stopped with exit 141 because `head` closed a version-output
pipeline under pipefail; no compilation or job ran then. A consuming `sed` fixed
the inspection, and the corrected build/job completed. Docker was present as an
unusable snap command with no daemon socket; no Docker image or older-Ubuntu
container was run. The claims here are native clean Ubuntu builds plus actual
older Linux/glibc execution, not a container certification.

## Report, demo and review package

- `output/pdf/libmemctl-review.pdf`: three-page report with current design,
  measurements/costs, compatibility, attribution and reproduction commands. It was
  rendered and all pages visually inspected.
- `demo/terminal.cast`, `run.log`, `recording.json`: actual GCC 13 independent-test
  subprocess output and hashes; recording exit status is zero.
- `demo/terminal-replay.mp4`: 1440x900 H.264 replay at original event times, with a
  disclosed two-second final hold. It is not an unedited desktop screen capture.
  `SPEAKER_NOTES.md` provides a two-minute explanation to rehearse.
- `scripts/package_review.py` and `PACKAGE_CONTENTS.json`: an explicit allowlist,
  normalized archive metadata, per-file manifest and content-addressed archive names.
  Matching optional prebuilt binaries are included only through an explicit input.
  Official kits, credentials, sibling competitions and intermediate builds are excluded.
- `baselines/checkpoint4_allocator.c`: our earlier authored source, pinned by hash,
  so the measured comparison can be rebuilt from an offline archive.

Create the source-only review archives with:

```bash
python3 scripts/package_review.py
```

An explicitly verified prebuilt directory may be supplied with `--prebuilt PATH`;
it must contain the exact source and binary manifests expected by the packager.
From an extracted candidate, run `sha256sum -c MANIFEST.sha256`, then `make check`
and `make sanitize`. The official kit is needed only for `make public-test`.
Archives and their outer checksums are written under ignored `dist/`.
The 128-file review candidate reproduced byte for byte across two builds; both
ZIP and tar extraction passed every file checksum. An intentional source edit was
rejected by the manifest checker, then restored. The extracted package ran the
prebuilt independent suite, a clean GCC 13 source build, all 59 sanitizer controls
and 28 offline current/baseline smoke profiles. The final documentation and raw-recording Git-attribute
refresh is checked against the exact executed input hashes; package-validation
logs are retained separately under `results/checkpoint6-package-2026-11-09/`.
Post-build package-validation logs are repository evidence outside the archives,
avoiding a self-referential archive hash. No release archive was uploaded publicly.

## Final delivery facts and remaining work

Rechecked on 9 November: official repository main remains pinned
`d23ac1d865df4cdacf7ad8e9fff3e1d560761c46`; the expanded Unstop listing still states
13 November 2026, 23:59 IST for submission, subject to change. Its generic deliverables
include build instructions, testable binaries where applicable, documentation,
benchmarks and functional demonstration. The prepared review package covers those
artifacts without inferring OS-track-only requirements for Systems Programming.

The official form was inspected read-only: name, institute, phone, email, track,
question ID, GitHub link and **optional YouTube demo**. Correct known values are
Systems Programming, SYSPROG10 and the supplied repository. No field was filled.
The solo identity is confirmed by the participant, but portal registration receipt,
institute/contact details and final access remain to be reviewed. The development
repository returned GitHub 404 in a signed-out browser while authenticated SSH
access works, so judge access is not established. No visibility or sharing setting
was changed. AI permission
continues to be attributed to the user's SPOC phone report. Final normalization
values were not found in the unchanged selected statement; no official points
or winning probability are invented.

Next milestone: participant review/rehearsal, final form/access/contact check and
an exact submission candidate for explicit approval. Recheck any later rule or
deadline change. Do not auto-submit, upload a public video, contact organizers or
publish a GitHub release without an instruction covering that action. Standing
authorization continues to cover reviewed development-checkpoint pushes.
