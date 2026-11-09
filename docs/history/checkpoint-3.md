# Checkpoint 3 — allocator-aware AddressSanitizer checks

> Archived development record. For the selected submission, start with
> [the current report](../report.md) and [the project overview](../../README.md).

Completed 9 November 2026. Allocator source SHA-256:
`521932e19106be195857014b44c2531e137c2b6e54cd33927f93cb138952e9a0`.
This development checkpoint was initially recorded locally, then published as
GitHub commit `94d9df0901b6ed9cff7ac49d6e297c2e75b24e37` after the user's standing
checkpoint-push instruction. No official submission has occurred.

## Change and purpose

ASan ordinarily sees an anonymous mapping without knowing the boundaries of its
individual allocations. ASan builds now poison unused region storage, allocation
headers, bytes beyond each requested payload, and cached freed blocks. Allocation
and realloc expose exactly the requested bytes (one internal byte for zero-size
requests). A 16-byte debug tail guard also protects a full-capacity block's end.
ASan-only free links occupy a header union so no freed payload byte needs to stay
accessible for allocator bookkeeping. Headers are exposed only while the allocator
uses them. Returned mappings have their shadow cleared before unmapping; new
mappings are cleared before initialization.

Adjacent blocks start on separate shadow granules. Bin locks protect shared region
updates; callers still synchronize ownership of a single allocation. No allocator
function disables ASan instrumentation. The normal and TSan builds retain the
original header, payload free links, region strides and allocation policy.

With GCC 15.2.0 and the same strict release flags, the allocator's complete `.text`
section matches the saved checkpoint-2 object byte for byte:
`5b5a6d639fd8988876b5064be682a7d32057a69ffce65d2b1335dac466f4a268`.
The release object has no ASan/UBSan undefined references. This verifies unchanged
generated code on this compiler; it does not establish identical output on every
compiler or a new performance result. Existing performance measurements describe
the release policy; debug guard overhead is not included in them.

## Executed validation

- All six unchanged official tests passed natively; independent failure, overflow,
  alignment, zero-size, region/reuse/trim and concurrent tests passed natively,
  with ASan/UBSan, and with TSan.
- Positive shadow queries passed across small/class/large boundaries, cached free
  and reuse, mapping reuse, failed realloc, in-place growth/shrink and moving
  realloc. Valid payload bytes remain writable; adjacent headers/tails are poisoned.
- **51 subprocess controls passed:** 23 valid accesses completed successfully;
  28 intentional overruns, header underflows, cached use-after-free and realloc
  boundary errors produced ASan `use-after-poison` write diagnostics at the test
  access. Each error must exit with the configured status and identify that test
  as the top stack frame. A signal, timeout or unrelated diagnostic cannot pass.
- The same runner against an uninstrumented build accepted the 23 valid cases and
  rejected all 28 invalid cases, exiting 1 as required. This is an expected harness
  negative control, not a failed allocator experiment.
- Native soak: **1,000,000 mixed operations + 131,072 ownership handoffs**;
  ASan/UBSan: **1,000,000 + 65,536**; TSan: **200,000 + 32,768**. All used seed
  `20261110` (a deterministic seed, not an execution date) and passed.
- Strict warnings, forbidden-symbol checks and GCC `-fanalyzer` passed.

Raw diagnostics, commands, hashes and logs are in
[results/checkpoint3-2026-11-09](../../results/checkpoint3-2026-11-09/verification.json).
No dependency was installed and no NHPC job was run for this checkpoint. The
separate-machine evidence in checkpoint 2 remains evidence for that earlier source.

## Reproduce

From this project, on Linux with GCC/ASan/UBSan, Make, binutils and Python 3.9+:

```bash
make check
make sanitize ANNOTATION_ARGS='--output results/new-annotation-controls.json'
make BUILD_DIR=build-sanitize CFLAGS='-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all' build-sanitize/soak
ASAN_OPTIONS=detect_leaks=0 timeout 180s build-sanitize/soak 125000 20261110 128
```

The participant kit is needed only for `make public-test`. See `verification.json`
for exact TSan, native soak and static-analysis invocations. ASan's deliberate
error reports are expected in the control runner; its overall exit must be zero.

## Limits and next milestone

These annotations improve spatial and cached-free checks; they do not provide
temporal quarantine or detect every invalid pointer. An unmapped large allocation
can fault without a poison diagnostic; a stale pointer after address reuse can
access a new live object. Region metadata is not fully guarded. Invalid/double
free remains outside the official API contract. LeakSanitizer remains disabled
for the documented host tracing limitation, and sanitizers do not prove correctness.

Next bounded milestone: measured allocation-latency and adversarial space coverage,
then a clean compatible Ubuntu/package/demo review. Final normalization/form/roster
and recording requirements remain unresolved. The user subsequently authorized regular reviewed development-checkpoint pushes.
Official upload remains a separate action requiring approval.
