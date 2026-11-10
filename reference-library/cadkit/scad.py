"""OpenSCAD discovery and rendering with ``-D`` parameter overrides.

Set ``CADKIT_OPENSCAD`` to an executable path to override discovery.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import tempfile
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
        return (self.returncode == 0 and not self.errors and self.output.is_file()
                and self.output.stat().st_size > 0)


def find_openscad() -> str | None:
    env = os.environ.get("CADKIT_OPENSCAD")
    if env:
        # which also rejects directories and non-executable files. An explicit
        # override must be usable; never silently fall back to another install.
        return shutil.which(env)
    for name in ("openscad", "openscad-nightly"):
        found = shutil.which(name)
        if found:
            return found
    return None


def version(executable: str | None = None) -> str | None:
    exe = executable or find_openscad()
    if not exe:
        return None
    try:
        proc = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    text = (proc.stdout + proc.stderr).strip()
    match = re.search(r"OpenSCAD version\s+(\S+)", text)
    return match.group(1) if match else None


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
    about six significant digits).

    Existing exports are replaced atomically only after a successful, nonempty
    render. A failed process, invalid parameters, or a timeout preserves them.
    ``RenderResult.command`` records the actual command, including its temporary
    output path; ``RenderResult.output`` is always the requested final path.
    """
    formatted_defines = [format_define(name, value) for name, value in (defines or {}).items()]
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("render timeout must be positive and finite")
    scad, out = Path(scad), Path(out)
    if (scad.resolve() == out.resolve()
            or (scad.exists() and out.exists() and scad.samefile(out))):
        raise ValueError("OpenSCAD source and output must be different files")
    if not scad.is_file():
        raise FileNotFoundError(f"OpenSCAD source was not found: {scad}")
    exe = executable or find_openscad()
    if not exe:
        raise FileNotFoundError("OpenSCAD was not found; install it or set CADKIT_OPENSCAD")
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, staged_name = tempfile.mkstemp(prefix=f".{out.stem}-", suffix=out.suffix, dir=out.parent)
    os.close(fd)
    staged = Path(staged_name)
    try:
        cmd = [exe, "-o", str(staged)]
        if export_format:
            cmd += ["--export-format", export_format]
        for define in formatted_defines:
            cmd += ["-D", define]
        cmd.append(str(scad))
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        log = proc.stdout + proc.stderr
        warnings = [line for line in log.splitlines() if line.lstrip().startswith("WARNING")]
        errors = [line for line in log.splitlines() if line.lstrip().startswith("ERROR")]
        if proc.returncode == 0 and not errors:
            if staged.is_file() and staged.stat().st_size > 0:
                staged.replace(out)
            else:
                errors.append("ERROR: OpenSCAD completed without a nonempty output file")
        return RenderResult(cmd, proc.returncode, proc.stdout, proc.stderr, out, version(exe), warnings, errors)
    finally:
        staged.unlink(missing_ok=True)
