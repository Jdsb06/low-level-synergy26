"""Run an offline judge check in fresh build directories and save exact results."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sanitizers", action="store_true",
                        help="also run ASan/UBSan and the 59 annotation controls")
    parser.add_argument("--official-dir", type=Path,
                        help="separately obtained SYSPROG10 directory containing tests/test_runner.c")
    args = parser.parse_args()
    if sys.version_info < (3, 9) or platform.system() != "Linux":
        parser.error("Linux and Python 3.9+ are required")
    compiler_text = os.environ.get("CC", "cc")
    compiler = shlex.split(compiler_text)
    if not compiler:
        parser.error("CC must name a C11 compiler")
    for command in ["make", "ar", "nm", "timeout", compiler[0]]:
        if shutil.which(command) is None:
            parser.error("missing build dependency: " + command)
    if args.official_dir:
        args.official_dir = args.official_dir.resolve()
        if not (args.official_dir / "tests/test_runner.c").is_file():
            parser.error("--official-dir must contain tests/test_runner.c")

    build = Path(tempfile.mkdtemp(prefix="build-evaluate-", dir=ROOT))
    native = (build / "native").relative_to(ROOT).as_posix()
    sanitized = (build / "sanitized").relative_to(ROOT).as_posix()
    result_path = build / "evaluation.json"
    record = dict(started_utc=datetime.now(timezone.utc).isoformat(), status="RUNNING",
                  platform=platform.platform(), python=sys.version, compiler=compiler,
                  source_sha256=hashlib.sha256((ROOT / "src/allocator.c").read_bytes()).hexdigest(),
                  options=dict(sanitizers=args.sanitizers,
                               official_dir=str(args.official_dir) if args.official_dir else None),
                  steps=[])

    def save():
        result_path.write_text(json.dumps(record, indent=2) + "\n")

    def run(label, command, environment=None, expected_stdout=None):
        print("[{}] {}".format(len(record["steps"]) + 1, label), flush=True)
        started = time.monotonic()
        step = dict(label=label, command=command, cwd=str(ROOT))
        try:
            result = subprocess.run(command, cwd=ROOT, env=environment,
                                    capture_output=True, text=True, timeout=300)
            step.update(exit=result.returncode, stdout=result.stdout, stderr=result.stderr)
        except subprocess.TimeoutExpired as error:
            step.update(exit=None, error="300-second timeout", stdout=str(error.stdout or ""),
                        stderr=str(error.stderr or ""))
        step["seconds"] = round(time.monotonic() - started, 3)
        record["steps"].append(step)
        save()
        if step["exit"] != 0:
            raise RuntimeError(label + " failed\n" + step["stdout"][-2000:] + step["stderr"][-2000:])
        if expected_stdout is not None and step["stdout"] != expected_stdout:
            raise RuntimeError(label + " output differs from the documented example")

    save()
    make = ["make", "CC=" + compiler_text, "PYTHON=" + sys.executable]
    try:
        run("Compiler version", compiler + ["--version"])
        run("Source, prebuilt, recording and document integrity",
            [sys.executable, "scripts/verify_submission.py"])
        run("Fresh native build, forbidden symbols and independent tests",
            make + ["BUILD_DIR=" + native, "CFLAGS=-O2 -g", "check"])
        example = native + "/example"
        run("Build the public-API example", compiler + ["-std=c11", "-Wall", "-Wextra", "-Werror",
            "-Iinclude", "examples/basic.c", native + "/libmemctl.a", "-pthread", "-o", example])
        run("Run the documented example", [str(ROOT / example)], expected_stdout=(
            "calloc: 8 zeroed items\n"
            "realloc: 8 values preserved in a 32-item buffer\n"
            "free + trim: example complete\n"))
        if args.official_dir:
            run("Unchanged official public tests", make + ["BUILD_DIR=" + native,
                "CFLAGS=-O2 -g", "OFFICIAL_DIR=" + str(args.official_dir), "public-test"])
        if args.sanitizers:
            environment = os.environ.copy()
            environment["ASAN_OPTIONS"] = "detect_leaks=0"
            run("Fresh ASan/UBSan build, independent tests and 59 annotation controls",
                make + ["BUILD_DIR=" + sanitized,
                        "CFLAGS=-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all",
                        "check", "annotation-check"], environment)
    except (OSError, RuntimeError) as error:
        record["status"] = "FAIL"
        record["error"] = str(error)
        print(str(error), file=sys.stderr)
    else:
        record["status"] = "PASS"
    record["finished_utc"] = datetime.now(timezone.utc).isoformat()
    save()
    print("{}: evaluation results saved to {}".format(record["status"], result_path))
    print("This check does not calculate an official score or run hidden tests.")
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
