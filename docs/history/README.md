# Development history

These records explain how the selected implementation was reached. Their results,
remaining-work notes and environment claims describe their own point in time.
For the final design and current measurements use [the report](../report.md),
[architecture](../architecture.md) and [project overview](../../README.md).

| Record | What it established |
| --- | --- |
| [Initial report](initial-report.md) | Working API, first sharding comparison and initial space measurements |
| [Region policy](checkpoint-2.md) | Compact starter regions, reclamation and early NHPC validation |
| [Sanitizer annotations](checkpoint-3.md) | Suballocation boundaries and misuse-detection controls |
| [Latency and lifetimes](checkpoint-4.md) | Per-API tails, sparse survivors and a corrected benchmark baseline |
| [Large-object reuse](checkpoint-5.md) | Selected throughput/space trade-off, including rejected trials |
| [Compatibility and packaging](checkpoint-6.md) | Current-source GCC9/GCC13 execution, report, recording and archive checks |

Raw experiments, including unsuccessful trials, remain under `results/` at the
project root. Their commands, seeds, source hashes and environment observations
are evidence rather than build inputs. The default Makefile selects only
`src/allocator.c`. Nothing in this history is an official score or submission receipt.
