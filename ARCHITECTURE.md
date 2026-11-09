# Allocator architecture and invariants

## Layout

```text
four public my_* entry points
    size <= 64 KiB -> thread-assigned shard -> size-class mutex -> reusable region
    64 KiB..1 MiB -> shard/band mutex -> capped dedicated-mapping reuse
    above 1 MiB   -> dedicated mmap region -> direct munmap on free
```

64 size classes use 16-byte steps through 256 bytes, 64-byte steps through 1 KiB,
256-byte steps through 4 KiB, 1-KiB steps through 16 KiB and 4-KiB steps through
64 KiB. This limits rounding waste compared with powers of two. A block has a
16-byte header on the target: immutable owner-region pointer and the current
requested size. Payload space holds the free-list link only while the block is
free. The compile-time alignment assertion rejects incompatible header layouts.

Regions are page-rounded and start at a 16 KiB minimum with a four-block target.
Once a bin exhausts its starter region, it remembers that demand and targets 32
blocks in future mappings, including after quiescence. Undersized starter regions
are no longer refilled in a busy bin: existing objects drain naturally before
unmapping. This prevents small-region churn while keeping sparse classes compact.
The bin's region count is overflow-checked and updated under its mutex. On the
verified targets, packed count/state fields keep bins cache-line sized; the array
base is aligned to 64 bytes. The
region header stores capacity, free/total counts, free-list head, mapping length
and available-list links. A region is owned by exactly one shard/class bin.
Completely full regions are absent from the available list. Allocation takes the
first available region in constant time; there is no scan of all allocated blocks.
Initializing a new region touches its metadata and has linear cost in block count.

Large allocations have one region and one block. Their size calculation checks
header addition and page-rounding overflow before mapping. Requests above 64 KiB
through 1 MiB use 64-KiB capacity bands, with one cache slot per band/shard. A
region-header union stores the immutable large-cache owner in the slot used for
small-region free-list metadata; region/header sizes remain unchanged on the target.
Uncached, over-budget and requests above 1 MiB are unmapped on free. Realloc can retain a mapping when the new request fits and is at
least half its capacity; substantial shrink requests move to avoid retaining a
large mapping unnecessarily. Allocation and copying complete before the old
object is freed. Moving realloc has linear cost in preserved payload bytes.

## Concurrency

Eight shards are the current measured default. A thread selects a shard once,
using a relaxed atomic round-robin counter and thread-local assignment. The TLS
contains no pointers to cached blocks or thread-owned memory, so thread exit
cannot strand objects. Free uses the object's immutable region owner; it can
occur in any thread, including after the allocating thread has exited.

A bin mutex protects the region list, free lists, counts and cached-region pointer.
Regions are initialized before a live pointer is published. A live allocation
prevents its region from reaching the all-free state, so its immutable metadata
remains mapped until that allocation is freed. The caller owns its requested-size
field and payload; concurrent operations on that same allocation require external
synchronization under the official API contract.

No operation holds two bin locks at once. Realloc allocates/copies before invoking
free, with no bin lock held. Trim takes one bin lock at a time and can only remove
fully empty cached regions. Large buckets have their own mutexes, with the same
no-nested-lock rule. Thread assignment remains a TLS shard number, not a pointer
to thread-owned cache storage. pthread_once initializes page size and both mutex
arrays. Large allocate/free helpers keep their extra logic outside small-call
bodies using an optional GCC/Clang noinline hint.

## Reclamation

A small empty region can be cached if it is at most 64 KiB and its bin has no
other cached region. Eligible large dedicated mappings can fill one cache slot
per shard/band. Both types must reserve their full mapping bytes within a shared
**2 MiB global bound**. All other completely empty regions are removed and unmapped.
Claiming a cached region for allocation subtracts its bytes under the bin lock.
The global byte counter coordinates distinct bins without nesting their locks.
`memctl_trim()` releases those cached mappings; it never touches live regions.

This bounds fully empty retention even when many short-lived threads visit many
size classes. A region with one surviving allocation cannot be unmapped; sparse
long-lived allocations across classes/shards remain a fragmentation risk. This
design uses whole-region reuse/reclamation rather than splitting/coalescing
variable-sized blocks. It does not claim to solve every fragmentation pattern.

## Correctness and costs

The allocator uses only permitted mapping, pthread, atomic and non-allocating C
utilities. It does not use brk/sbrk, standard heap allocation, third-party allocator
code or a framework. The API declarations and contract come from the official kit;
the implementation and additional tests are authored in this workspace after the
start. Architecture suggestions in the problem statement informed the region/
size-class approach. AI assistance was used under the user's reported SPOC approval.

Fixed limitations include mutex acquisition on every small allocation/free,
cross-thread frees contending on the original shard, O(blocks) region initialization,
large-object syscall costs and no in-place physical region growth. Cache reservation
may also contend in repeated completely-empty-region workloads. The measured
one-thread loss from eight shards is preserved rather than hidden.

ASan builds explicitly poison headers, unused payload capacity, 16-byte tail guards
and cached free blocks. Only requested payload bytes (one for zero-size) are exposed.
An ASan-only header union holds free links, avoiding accessible freed payload bytes.
Metadata initialization/free/realloc temporarily exposes the affected header;
mapping reclamation clears shadow state. Strides preserve separate shadow granules
for adjacent blocks. Release and TSan builds retain the original layout and code.
See [checkpoint 3](CHECKPOINT3.md) for executed positive/negative controls and limits:
there is no temporal quarantine, and address reuse can hide stale-pointer access.
[Checkpoint 5](CHECKPOINT5.md) adopts capped large-object reuse with measured
throughput/latency gains and higher held VM; eight-thread mixed throughput has
a lower median. `MEMCTL_LARGE_CACHE=0` disables it for comparison.
[Checkpoint 4](CHECKPOINT4.md) measures per-API tails and three burst/drain/refill
cycles. Repeated large mappings have high concurrent tails; learned regions can
retain substantial VM while sparse survivors remain. Empty-cache bounds do not
bound live-region fragmentation. Final compatible-package and demo checks remain future work.
