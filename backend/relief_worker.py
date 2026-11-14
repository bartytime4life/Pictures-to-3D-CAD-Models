"""One bounded relief build. Run with python -m backend.relief_worker JOB_DIR."""

import json
import sys
from pathlib import Path

from .relief import ReliefError, ReliefSettings, build_relief
from .three_mf import ThreeMFError
from .tracing import TraceError

SOURCE = "source.upload"


def run(job_dir: Path) -> dict:
    settings = ReliefSettings.model_validate_json(
        (job_dir / "input.json").read_text(encoding="utf-8")
    )
    source = job_dir / SOURCE
    try:
        data = source.read_bytes()
    finally:
        # The photograph is needed only to compute the thickness map; never keep it.
        source.unlink(missing_ok=True)
    result = build_relief(data, settings, job_dir)
    (job_dir / "result.json").write_text(json.dumps(result, allow_nan=False), encoding="utf-8")
    return result


if __name__ == "__main__":
    directory = Path(sys.argv[1]).resolve()
    try:
        run(directory)
    except Exception as exc:  # noqa: BLE001 - report every failure at the process boundary.
        (directory / SOURCE).unlink(missing_ok=True)
        (directory / "error.json").write_text(
            json.dumps(
                {
                    "error": str(exc)[:500],
                    "public": isinstance(exc, (ReliefError, TraceError, ThreeMFError)),
                }
            ),
            encoding="utf-8",
        )
        raise SystemExit(1)
