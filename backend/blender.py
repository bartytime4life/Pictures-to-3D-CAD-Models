"""Opt-in local handoff to an installed Blender, independent of geometry generation.

Blender is started with a fixed, static script shipped in this repository
(``backend/blender_relief.py``). The script reads only the generated ``relief.json``
and ``heightmap.png`` copied beside it; no request value becomes code or arguments.
"""

import glob
import hashlib
import json
import os
import shutil
import subprocess
import uuid
import zipfile
from pathlib import Path

TESTED_VERSION = "5.3.0"
MINIMUM_VERSION = "4.2 LTS"
DOWNLOAD_URL = "https://www.blender.org/download/"
BUNDLE_MEMBERS = (
    "build_relief.py",
    "relief.json",
    "heightmap.png",
    "model.stl",
    "README.md",
    "manifest.json",
)


class BlenderError(ValueError):
    """An unavailable Blender handoff, with a message suitable for the interface."""


def bridge_enabled():
    return os.environ.get("PICAD_ENABLE_BLENDER_LAUNCH") == "1"


def _usable(path):
    return path.is_file() and os.access(path, os.X_OK)


def executable():
    configured = os.environ.get("PICAD_BLENDER")
    if configured:
        path = Path(configured).expanduser()
        # One absolute executable path, never an argument string or shell command.
        # Symlinks are kept as given: a Snap launcher resolves to the generic snap binary.
        return str(path) if path.is_absolute() and _usable(path) else None
    found = shutil.which("blender")
    if found:
        return os.path.abspath(found)
    if os.name == "nt":
        folder = os.environ.get("ProgramFiles", "C:/Program Files")
        candidates = sorted(
            glob.glob(f"{folder}/Blender Foundation/Blender*/blender.exe"), reverse=True
        )
    else:
        candidates = ["/Applications/Blender.app/Contents/MacOS/Blender", "/snap/bin/blender"]
    return next((str(Path(c)) for c in candidates if _usable(Path(c))), None)


def status():
    enabled = bridge_enabled()
    detected = executable() is not None
    if not enabled:
        reason = (
            "Direct opening is off. Download the Blender ZIP, or enable the local "
            "launcher in project setup."
        )
    elif not detected:
        reason = "Blender was not found on this computer. Install it or set PICAD_BLENDER."
    else:
        reason = (
            "Ready to request opening on this computer. The installed version has not been checked."
        )
    return {
        "name": "Blender",
        "tested_version": TESTED_VERSION,
        "minimum_version": MINIMUM_VERSION,
        "download_url": DOWNLOAD_URL,
        "detected": detected,
        "bridge_enabled": enabled,
        "launch_available": enabled and detected,
        "launch_reason": reason,
        "version_status": "not_checked",
    }


def launch(bundle: Path, handoff_root: Path):
    """Extract a generated Blender bundle to a retained folder and open Blender there."""
    if not bridge_enabled():
        raise BlenderError(
            "Direct opening is off. Download the Blender ZIP or enable the local launcher."
        )
    program = executable()
    if not program:
        raise BlenderError("Blender was not found. Install it or configure PICAD_BLENDER first.")
    bundle = Path(bundle)
    if not bundle.is_file():
        raise BlenderError("This model has no Blender handoff. Build it again and try again.")
    handoff_root = Path(handoff_root)
    handoff_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    handoff_id = uuid.uuid4().hex
    directory = handoff_root / handoff_id
    directory.mkdir(mode=0o700)
    try:
        with zipfile.ZipFile(bundle) as archive:
            names = set(archive.namelist())
            if not names <= set(BUNDLE_MEMBERS) or "build_relief.py" not in names:
                raise BlenderError("The Blender handoff is incomplete. Build the model again.")
            for name in names:  # A fixed allow-list of flat names: no paths are created.
                (directory / name).write_bytes(archive.read(name))
                (directory / name).chmod(0o600)
        script = directory / "build_relief.py"
        record = {
            "format": "pictures-to-cad-blender-launch",
            "version": 1,
            "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
            "status": "prepared",
        }
        process = subprocess.Popen(
            [program, "--python", str(script.resolve())],
            cwd=directory,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            start_new_session=True,
        )
        record.update(status="launch_requested", pid=process.pid)
        (directory / "launch.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8"
        )
    except (OSError, zipfile.BadZipFile) as exc:
        raise BlenderError(
            "Blender could not be started. Download the Blender ZIP and open it manually."
        ) from exc
    return {
        "status": "launch_requested",
        "handoff_id": handoff_id,
        "detail": "Opening was requested with a retained local copy. Check the scene in Blender.",
    }
