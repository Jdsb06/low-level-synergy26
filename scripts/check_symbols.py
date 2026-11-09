"""Reject every forbidden allocator entry point from the SYSPROG10 contract."""

import subprocess
import sys

forbidden = {
    "malloc", "free", "calloc", "realloc", "aligned_alloc", "posix_memalign",
    "memalign", "valloc", "pvalloc", "strdup", "sbrk",
}
result = subprocess.run(["nm", "-u", sys.argv[1]], text=True, capture_output=True, check=True)
symbols = {line.split()[-1].split("@")[0] for line in result.stdout.splitlines() if line.split()}
bad = sorted(forbidden & symbols)
if bad:
    raise SystemExit("Forbidden allocation references: " + ", ".join(bad))
print("PASS forbidden allocation symbol check")
