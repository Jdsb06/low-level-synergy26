#!/usr/bin/env python3
"""Require real ASan diagnostics; a crash alone cannot pass a negative control."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sizes = [0, 1, 7, 8, 15, 16, 17, 31, 32, 33, 255, 256, 257,
             1024, 1025, 4096, 4097, 16384, 16385, 65536, 65537, 69616, 69617,
             1048576, 1048577]
    cases = [("valid", n) for n in sizes]
    cases += [("overrun", n) for n in sizes]
    cases += [("underflow", 33), ("underflow", 65537), ("freed", 33),
              ("shrink", 48), ("grow", 33), ("freed", 65537), ("reused", 65537),
              ("freed", 1048576), ("reused", 1048576)]
    env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:halt_on_error=1:abort_on_error=0:exitcode=86")
    records = []
    for case, size in cases:
        command = [str(args.binary.resolve()), case, str(size)]
        try:
            run = subprocess.run(command, env=env, capture_output=True, text=True, timeout=20)
            diagnostic = ("ERROR: AddressSanitizer: use-after-poison" in run.stderr
                          and re.search(r"#0 [^\n]*asan_negative\.c:\d+", run.stderr) is not None
                          and "WRITE of size 1" in run.stderr)
            passed = ((run.returncode == 0 and "PASS: valid control" in run.stdout
                       and not run.stderr) if case == "valid"
                      else run.returncode == 86 and diagnostic)
            records.append(dict(command=command, exit=run.returncode, passed=passed,
                                stdout=run.stdout, stderr=run.stderr))
        except subprocess.TimeoutExpired:
            records.append(dict(command=command, passed=False, error="timeout"))
    result = dict(environment=platform.platform(), python=sys.version,
                  asan_options=env["ASAN_OPTIONS"],
                  binary_sha256=hashlib.sha256(args.binary.read_bytes()).hexdigest(),
                  source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in [Path("src/allocator.c"), Path("tests/asan_negative.c")]},
                  cases=records)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    failures = [r for r in records if not r["passed"]]
    valid_count = sum(case == "valid" for case, _ in cases)
    print("Annotation controls: {}/{} passed ({} valid, {} deliberate errors)".format(
        len(records) - len(failures), len(records), valid_count, len(cases) - valid_count))
    for record in failures:
        print(json.dumps(record))
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
