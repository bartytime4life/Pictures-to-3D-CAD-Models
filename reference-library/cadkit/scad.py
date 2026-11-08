"""OpenSCAD discovery and rendering with ``-D`` parameter overrides.

Set ``CADKIT_OPENSCAD`` to an executable path to override discovery.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


@dataclass
class RenderResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    output: Path
    version: str | None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.errors and self.output.exists()


def find_openscad() -> str | None:
    env = os.environ.get("CADKIT_OPENSCAD")
    if env:
        return env if Path(env).exists() or shutil.which(env) else None
    for name in ("openscad", "openscad-nightly"):
        found = shutil.which(name)
        if found:
            return found
    return None


def version(executable: str | None = None) -> str | None:
    exe = executable or find_openscad()
    if not exe:
        return None
    proc = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30)
    text = (proc.stdout + proc.stderr).strip()
    match = re.search(r"OpenSCAD version\s+(\S+)", text)
    return match.group(1) if match else (text.splitlines()[0] if text else None)


def format_define(name: str, value) -> str:
    """Format one ``-D name=value`` argument with OpenSCAD literal syntax."""
    if not re.match(r"^[A-Za-z_$][A-Za-z0-9_]*$", name):
        raise ValueError(f"invalid OpenSCAD variable name {name!r}")
    if isinstance(value, bool):
        literal = "true" if value else "false"
    elif isinstance(value, int):
        literal = str(value)
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{name}: value must be finite")
        literal = repr(value)
    elif isinstance(value, str):
        literal = '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    elif value is None:
        raise ValueError(f"{name}: unknown (None) values cannot be passed to OpenSCAD")
    else:
        raise TypeError(f"{name}: unsupported value type {type(value).__name__}")
    return f"{name}={literal}"


def render(scad: str | Path, out: str | Path, defines: Mapping[str, object] | None = None,
           timeout: float = 300, export_format: str | None = "binstl",
           executable: str | None = None) -> RenderResult:
    """Render ``scad`` to ``out``. ``export_format`` 'binstl' keeps float32 precision;
    pass ``None`` to let OpenSCAD choose from the file extension (ASCII STL keeps
    about six significant digits)."""
    exe = executable or find_openscad()
    if not exe:
        raise FileNotFoundError("OpenSCAD was not found; install it or set CADKIT_OPENSCAD")
    scad, out = Path(scad), Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    cmd = [exe, "-o", str(out)]
    if export_format:
        cmd += ["--export-format", export_format]
    for name, value in (defines or {}).items():
        cmd += ["-D", format_define(name, value)]
    cmd.append(str(scad))
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    log = proc.stdout + proc.stderr
    warnings = [line for line in log.splitlines() if line.startswith("WARNING")]
    errors = [line for line in log.splitlines() if line.startswith("ERROR")]
    return RenderResult(cmd, proc.returncode, proc.stdout, proc.stderr, out, version(exe), warnings, errors)
