# Evaluation and reproduction tools

Run these scripts from the repository root. Core evaluation uses Python 3.9+ and
system build tools, with no third-party Python packages or downloads.

## Evaluate the submission

| Script | Purpose |
| --- | --- |
| [evaluate.py](evaluate.py) | Fresh isolated build, artifact checks, independent tests and the working example; optional sanitizers/public suite |
| [verify_submission.py](verify_submission.py) | Source/artifact identities, prebuilt manifests, recording/video provenance and local document links |
| [check_symbols.py](check_symbols.py) | Reject forbidden heap-allocation references in the allocator object; invoked by Make |
| [check_annotations.py](check_annotations.py) | Check valid/invalid sanitizer subprocess controls; invoked by sanitizer targets |

```bash
python3 scripts/evaluate.py
python3 scripts/evaluate.py --sanitizers
```

## Reproduce measurements

| Script | Purpose |
| --- | --- |
| [compare_large_cache.py](compare_large_cache.py) | Paired comparison against the pinned authored baseline |
| [run_benchmarks.py](run_benchmarks.py) | Fresh-process throughput/scaling and space runs, recording hashes, environment, seeds and ranges |
| [profile_workloads.py](profile_workloads.py) | Per-API latency and lifetime/space profiles |

See [reproduction commands](../docs/reproduction.md) before running measurements.
Short execution checks do not reproduce the recorded headline timing protocol.

## Optional artifact generation

| Script | Produces |
| --- | --- |
| [package_review.py](package_review.py) | Reproducible ZIP/tar from [the explicit inventory](package-contents.json), with integrity manifests |
| [plot_cache_comparison.py](plot_cache_comparison.py) | Comparison chart from recorded CSV measurements |
| [build_review_pdf.py](build_review_pdf.py) | Three-page technical report |
| [record_demo.py](record_demo.py) | An actual subprocess terminal recording in a fresh output directory |
| [render_demo_video.py](render_demo_video.py) | Video replay of the captured terminal events |

Report/video generation dependencies are pinned in [requirements-review.txt](requirements-review.txt);
plot dependencies are in [requirements-plots.txt](requirements-plots.txt). Fonts and
ffmpeg are system tools. These optional dependencies are unnecessary for compiling,
evaluating or reading the included deliverables. Artifact/source hash changes must
be reflected in the selected manifests; recording tools refuse accidental overwrite.
