# Authored comparison source

`checkpoint4_allocator.c` is our earlier authored allocator, not the official
one-mapping-per-object starter. It comes from development commit
`ad2ae279664ea83473f3092767dd6c2ef2214ff3`, with SHA-256
`521932e19106be195857014b44c2531e137c2b6e54cd33927f93cb138952e9a0`.

This explicit snapshot makes the checkpoint-5 comparison reproducible from a
source archive without Git history or network access:

```bash
mkdir -p build-checkpoint4
cp baselines/checkpoint4_allocator.c build-checkpoint4/allocator.c
make BUILD_DIR=build-checkpoint4 ALLOCATOR_SRC=build-checkpoint4/allocator.c profiles benchmark
```

The selected implementation remains `src/allocator.c`. These implementations
export the same API and must be linked into separate executables, not together.
