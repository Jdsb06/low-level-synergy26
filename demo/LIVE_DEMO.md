# Two-minute live CLI demonstration

Run from the `libmemctl` project directory on Linux. This is a local demonstration;
do not show private SSH configuration, credentials or other students' directories.

1. State the goal: implement the exact four-function C allocation API without
   calling the standard heap allocator. Show `include/libmemctl.h`.
2. Build and run independent checks:

   ```bash
   make
   make check
   ```

   Explain the failure-injection and producer-exit/cross-thread-free checks. Point
   out that trimming returns all allocator mappings in the checked workload.
3. Run unchanged official tests, if the official kit is installed:

   ```bash
   make public-test
   ```

4. Show a live measured workload, followed by its space sample:

   ```bash
   make benchmark
   ./build/benchmark_candidate 8 500000 12345 mixed
   ./build/benchmark_candidate space
   ```

5. Show the results table in `README.md` and the method in `docs/report.md`.
   Explain the selected large-reuse decision: eight-thread large throughput rose
   69.6% and malloc p99 fell 38.1% on the recorded shared-laptop trace. The costs
   are 34.7% more large-burst virtual-memory growth and an 11.1% lower mixed
   throughput median. Sparse live objects still pin regions; no official score
   or universal speedup is claimed. Source compatibility and clean-package
   execution are already verified, with coverage limits in the report.

The official selected statement requires source/build instructions, a design note
and benchmark results; the general listing also calls for functional demonstration.
The official form inspected 9 November labels its YouTube demo link optional.
`bash demo/run_demo.sh` runs the authored independent tests; actual PTY output and
a rendered replay are preserved in `demo/`, with two-minute speaker notes.
This is not an unedited desktop screen capture, and no public video was uploaded.
