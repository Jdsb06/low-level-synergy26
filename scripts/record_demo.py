"""Record the actual demo subprocess as raw terminal output and an asciicast v2."""
import argparse
import codecs
from datetime import datetime, timezone
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pty
import struct
import subprocess
import termios
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default="cc")
    parser.add_argument("--output", type=Path, default=ROOT / "demo")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for name in ["terminal.cast", "run.log", "recording.json"]:
        if (args.output / name).exists():
            parser.error("recording exists; select a fresh output directory")
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 32, 128, 0, 0))
    env = dict(os.environ, CC=args.compiler, TERM="xterm-256color", LC_ALL="C")
    command = ["bash", "demo/run_demo.sh"]
    began = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    header = dict(version=2, width=128, height=32, timestamp=int(time.time()),
                  title="libmemctl actual authored-test terminal run", env={"TERM": env["TERM"]})
    process = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=slave, stderr=slave)
    os.close(slave)
    decoder = codecs.getincrementaldecoder("utf-8")("replace")
    with (args.output / "terminal.cast").open("x") as cast, (args.output / "run.log").open("xb") as raw:
        cast.write(json.dumps(header) + "\n")
        while True:
            try:
                data = os.read(master, 65536)
            except OSError as exc:
                if exc.errno == errno.EIO:
                    break
                raise
            if not data:
                break
            raw.write(data)
            cast.write(json.dumps([round(time.monotonic() - started, 6), "o", decoder.decode(data)]) + "\n")
        remaining = decoder.decode(b"", final=True)
        if remaining:
            cast.write(json.dumps([round(time.monotonic() - started, 6), "o", remaining]) + "\n")
    os.close(master)
    status = process.wait()
    record = dict(command=command, compiler=args.compiler, started_utc=began,
                  finished_utc=datetime.now(timezone.utc).isoformat(), exit=status,
                  duration_seconds=time.monotonic() - started,
                  source_sha256=hashlib.sha256((ROOT / "src/allocator.c").read_bytes()).hexdigest(),
                  files={name: hashlib.sha256((args.output / name).read_bytes()).hexdigest()
                         for name in ["terminal.cast", "run.log"]},
                  scope="Actual subprocess PTY output, preserved without editing; not a desktop screen capture.")
    (args.output / "recording.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
