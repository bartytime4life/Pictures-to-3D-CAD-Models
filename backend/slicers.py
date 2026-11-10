"""Opt-in local GUI handoff to fixed slicer programs, independent of CAD construction."""

import hashlib
import ipaddress
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from urllib.parse import urlsplit

PROGRAMS = {
    "bambu": {
        "id": "bambu",
        "name": "Bambu Studio",
        "target_version": "2.9.1",
        "source_url": "https://github.com/bambulab/BambuStudio",
        "release_url": "https://github.com/bambulab/BambuStudio/releases/tag/v02.09.01.70",
        "environment": "PICAD_BAMBU_STUDIO",
        "commands": ("bambu-studio", "BambuStudio", "bambustudio"),
    },
    "prusa": {
        "id": "prusa",
        "name": "PrusaSlicer",
        "target_version": "2.9.7",
        "source_url": "https://github.com/prusa3d/PrusaSlicer",
        "release_url": "https://github.com/prusa3d/PrusaSlicer/releases/tag/version_2.9.7",
        "environment": "PICAD_PRUSA_SLICER",
        "commands": ("prusa-slicer", "PrusaSlicer", "prusa-slicer-console"),
    },
}


class SlicerError(ValueError):
    """An unavailable local handoff, with a message suitable for the interface."""


def bridge_enabled():
    return os.environ.get("PICAD_ENABLE_SLICER_LAUNCH") == "1"


def executable_for(program_id):
    if program_id not in PROGRAMS:
        raise SlicerError("Choose Bambu Studio or PrusaSlicer.")
    program = PROGRAMS[program_id]
    configured = os.environ.get(program["environment"])
    if configured:
        path = Path(configured).expanduser()
        # Config is a single executable path, never an argument string or shell command.
        return (
            str(path.resolve())
            if path.is_absolute() and path.is_file() and os.access(path, os.X_OK)
            else None
        )
    for name in program["commands"]:
        found = shutil.which(name)
        if found:
            return str(Path(found).resolve())
    if os.name == "nt":
        folder = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
        candidates = (
            [folder / "Bambu Studio/bambu-studio.exe"]
            if program_id == "bambu"
            else [
                folder / "Prusa3D/PrusaSlicer/prusa-slicer.exe",
                folder / "Prusa3D/PrusaSlicer/PrusaSlicer.exe",
            ]
        )
    else:
        app_name = "BambuStudio" if program_id == "bambu" else "PrusaSlicer"
        candidates = [Path(f"/Applications/{app_name}.app/Contents/MacOS/{app_name}")]
    return next(
        (str(p.resolve()) for p in candidates if p.is_file() and os.access(p, os.X_OK)), None
    )


def program_status():
    enabled = bridge_enabled()
    result = []
    for program_id, program in PROGRAMS.items():
        detected = executable_for(program_id) is not None
        if not enabled:
            reason = "Direct opening is off. Download the handoff package, or enable the local launcher in project setup."
        elif not detected:
            reason = f"{program['name']} was not found on this computer. Install it or configure its executable path."
        else:
            reason = "Ready to request opening on this computer. The installed version and import result have not been checked."
        result.append(
            {
                **{
                    key: program[key]
                    for key in ("id", "name", "target_version", "release_url", "source_url")
                },
                "detected": detected,
                "launch_available": enabled and detected,
                "launch_reason": reason,
                "version_status": "not_checked",
                "bridge_enabled": enabled,
            }
        )
    return {"programs": result, "local_bridge_enabled": enabled}


def _loopback(host):
    if not host:
        return False
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def launch_request_allowed(client_host, request_url, origin, content_type):
    """Require local caller/host and a same-origin JSON request for host execution."""
    try:
        target = urlsplit(request_url)
        supplied = urlsplit(origin or "")
        # Accessing .port rejects malformed authority strings.
        expected = (target.scheme, target.hostname, target.port or 80)
        actual = (supplied.scheme, supplied.hostname, supplied.port or 80)
        return (
            _loopback(client_host)
            and _loopback(target.hostname)
            and target.scheme == "http"
            and expected == actual
            and not supplied.username
            and not supplied.password
            and supplied.path in ("", "/")
            and not supplied.query
            and not supplied.fragment
            and content_type.split(";", 1)[0].strip().lower() == "application/json"
        )
    except (ValueError, TypeError):
        return False


def launch(program_id, source, handoff_root):
    """Copy a generated 3MF, then request its GUI opening without slicing actions.

    Copies outlive temporary jobs and are never removed by Clear temporary exports.
    The API accepts only program IDs; the caller supplies its validated job path.
    """
    if program_id not in PROGRAMS:
        raise SlicerError("Choose Bambu Studio or PrusaSlicer.")
    if not bridge_enabled():
        raise SlicerError(
            "Direct opening is off. Download the handoff package or enable the local launcher."
        )
    executable = executable_for(program_id)
    if not executable:
        raise SlicerError(
            f"{PROGRAMS[program_id]['name']} was not found. Configure its installed executable first."
        )
    source = Path(source)
    if not source.is_file() or source.suffix != ".3mf":
        raise SlicerError("This model has no 3MF handoff. Update the model and try again.")
    handoff_root = Path(handoff_root)
    handoff_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    handoff_id = uuid.uuid4().hex
    directory = handoff_root / handoff_id
    directory.mkdir(mode=0o700)
    target = directory / "model.3mf"
    try:
        shutil.copyfile(source, target)
        target.chmod(0o600)
        record = {
            "format": "pictures-to-cad-native-handoff",
            "version": 1,
            "program_id": program_id,
            "target_version": PROGRAMS[program_id]["target_version"],
            "model_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "status": "prepared",
            "import_verified": False,
            "note": "Local copy retained independently of temporary CAD jobs. No print or slicing action was requested.",
        }
        record_path = directory / "handoff.json"
        record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        process = subprocess.Popen(
            [executable, str(target.resolve())],
            cwd=directory,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            start_new_session=True,
        )
        record.update(status="launch_requested", pid=process.pid)
        record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        # Keep a complete model copy if launch fails, rather than destroying a handoff.
        raise SlicerError(
            "The slicer could not be started. Download the handoff package and open it manually."
        ) from exc
    return {
        "status": "launch_requested",
        "program_id": program_id,
        "name": PROGRAMS[program_id]["name"],
        "handoff_id": handoff_id,
        "detail": "Opening was requested with a retained local model copy. Verify import, printer, filament and settings in the slicer.",
    }
