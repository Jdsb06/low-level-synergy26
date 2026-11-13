# Functional demonstration

[Watch the terminal replay](terminal-replay.mp4), or run the same demonstration
from the repository root:

```bash
bash demo/run_demo.sh
```

The demonstration builds and executes the independent correctness suite, then
explains region ownership, the shared 2 MiB empty-cache bound and the measured
large-reuse trade-off. The displayed benchmark numbers come from the recorded
five-process comparisons; the demonstration does not present them as fresh timings.
See [the technical report](../docs/report.md) for methods, ranges and costs.

## Recording provenance

The included run was captured on **13 November 2026**, using GCC 13 and the selected
allocator source. It exited successfully. The video renders actual terminal events
at their captured times with a two-second final hold; it is not a desktop recording.

| File | Purpose |
| --- | --- |
| [terminal-replay.mp4](terminal-replay.mp4) | H264 replay, 1440 x 900, approximately 14.5 seconds |
| [terminal.cast](terminal.cast) | Original asciicast v2 event stream |
| [run.log](run.log) | Original raw terminal output |
| [recording.json](recording.json) | Invocation, compiler, timing, exit status and recording/source checksums |
| [video.json](video.json) | Rendering command and video/cast checksums |

`python3 scripts/verify_submission.py` verifies the recording/video against their
metadata and the selected allocator hash. Regeneration tools are documented in
[the scripts guide](../scripts/README.md); reading or running the demonstration
does not require the optional media-generation dependencies.
