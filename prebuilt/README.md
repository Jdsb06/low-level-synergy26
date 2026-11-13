# Verified Linux x86-64 build

These binaries and the static library were built from the source files listed in
`BUILD_INPUTS.sha256` using GCC 9.3.1, glibc 2.17 and strict C11 flags. The actual
build environment is in `BUILD_INFO.txt`; the build log and execution evidence are
in [the compatibility results](../results/compatibility/nhpc-build.txt).
No official starter, system runtime libraries or intermediate object files are bundled.

The executables passed on NHPC Linux 3.10/glibc 2.17 and native Ubuntu 26.04.1/glibc
2.43. This is verified coverage of those environments, not a guarantee for every
Linux version, architecture or C library. These are ordinary release builds;
rebuild using `make sanitize` for sanitizer instrumentation.

From the repository or extracted package root:

```bash
sha256sum -c prebuilt/SHA256SUMS
sha256sum -c prebuilt/BUILD_INPUTS.sha256
prebuilt/bin/test_allocator
prebuilt/bin/soak 12500 20261109 128
prebuilt/bin/large_lifetimes
```

`lib/libmemctl.a` contains the allocator. Its interface is `include/libmemctl.h`;
callers must link pthreads. The test executable intentionally uses linker wrappers
for mapping-failure injection and byte accounting. The soak exercises seeded
concurrency/ownership transfer; the lifetime probe touches payloads and reports
phase VM/RSS. None is the official grader. Rebuild via the root Makefile for a new
environment. Checksums use paths relative to the repository root.
