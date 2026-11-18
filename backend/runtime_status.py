"""Read-only setup checks; importing this module requires only the Python standard library.

The report is safe to show in the local app: it omits paths, configured addresses,
model names and exception contents. These checks do not execute CAD or inference.
"""

import http.client
import importlib.metadata
import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .build_info import runtime_identity

ROOT = Path(__file__).resolve().parents[1]
AI_TIMEOUT = 1.5
MAX_METADATA_BYTES = 512 * 1024
PYTHON_PACKAGES = (
    "cadquery",
    "fastapi",
    "uvicorn",
    "pillow",
    "python-multipart",
    "opencv-python-headless",
    "shapely",
    "pi-heif",
    "onnxruntime",
)
MODEL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}\Z")


def _check(identifier, label, status, required, detail, command=None, action_label=None):
    result = {
        "id": identifier,
        "label": label,
        "status": status,
        "required": required,
        "detail": detail,
    }
    if command:
        result["action"] = {"label": action_label or "Next step", "command": command}
    return result


class _BuiltAssets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        value = values.get("src") if tag == "script" else values.get("href")
        if value and value.startswith("/assets/"):
            self.assets.append(value)


def _frontend_ready(root):
    dist = root / "frontend" / "dist"
    try:
        parser = _BuiltAssets()
        parser.feed((dist / "index.html").read_text("utf-8"))
        if not parser.assets:
            return False
        for asset in parser.assets:
            path = (dist / unquote(urlsplit(asset).path).lstrip("/")).resolve()
            if not path.is_relative_to(dist.resolve()) or not path.is_file():
                return False
        return True
    except (OSError, UnicodeError, ValueError):
        return False


def _ollama_address():
    parsed = urlsplit(os.environ.get("PICTURES_CAD_OLLAMA_URL", "http://127.0.0.1:11434"))
    host = parsed.hostname
    if (
        parsed.scheme != "http"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("An HTTP loopback address is required")
    if host == "localhost":
        host = "127.0.0.1"
    elif not ipaddress.ip_address(host).is_loopback:
        raise ValueError("A loopback address is required")
    port = parsed.port if parsed.port is not None else 11434
    if not 1 <= port <= 65535:
        raise ValueError("Invalid port")
    return host, port


def _metadata_request(address, method, path, deadline, payload=None):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError
    connection = http.client.HTTPConnection(*address, timeout=remaining)
    try:
        body = json.dumps(payload).encode() if payload is not None else None
        connection.request(method, path, body, headers={"Content-Type": "application/json"})
        response_socket = connection.sock
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError("Metadata request failed")
        data = bytearray()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            if response_socket is not None:
                response_socket.settimeout(remaining)
            chunk = response.read1(min(65536, MAX_METADATA_BYTES + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > MAX_METADATA_BYTES:
                raise ValueError("Metadata response is too large")
        result = json.loads(data)
        if not isinstance(result, dict) or "error" in result:
            raise ValueError("Invalid metadata")
        return result
    finally:
        connection.close()


def _cloud_model(model):
    return (
        "cloud" in re.split(r"[:/._-]", str(model.get("name", "")).lower())
        or bool(model.get("remote_host"))
        or bool(model.get("remote_model"))
    )


def _ollama_check():
    action = "./scripts/ollama.sh check"
    try:
        address = _ollama_address()
    except ValueError:
        return _check(
            "ollama",
            "Local AI (optional)",
            "limited",
            False,
            "Use an HTTP loopback Ollama address. Photo tracing and CAD work without AI.",
            action,
            "Review local AI setup",
        )
    deadline = time.monotonic() + AI_TIMEOUT
    try:
        tags = _metadata_request(address, "GET", "/api/tags", deadline)
        models = tags.get("models")
        if not isinstance(models, list) or len(models) > 128:
            raise ValueError("Invalid model list")
        candidates = [
            model
            for model in models
            if isinstance(model, dict)
            and isinstance(model.get("name"), str)
            and MODEL_NAME.fullmatch(model["name"])
            and "://" not in model["name"]
            and isinstance(model.get("size"), int)
            and model["size"] > 0
            and not _cloud_model(model)
        ]
        preferred = os.environ.get("PICTURES_CAD_OLLAMA_MODEL", "qwen3:1.7b")
        candidates.sort(key=lambda model: (model["name"] != preferred, model["size"]))
        for model in candidates:
            details = _metadata_request(
                address, "POST", "/api/show", deadline, {"model": model["name"]}
            )
            capabilities = details.get("capabilities")
            if (
                isinstance(capabilities, list)
                and "completion" in capabilities
                and not _cloud_model({"name": model["name"], **details})
            ):
                return _check(
                    "ollama",
                    "Local AI (optional)",
                    "ready",
                    False,
                    "Ollama reports an installed local chat model. No inference was run.",
                    ".venv/bin/python scripts/check_ai.py --probe",
                    "Test AI responses (optional)",
                )
        detail = (
            "Ollama is running; no local chat model was verified. Embedding and cloud models "
            "cannot answer creative prompts. Photo tracing and CAD work without AI."
        )
    except (OSError, ValueError, UnicodeError, http.client.HTTPException):
        detail = (
            "Local AI was not verified within the short readiness check. "
            "Photo tracing and CAD work without AI; review Ollama setup when needed."
        )
    return _check(
        "ollama", "Local AI (optional)", "limited", False, detail, action, "Check local AI"
    )


def _development_check():
    try:
        node = shutil.which("node")
        npm = shutil.which("npm")
        if not node or not npm:
            raise ValueError
        result = subprocess.run(
            [node, "--version"], capture_output=True, text=True, timeout=1, check=True
        )
        match = re.fullmatch(r"v(\d+)\.(\d+)\.\d+\s*", result.stdout)
        if not match or tuple(map(int, match.groups())) < (22, 12):
            raise ValueError
        return _check(
            "development",
            "Frontend development (optional)",
            "ready",
            False,
            "Node.js 22.12+ and npm were found. The built app does not need Node.js.",
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        return _check(
            "development",
            "Frontend development (optional)",
            "limited",
            False,
            "Install Node.js 22.12+ and npm to build or change the interface. "
            "The already built app can run without them.",
        )


def summarize_runtime(*, include_development=False, check_ai=True, root=None):
    """Return path-free readiness for the current interpreter and this checkout.

    Optional capability failures never block the app. The Ollama check reads only
    loopback metadata, with a shared 1.5-second budget and a bounded response size.
    """
    root = ROOT if root is None else Path(root)
    checks = []
    environment = root / ".venv"
    environment_ready = os.access(environment / "bin" / "python", os.X_OK)
    python_ready = (
        sys.version_info[:2] == (3, 12) and Path(sys.prefix).resolve() == environment.resolve()
    )
    checks.append(
        _check(
            "python",
            "App Python environment",
            "ready" if environment_ready and python_ready else "missing",
            True,
            "The app environment uses the supported Python 3.12 runtime."
            if environment_ready and python_ready
            else "Prepare the app environment with Python 3.12, then run this check again.",
            None if environment_ready and python_ready else "./scripts/setup.sh",
            "Prepare app environment",
        )
    )
    missing = []
    for name in PYTHON_PACKAGES:
        try:
            importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            missing.append(name)
    checks.append(
        _check(
            "packages",
            "CAD and image packages",
            "missing" if missing else "ready",
            True,
            "Required Python packages were found. This check does not execute a CAD build."
            if not missing
            else "Missing app packages: " + ", ".join(missing) + ".",
            "./scripts/setup.sh" if missing else None,
            "Install app dependencies",
        )
    )
    built = _frontend_ready(root)
    checks.append(
        _check(
            "interface",
            "Built app interface",
            "ready" if built else "missing",
            True,
            "The interface and its referenced assets are present."
            if built
            else "The built interface is missing or incomplete. Build it before starting the app.",
            "npm run build" if not built else None,
            "Build interface",
        )
    )
    if check_ai:
        checks.append(_ollama_check())
    else:
        checks.append(
            _check(
                "ollama",
                "Local AI (optional)",
                "limited",
                False,
                "Not checked in this run. Photo tracing and CAD work without AI.",
            )
        )
    if include_development:
        checks.append(_development_check())
    return {
        "ready": all(check["status"] == "ready" for check in checks if check["required"]),
        "checks": checks,
        "identity": runtime_identity(root),
    }
