# Superseded warm-baseline experiment

105/105 processes completed on 9 November 2026. The latency traces remain valid,
but this space method warmed each worker with an allocation before its idle
baseline. That included libc's per-thread arena reservations in idle VM and made
its subsequent VM growth appear zero. It is unsuitable for comparing cold-start
allocator VM costs. Absolute idle/high-water values remain in raw.json; no result
was discarded. Authored harness source snapshots are in sources/ (allocator/header
and build flags are the unchanged pinned project files/hashes in raw.json).

The accepted checkpoint-4 run removes per-worker allocations and trim before the
idle snapshot, so first-use arena reservations appear in growth. Workers/stacks
remain alive at both measurements. Latency warmup is retained and explicitly
separate. Do not mix the two space baselines or use the zero delta as a claim that
libc requires no VM. No allocator implementation was changed by this experiment.
