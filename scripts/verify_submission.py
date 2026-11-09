"""Verify selected source, shipped binaries, recorded media and package inventory offline."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
BUILD_INPUTS = {"Makefile", "include/libmemctl.h", "src/allocator.c", "tests/test_allocator.c",
                "tests/soak.c", "scripts/check_symbols.py", "bench/lifetimes.c", "bench/profile.h"}
PREBUILT_FILES = {"prebuilt/README.md", "prebuilt/BUILD_INFO.txt", "prebuilt/BUILD_INPUTS.sha256",
                  "prebuilt/include/libmemctl.h", "prebuilt/lib/libmemctl.a",
                  "prebuilt/bin/test_allocator", "prebuilt/bin/soak", "prebuilt/bin/large_lifetimes"}
FORBIDDEN = {"official", ".git", ".workspace-git", ".aws", ".codex", ".agents", "dist", "__pycache__"}


def checked_path(root, name):
    parts = PurePosixPath(name).parts
    if (not parts or PurePosixPath(name).is_absolute() or ".." in parts
            or any(p in FORBIDDEN for p in parts)
            or any(p.startswith("build") for p in parts[:-1])):
        raise ValueError("Unsafe deliverable path: " + name)
    path = root / name
    if (any(parent.is_symlink() for parent in [path, *path.parents] if parent != root.parent)
            or not path.resolve().is_relative_to(root.resolve()) or not path.is_file()):
        raise ValueError("Missing or linked deliverable: " + name)
    return path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_manifest(root, name, expected):
    seen = set()
    for line in checked_path(root, name).read_text().splitlines():
        fields = line.split(None, 1)
        if len(fields) != 2:
            raise ValueError("Invalid checksum line in " + name)
        digest, relative = fields
        if relative not in expected or relative in seen or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Unexpected checksum entry in " + name)
        if sha(checked_path(root, relative)) != digest:
            raise ValueError("Checksum mismatch: " + relative)
        seen.add(relative)
    if seen != expected:
        raise ValueError("Incomplete checksum inventory in " + name)
    return len(seen)


def verify(root=ROOT):
    root = root.resolve()
    spec = json.loads(checked_path(root, "SUBMISSION.json").read_text())
    if (spec["format_version"] != 1 or spec["question_id"] != "SYSPROG10"
            or spec["track"] != "Systems Programming"):
        raise ValueError("Wrong submission identity")
    if sha(checked_path(root, "src/allocator.c")) != spec["source_sha256"]:
        raise ValueError("Selected allocator source hash mismatch")
    required = set(spec["required_paths"]) | {"SUBMISSION.json", "PACKAGE_CONTENTS.json"}
    for name in required:
        checked_path(root, name)
    for name, digest in spec["artifacts"].items():
        if sha(checked_path(root, name)) != digest:
            raise ValueError("Submission artifact checksum mismatch: " + name)

    check_manifest(root, "prebuilt/BUILD_INPUTS.sha256", BUILD_INPUTS)
    check_manifest(root, "prebuilt/SHA256SUMS", PREBUILT_FILES)
    if (root / "prebuilt/include/libmemctl.h").read_bytes() != (root / "include/libmemctl.h").read_bytes():
        raise ValueError("Prebuilt public header differs from current source")
    for name in sorted(PREBUILT_FILES):
        if name.startswith("prebuilt/bin/"):
            path = root / name
            if not path.read_bytes().startswith(b"\x7fELF") or path.stat().st_mode & 0o111 == 0:
                raise ValueError("Not an executable ELF: " + name)
    if not (root / "prebuilt/lib/libmemctl.a").read_bytes().startswith(b"!<arch>\n"):
        raise ValueError("Invalid static library")

    recording = json.loads(checked_path(root, "demo/recording.json").read_text())
    if recording["exit"] != 0 or recording["source_sha256"] != spec["source_sha256"]:
        raise ValueError("Demo did not run the selected source successfully")
    if set(recording["files"]) != {"terminal.cast", "run.log"}:
        raise ValueError("Unexpected recording inventory")
    for name, digest in recording["files"].items():
        if sha(checked_path(root, "demo/" + name)) != digest:
            raise ValueError("Recorded terminal checksum mismatch: " + name)
    video = json.loads(checked_path(root, "demo/video.json").read_text())
    if (video["cast_sha256"] != recording["files"]["terminal.cast"]
            or video["video_sha256"] != sha(root / "demo/terminal-replay.mp4")):
        raise ValueError("Video and original recording do not match provenance")

    package = json.loads(checked_path(root, "PACKAGE_CONTENTS.json").read_text())["files"]
    if len(package) != len(set(package)):
        raise ValueError("Duplicate package input")
    if not (required | PREBUILT_FILES | BUILD_INPUTS).issubset(set(package)):
        raise ValueError("Package omits a required deliverable")
    for name in package:
        checked_path(root, name)

    # Judge-facing links must also work in a standalone clone/extracted package.
    links = 0
    for name in ["README.md", "SUBMISSION.md", "TECHNICAL_REPORT.md", "REVIEW_GUIDE.md", "prebuilt/README.md"]:
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", (root / name).read_text()):
            target = urlsplit(link.strip("<>"))
            if target.scheme or target.netloc or not target.path:
                continue
            path = ((root / name).parent / unquote(target.path)).resolve()
            if not path.is_relative_to(root) or not path.exists():
                raise ValueError("Broken local link in " + name + ": " + link)
            if path.is_file() and path.relative_to(root).as_posix() not in package:
                raise ValueError("Linked deliverable omitted from package: " + link)
            links += 1
    return dict(status="PASS", source_sha256=spec["source_sha256"],
                package_input_files=len(package), prebuilt_checksums=len(PREBUILT_FILES),
                prebuilt_source_inputs=len(BUILD_INPUTS), local_links_checked=links,
                note="Integrity verification is separate from executed tests and official submission.")


def main():
    try:
        result = verify()
    except (ValueError, KeyError, OSError, TypeError) as error:
        print("Submission verification FAILED: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
