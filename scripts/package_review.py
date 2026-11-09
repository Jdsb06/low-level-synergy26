"""Create normalized, content-addressed review archives from an explicit file allowlist."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile
import zipfile

from verify_submission import verify

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = [rb"-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----",
                   rb"gh[pousr]_[A-Za-z0-9]{30,}", rb"github_pat_[A-Za-z0-9_]{30,}",
                   rb"AKIA[A-Z0-9]{16}", rb"sk-proj-[A-Za-z0-9_-]{20,}"]


def safe_write(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError("Refusing to overwrite different artifact: " + str(path))
    else:
        with path.open("xb") as handle:
            handle.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--prebuilt", type=Path,
                        help="optional NHPC input directory to cross-check against the committed binaries")
    args = parser.parse_args()
    verification = verify(ROOT)
    spec = json.loads((ROOT / "scripts/package-contents.json").read_text())
    files = spec["files"]
    if len(files) != len(set(files)):
        raise ValueError("Duplicate package path")
    payloads = {}
    for name in sorted(files):
        parts = PurePosixPath(name).parts
        if (not parts or PurePosixPath(name).is_absolute() or ".." in parts
                or any(p in {"official", ".git", ".workspace-git", ".aws", ".codex", ".agents", "dist", "__pycache__"}
                       for p in parts) or any(p.startswith("build") for p in parts[:-1])):
            raise ValueError("Forbidden package path: " + name)
        source = ROOT / name
        if source.is_symlink() or not source.resolve().is_relative_to(ROOT) or not source.is_file():
            raise ValueError("Missing, linked or out-of-project input: " + name)
        data = source.read_bytes()
        if source.suffix not in {".png", ".pdf"} and any(re.search(p, data) for p in SECRET_PATTERNS):
            raise ValueError("Credential pattern in " + name)
        payloads[name] = data
    if args.prebuilt:
        base = args.prebuilt.resolve()
        def read_relative(name):
            path = base / name
            if path.is_symlink() or not path.resolve().is_relative_to(base):
                raise ValueError("Unsafe prebuilt path")
            return path.read_bytes()
        source_inputs = {}
        for line in read_relative("INPUT_SHA256").decode().splitlines():
            digest, name = line.split(None, 1)
            source_inputs[name.strip()] = digest
        required_inputs = {"Makefile", "include/libmemctl.h", "src/allocator.c", "tests/test_allocator.c",
                           "tests/soak.c", "scripts/check_symbols.py", "bench/lifetimes.c", "bench/profile.h"}
        if set(source_inputs) != required_inputs:
            raise ValueError("Unexpected prebuilt source inventory")
        for name, digest in source_inputs.items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
                raise ValueError("Prebuilt input no longer matches source: " + name)
        inventories = {"BINARY_SHA256": {"build/test_allocator", "build/soak", "build/large_lifetimes"},
                       "LIBRARY_SHA256": {"build/libmemctl.a", "build/allocator.o"}}
        for manifest_name, expected_names in inventories.items():
            seen = set()
            for line in read_relative(manifest_name).decode().splitlines():
                digest, name = line.split(None, 1)
                name = name.strip()
                if name not in expected_names or name in seen or not re.fullmatch(r"[0-9a-f]{64}", digest):
                    raise ValueError("Unexpected prebuilt binary inventory")
                seen.add(name)
                if hashlib.sha256(read_relative(name)).hexdigest() != digest:
                    raise ValueError("Prebuilt binary checksum mismatch")
            if seen != expected_names:
                raise ValueError("Incomplete prebuilt binary inventory")
        if hashlib.sha256(read_relative("include/libmemctl.h")).hexdigest() != source_inputs["include/libmemctl.h"]:
            raise ValueError("Prebuilt header checksum mismatch")
        for source, target in {"build/libmemctl.a": "lib/libmemctl.a", "build/test_allocator": "bin/test_allocator",
                               "build/soak": "bin/soak", "build/large_lifetimes": "bin/large_lifetimes",
                               "include/libmemctl.h": "include/libmemctl.h", "build-toolchain.txt": "BUILD_INFO.txt",
                               "INPUT_SHA256": "BUILD_INPUTS.sha256"}.items():
            name = "prebuilt/" + target
            if payloads.get(name) != read_relative(source):
                raise ValueError("External prebuilt differs from reviewed committed artifact: " + name)
    for required in ["Makefile", "src/allocator.c", "include/libmemctl.h", "README.md", "docs/author.md",
                     "docs/architecture.md", "docs/review-guide.md", "output/pdf/libmemctl-review.pdf"]:
        if required not in payloads:
            raise ValueError("Required review input omitted: " + required)
    manifest = "".join(hashlib.sha256(data).hexdigest() + "  " + name + "\n"
                       for name, data in sorted(payloads.items())).encode()
    digest = hashlib.sha256(manifest).hexdigest()
    payloads["PACKAGE_INFO.json"] = (json.dumps(dict(format_version=1,
        purpose="Submission-ready repository package; not an official submission receipt",
        source_sha256=hashlib.sha256(payloads["src/allocator.c"]).hexdigest(),
        content_manifest_sha256=digest, input_files=len(payloads), prebuilt_included=True,
        integrity_verification=verification["status"]), indent=2) + "\n").encode()
    # Include package metadata in the integrity check, without a self-hash cycle.
    manifest += hashlib.sha256(payloads["PACKAGE_INFO.json"]).hexdigest().encode() + b"  PACKAGE_INFO.json\n"
    payloads["MANIFEST.sha256"] = manifest
    base = "libmemctl-IMT2024022-review-" + digest[:12]
    tar_bytes = io.BytesIO()
    with tarfile.open(fileobj=tar_bytes, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name, data in sorted(payloads.items()):
            entry = tarfile.TarInfo("libmemctl-review/" + name)
            entry.size = len(data)
            entry.mode = 0o755 if name.endswith(".sh") or name.startswith("prebuilt/bin/") else 0o644
            entry.mtime = entry.uid = entry.gid = 0
            entry.uname = entry.gname = ""
            archive.addfile(entry, io.BytesIO(data))
    compressed = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode="wb", filename="", mtime=0, compresslevel=9) as handle:
        handle.write(tar_bytes.getvalue())
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(payloads.items()):
            entry = zipfile.ZipInfo("libmemctl-review/" + name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (stat.S_IFREG | (0o755 if name.endswith(".sh") or name.startswith("prebuilt/bin/") else 0o644)) << 16
            archive.writestr(entry, data)
    args.output.mkdir(parents=True, exist_ok=True)
    outputs = {base + ".tar.gz": compressed.getvalue(), base + ".zip": zip_bytes.getvalue()}
    for name, data in outputs.items():
        safe_write(args.output / name, data)
    checksums = "".join(hashlib.sha256(data).hexdigest() + "  " + name + "\n" for name, data in outputs.items())
    safe_write(args.output / (base + ".SHA256SUMS"), checksums.encode())
    print(json.dumps(dict(files=len(payloads), content_manifest_sha256=digest,
                         artifacts={str(args.output / n): hashlib.sha256(d).hexdigest() for n, d in outputs.items()}), indent=2))


if __name__ == "__main__":
    main()
