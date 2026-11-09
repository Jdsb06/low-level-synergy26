# Two-minute explanation to rehearse

These notes are a suggested talk track. Review the source and replace wording with
your own explanation; do not present the generated recording as a manual coding session.

**0:00-0:20 - Goal and contract.** I am Jashandeep Singh, entering solo as IMT2024022.
The challenge is a C11 allocator implementing malloc, free, realloc and calloc through
the required my_* API. Backing storage is private anonymous mmap; the allocator
does not forward allocation to libc. Correctness comes before throughput.

**0:20-0:50 - Design.** Small requests use 64 size classes and eight shards. Each
region has one immutable owner; free follows that owner, including across threads.
Per-bin locks protect metadata, and no path holds two allocator locks. Realloc
preserves the required prefix and releases the old object only after success.

**0:50-1:20 - Tests and compatibility.** Show the preserved independent-test run.
Explain forced mapping failures, reuse/zeroing, exact boundaries and live-safe trim.
The current source passes six official tests locally, 59 ASan controls and TSan
stress; GCC 13 on Ubuntu and GCC 9/glibc 2.17 on NHPC also executed successfully.
NHPC's older kernel required a benchmark RSS-counter fallback, not an allocator change.

**1:20-1:45 - One measured decision.** Capped reuse above 64 KiB through 1 MiB
improved the local eight-thread large trace by about 70% in throughput and 38% in
malloc p99. State the costs: 35% more held VM in that large burst and an 11% lower
eight-thread mixed-throughput median. Results are five-process medians on a shared
laptop, not an official score or a guarantee on every workload.

**1:45-2:00 - Limits and reproduction.** All empty caches share a 2 MiB bound and
trim returns cached mappings. Sparse live allocations still pin regions, and cache
misses still have long tails. Show README and the package manifest. AI assistance
is disclosed; its permission is attributed to my reported SPOC phone confirmation.

The MP4 is a rendered terminal replay at its captured event times, plus a two-second
final hold. `terminal.cast`, `run.log` and recording hashes preserve the actual
subprocess output. It is not a desktop screen recording. The official submission
form labels its YouTube field optional; no public video has been uploaded.
