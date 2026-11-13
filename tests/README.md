# Correctness and stress tests

Run from the repository root. The default tests need no official kit or network.

| File | Coverage | Run |
| --- | --- | --- |
| [test_allocator.c](test_allocator.c) | Zero-size semantics, alignment, overflow, mapping failures, realloc preservation, reuse/zeroing, cross-thread ownership, cache bounds and trim accounting | `make check` |
| [test_annotations.c](test_annotations.c) | Valid accesses, protected headers/tails and reuse/shadow-state behavior in sanitizer builds | `make sanitize` |
| [asan_negative.c](asan_negative.c) | Deliberate invalid accesses, each isolated as a sanitizer subprocess control | `make sanitize` |
| [soak.c](soak.c) | Seeded full-payload checks, synchronized ownership transfer and concurrent trimming | `make soak` |

The 59 sanitizer controls comprise **25 valid accesses** that must succeed and
**34 invalid accesses** that must be detected. Deliberate invalid accesses are confined to sanitizer subprocess controls.
The annotation runner checks the expected outcome of each child process. LeakSanitizer is
disabled; address reuse and unmapped storage limit misuse detection.

For fresh isolated build directories with full command/output logs:

```bash
python3 scripts/evaluate.py --sanitizers
```

The unchanged official public suite is obtained separately and can be added with
`--official-dir '/path/to/SYSPROG10'`. The [results index](../results/README.md#correctness)
links recorded validation and stress evidence; the [report](../docs/report.md)
explains the supported contract and limitations.
