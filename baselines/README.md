# Comparison baseline

`allocator.c` is our authored allocator before bounded large-mapping reuse, not the
official one-mapping-per-allocation starter. Its SHA-256 is
`521932e19106be195857014b44c2531e137c2b6e54cd33927f93cb138952e9a0`.
It makes the paired throughput/latency/space comparison reproducible offline.

Run from the project root:

```bash
mkdir -p build-baseline
cp baselines/allocator.c build-baseline/allocator.c
make BUILD_DIR=build-baseline ALLOCATOR_SRC=build-baseline/allocator.c profiles benchmark
```

The submitted implementation is `src/allocator.c`. The two implementations export
the same API and must be linked into separate executables, never together. The
[reproduction guide](../docs/reproduction.md) supplies the complete comparison commands.
