# Evaluation results

This directory contains the evidence for the submitted allocator. Start with the
[technical report](../docs/report.md) for interpretation, or run
`python3 scripts/evaluate.py` for a fresh isolated correctness check.

## Benchmarks

| Dataset | What it demonstrates | Recorded evidence |
| --- | --- | --- |
| Large-mapping reuse | Paired throughput, API latency and fully touched memory phases; 140 fresh processes, five repetitions per case | [Summary](benchmarks/cache-reuse/summary.csv), [raw measurements](benchmarks/cache-reuse/raw.json), [chart](benchmarks/cache-reuse/tradeoff.png) |
| Longer common workloads | Small/mixed throughput confirmation using five million calls per worker; 40 fresh processes | [Summary](benchmarks/common-workloads/summary.csv), [raw measurements](benchmarks/common-workloads/raw.json) |
| Thread scaling | Selected source at 1/2/4/8 threads; 60 timing processes and 10 separate space samples | [Common summary](benchmarks/thread-scaling/common/summary.csv), [common raw](benchmarks/thread-scaling/common/raw.json), [large summary](benchmarks/thread-scaling/large/summary.csv), [large raw](benchmarks/thread-scaling/large/raw.json) |

The paired measurements were captured on 9 November 2026; scaling was captured on
10 November. The runner records machine/compiler details, flags, source/binary
hashes, seeds, CPU placement, all repetitions and ranges. These are shared-laptop
measurements with uncontrolled clock/thermal/background activity. Separate traces
and dates must not be combined into an official score or universal speedup.

Raw JSON captures are unchanged and retain capture-time identifiers and paths.
Summary CSVs display the reference variant as `baseline`; all measurement values
remain unchanged. Current commands and the
pinned baseline are in the [reproduction guide](../docs/reproduction.md).

## Correctness

| Evidence | Coverage |
| --- | --- |
| [Validation](correctness/validation.json) | Native/public tests, sanitizers, strict warnings and static analysis, with exact invocations and source hashes |
| [Sanitizer controls](correctness/sanitizer-controls.json) | 59 controls: 25 valid accesses and 34 deliberately invalid accesses detected |
| [Stress runs](correctness/stress.json) | Seeded native/ASan/TSan workloads, ownership transfers and concurrent trimming |
| [Isolated evaluation](correctness/evaluation.json) | Recorded fresh-build evaluation, example, public tests and sanitizer controls |

The core allocator SHA-256 is
`ce2e34f557608c4c1cd4277a12dc85fa88cdcc343e6540d74924ddd31024d267`.
Capture metadata distinguishes the allocator from benchmark/supporting-source
revisions. LeakSanitizer is disabled; address reuse and already-unmapped storage
limit misuse detection. Invalid/double frees are outside the API contract.

## Compatibility

| Environment | Evidence |
| --- | --- |
| Ubuntu 26.04.1, GCC 13.4 / glibc 2.43 | [Executed checks](compatibility/ubuntu-gcc13.json), [sanitizer controls](compatibility/gcc13-annotations.json) |
| NHPC Linux 3.10, GCC 9.3.1 / glibc 2.17 | [Build](compatibility/nhpc-build.txt), [execution](compatibility/nhpc-validation.txt), [source/launch verification](compatibility/nhpc-verification.json) |
| Shipped GCC9 executables on Ubuntu | [Execution record](compatibility/prebuilt-on-ubuntu.json) |
| Input/output identities | [Source inputs](compatibility/nhpc-inputs.sha256), [binaries](compatibility/nhpc-binaries.sha256), [shipped checksums](../prebuilt/SHA256SUMS) |

NHPC runs establish correctness/compatibility, not cluster throughput. They use
the same allocator source as the recorded local comparison. No compatibility
promise is made beyond the executed environments.
