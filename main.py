#!/usr/bin/env python3
"""Entry point for the make.fun news-image-20261121 entry.

The picture itself is a fixed build artifact: draw.py (PIL) rendered
entry.png while the entry was being built, and this program only ships
that file to the grader. It copies ./entry.png into the directory named
by MAKEFUN_OUTPUT_DIR (or /output when the variable is unset), after
checking the file exists and really is a PNG. Only the standard
library is used, so the two grading runs produce byte-identical output.
"""

from hashlib import sha256
from pathlib import Path
import os
import shutil
import sys

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
CHUNK = 1 << 16


def digest(path):
    """SHA-256 hex digest of a file, streamed in 64 KiB blocks."""
    hasher = sha256()
    with open(path, "rb") as stream:
        while True:
            block = stream.read(CHUNK)
            if not block:
                break
            hasher.update(block)
    return hasher.hexdigest()


def fail(message):
    print("error:", message, file=sys.stderr)
    raise SystemExit(1)


def run():
    source = Path(__file__).resolve().parent / "entry.png"
    if not source.is_file():
        fail(f"missing source image: {source}")
    with open(source, "rb") as stream:
        if stream.read(len(PNG_MAGIC)) != PNG_MAGIC:
            fail(f"source image is not a PNG: {source}")
    target_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "entry.png"
    shutil.copyfile(source, target)
    print("wrote", target)
    print("sha256", digest(target))
    print("bytes", target.stat().st_size)


if __name__ == "__main__":
    run()
