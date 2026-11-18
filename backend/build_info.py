"""Path-free build diagnostics, independent of installed app dependencies.

The backend identity records source present when this module first imports. It is
a startup source snapshot, not an attestation of every byte loaded by Python.
"""

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import time
from pathlib import Path
from types import MappingProxyType

ROOT = Path(__file__).resolve().parents[1]
GIT_TIMEOUT = 0.75
MAX_MANIFEST_BYTES = 4096
MAX_SOURCE_FILES = 4096
MAX_SOURCE_FILE_BYTES = 4 * 1024 * 1024
MAX_SOURCE_BYTES = 32 * 1024 * 1024
REVISION = re.compile(r"[0-9a-f]{40}\Z")
SOURCE_HASH = re.compile(r"[0-9a-f]{64}\Z")


def source_fingerprint(root):
    """Hash framed relative paths and bytes of regular backend Python/config files.

    After the picad-backend-inputs-v1 NUL-terminated domain, each sorted entry is
    an 8-byte big-endian path length, its UTF-8 POSIX path,
    an 8-byte content length, and those contents. Symlinks are excluded. Any read
    failure or bound violation makes the fingerprint unavailable.
    """
    root = Path(root)
    try:
        paths = [
            path
            for path in (root / "backend").rglob("*.py")
            if not path.is_symlink() and path.is_file()
        ]
        if not paths:
            return None
        paths.extend(
            root / name
            for name in ("requirements.txt", "pyproject.toml")
            if (root / name).exists() and not (root / name).is_symlink()
        )
        if len(paths) > MAX_SOURCE_FILES:
            return None
        digest, total = hashlib.sha256(b"picad-backend-inputs-v1\0"), 0
        for path in sorted(
            paths, key=lambda candidate: candidate.relative_to(root).as_posix().encode("utf-8")
        ):
            file_stat = path.stat()
            if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_size > MAX_SOURCE_FILE_BYTES:
                return None
            total += file_stat.st_size
            if total > MAX_SOURCE_BYTES:
                return None
            with path.open("rb") as source:
                data = source.read(MAX_SOURCE_FILE_BYTES + 1)
            if len(data) != file_stat.st_size:
                return None
            name = path.relative_to(root).as_posix().encode("utf-8")
            digest.update(len(name).to_bytes(8, "big"))
            digest.update(name)
            digest.update(len(data).to_bytes(8, "big"))
            digest.update(data)
        return digest.hexdigest()
    except (OSError, ValueError, UnicodeError, RecursionError):
        return None


def git_identity(root):
    """Best-effort local Git metadata with one short budget and no index writes."""
    git = shutil.which("git")
    if not git:
        return {"revision": None, "dirty": None}
    deadline = time.monotonic() + GIT_TIMEOUT
    environment = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}

    def run(arguments):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        return subprocess.run(
            [git, "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", *arguments],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
            timeout=remaining,
        ).stdout

    revision = None
    try:
        candidate = run(["rev-parse", "--verify", "HEAD"]).strip()
        if not REVISION.fullmatch(candidate):
            return {"revision": None, "dirty": None}
        revision = candidate
        dirty = bool(run(["status", "--porcelain=v1", "--untracked-files=normal"]).strip())
        return {"revision": revision, "dirty": dirty}
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
        return {"revision": revision, "dirty": None}


def capture_backend_identity(root):
    return {**git_identity(root), "source_sha256": source_fingerprint(root)}


# Captured once. Requests and doctor summaries do not rescan the backend source.
BACKEND_STARTUP_IDENTITY = MappingProxyType(capture_backend_identity(ROOT))


def read_interface_identity(root=ROOT):
    """Return only validated identity fields from the small Vite build manifest."""
    path = Path(root) / "frontend" / "dist" / "build-info.json"
    try:
        if path.is_symlink():
            return None
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
        try:
            file_stat = os.fstat(descriptor)
            if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_size > MAX_MANIFEST_BYTES:
                return None
            data = os.read(descriptor, MAX_MANIFEST_BYTES + 1)
        finally:
            os.close(descriptor)
        if len(data) > MAX_MANIFEST_BYTES:
            return None
        manifest = json.loads(data.decode("utf-8"))
        if (
            not isinstance(manifest, dict)
            or set(manifest) != {"schema", "revision", "dirty", "source_sha256"}
            or type(manifest["schema"]) is not int
            or manifest["schema"] != 1
            or manifest["revision"] is not None
            and (
                not isinstance(manifest["revision"], str)
                or not REVISION.fullmatch(manifest["revision"])
            )
            or manifest["dirty"] is not None
            and type(manifest["dirty"]) is not bool
            or manifest["source_sha256"] is not None
            and (
                not isinstance(manifest["source_sha256"], str)
                or not SOURCE_HASH.fullmatch(manifest["source_sha256"])
            )
        ):
            return None
        return {key: manifest[key] for key in ("revision", "dirty", "source_sha256")}
    except (OSError, ValueError, UnicodeError, RecursionError):
        return None


def runtime_identity(root=ROOT):
    return {
        "backend": dict(BACKEND_STARTUP_IDENTITY),
        "interface": read_interface_identity(root),
    }
