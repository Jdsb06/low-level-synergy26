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

5. Show the recorded longer five-process comparison and explain one trade-off:
   eight shards improved the local eight-thread mixed trace but lost about 3% at
   one thread. Cite the machine and method before quoting numbers. Close with the
   remaining fragmentation/debug/second-machine work; do not claim an official score.

The official selected statement requires source/build instructions, a design note
and benchmark results. Any final video/demo requirements from the general event
contract must still be reconciled during package review. No video exists yet.
