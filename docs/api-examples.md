# API examples and recovery

Start the workbench with `make start` after [setup](development.md). Its default
API origin is `http://127.0.0.1:8000` on the backend machine. Open `/docs` there
for interactive request schemas or `/openapi.json` for the generated contract.
See [architecture](architecture.md#api-overview) for the full field and limit
reference, and [project status](project-status.md) for source identity.

The service is single-user and has no account authentication. Generated IDs
identify temporary artifacts; they do not grant per-user authorization. Keep
the server's access appropriate for that scope.

The endpoint map below describes HTTP operations. The research branch also has
[private source-context](source-context.md) and [conditional blur-fitting](psf-calibration.md)
Python APIs. They have no HTTP route, saved source session or automatic geometry
update. Check [which source line you are using](project-status.md#source-and-review-state)
before importing those modules.

## Endpoint map

| Method and path | Purpose | Successful response |
| --- | --- | --- |
| `GET /api/health` | Check that the service responds | 200; status, version and workflow |
| `POST /api/trace` | Upload one supported photo as multipart form data | 200; profile, normalized image and tracing evidence |
| `POST /api/build` | Validate a reviewed profile and construct CAD | 200; ID, revision, dimensions, mesh, parts, warnings and download links |
| `GET /api/download/{job_id}/{kind}` | Download a generated artifact | 200; file |
| `DELETE /api/models/{job_id}` | Delete one temporary model and its exports | 204; no response body |
| `DELETE /api/models` | Clear all completed models on this instance | 200; `{"deleted": N}`; blocked during a build |
| `GET /api/printers` | Read the bundled printer catalog | 200; catalog and provenance |
| `GET /api/slicers` | Inspect configured executable discovery | 200; availability and launch configuration |
| `POST /api/models/{job_id}/slicer/{program_id}` | Explicitly request configured local GUI opening | 202; `launch_requested`, subject to local launch checks |
| `GET /api/assistant/status` | Inspect the optional local model service | 200; includes `running: false` when unavailable |
| `POST /api/assistant/chat` | Ask for bounded text guidance | 200; answer, optional proposal, warnings and duration |

The static frontend and allowlisted companion-library routes are described in
[architecture](architecture.md#published-companion-library). Slicer opening and
AI requests require their separate [slicer](slicers.md) and [AI](ollama.md) setup.

## Build a synthetic rectangle

This example uses a deliberately specified 80 × 40 pixel rectangle, a 40 mm
source width and 3 mm thickness. At the default design scales it produces a
40 × 20 × 3 mm digital solid with volume 2400 mm³. It makes no photo-measurement
or fabrication claim and requires neither a photograph nor an AI service.

Run from the repository root with the server already running. The output folder
must not exist; choose another folder before repeating. Set `PICAD_BASE_URL`
only when deliberately selecting another server. The example uses Python's
standard library, reads the server-provided STEP link and deletes only its own
temporary model in `finally`. Downloaded copies remain in the output folder.

```bash
.venv/bin/python - <<'PY'
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

base = os.environ.get("PICAD_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
output = Path(".local/api-example")
output.mkdir(parents=True, exist_ok=False)
payload = {
    "profile": {"outer": [[0, 0], [80, 0], [80, 40], [0, 40]], "holes": []},
    "width_mm": 40,
    "thickness_mm": 3,
    "name": "Synthetic documentation rectangle",
    "revision": "docs-example-v1",
}

def call(path, *, method="GET", data=None):
    body = None if data is None else json.dumps(data).encode("utf-8")
    headers = {} if body is None else {"Content-Type": "application/json"}
    request = Request(base + path, data=body, headers=headers, method=method)
    with urlopen(request, timeout=90) as response:
        return response.read()

model_id = None
try:
    health = json.loads(call("/api/health"))
    assert health["status"] == "ok"
    result = json.loads(call("/api/build", method="POST", data=payload))
    model_id = result["id"]
    assert result["revision"] == payload["revision"]
    for key, expected in {"width": 40, "height": 20, "thickness": 3}.items():
        assert abs(result["dimensions"][key] - expected) < 1e-6
    assert abs(result["volume_mm3"] - 2400) < 1e-6
    step = call(result["downloads"]["step"])
    assert step.startswith(b"ISO-10303-21;")
    (output / "model.step").write_bytes(step)
    (output / "request.json").write_text(json.dumps(payload, indent=2) + "\n")
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("PASS: 40 x 20 x 3 mm synthetic solid; STEP saved to", output)
finally:
    if model_id is not None:
        call("/api/models/" + model_id, method="DELETE")
PY
```

The saved `result.json` is a record of this response. Its download links stop
working after the example deletes its model. Keep `request.json` to rebuild the
same synthetic profile. A production client should preserve its reviewed
inputs, distinguish old results from the current revision and inspect warnings.

For an actual photo-to-STEP check using the bundled sample, run `make smoke`
against the running app (`PICAD_BASE_URL` selects an explicitly managed server).
It traces the sample, builds with demonstration dimensions and deletes its own
model after checking the download.

## Tracing and coordinates

`POST /api/trace` requires a multipart `file` field. Use `reference=none` for
ordinary tracing, or explicitly select `a4`, `letter` or `custom`. A custom sheet
also needs measured `sheet_width_mm` and `sheet_height_mm`. Send `fallback=true`
only when you intend to accept ordinary tracing with a warning for eligible
sheet-finding/use failures. Other validation and final-profile failures still
refuse the request. Review whether the returned profile actually has reference
evidence.

Ordinary tracing uses `threshold=-1` for automatic selection or an integer
cutoff from 0 through 255. Reference-sheet tracing selects its own threshold;
the submitted cutoff applies if an eligible failure takes the explicitly
enabled ordinary fallback. `snap` applies to the reference-sheet fitting path.

`profile.outer`, `profile.holes` and optional primitives use the normalized or
rectified working-image pixel frame, with Y down. Build width and thickness are
millimeters. The worker centers the outline and flips Y into CAD's XY frame.
Keep the polygon rings, primitives and reference evidence in the same frame;
do not mix pixel and millimeter coordinates within a profile. See
[geometry conventions](architecture.md#geometry-conventions).

An API arc has `kind: "arc"` and `start`, `mid`, `end` coordinate pairs; those
three points define its circle and sweep. It has no separate centre/radius
fields. Build validation checks that supplied boundary and its polygon, rather
than the internal fit that preceded trace correction. The trace path now checks
[circle-consistent final assembly](architecture.md#circle-consistent-final-assembly)
before returning fitted arcs. Unresolved joins recover per boundary as traced
polylines, with warnings and reference notes; other boundaries may remain
analytic. This changes neither the arc schema nor the meaning of the build
API's separate primitive/polygon validation.

If the recovered outline cannot form a valid profile, tracing returns 422 with
a recovery message. This is not a sheet-finding failure and is not converted
to ordinary tracing by `fallback=true`. Correct the capture or explicitly choose
ordinary tracing; do not treat an initial eligibility proxy as an exported arc.

The browser's saved project recipe is not a `/api/build` request: it can contain
format-version and browser-only calibration/height fields that the strict API
does not accept. Use the documented build schema. Backend handoff recipes omit
those browser-only notes; see [recipe contents](exports.md).

## Python example: fit a declared straight source edge

Run this from the repository root with `.venv/bin/python` on the PR #79 research
line. It creates exact synthetic point-sample means, supplies independent unit
noise and fits offset, width and both levels. It needs no server or photograph.

```python
import json
import math
from dataclasses import asdict

import numpy as np
from backend.edge_spread import fit_edge_spread
from backend.profile_observations import PixelNoise

pixels = np.array([(x, y) for x in range(8, 25) for y in (14, 17, 20)])
normal = np.array([0.8, 0.6])
anchor = np.array([16.3, 16.7])
distance = (pixels + 0.5 - anchor) @ normal
probability = np.array([
    0.5 * math.erfc(-(float(d) - 0.237) / (math.sqrt(2) * 1.37))
    for d in distance
])
values = 31.0 * (1.0 - probability) + 207.0 * probability
noise = PixelNoise.factor(np.eye(len(pixels)), 1.0)
fit = fit_edge_spread(
    pixels, values, noise, sensor_shape=(32, 32), normal=normal, anchor=anchor,
    offset_bounds=(-1.0, 1.0), sigma_bounds=(0.7, 2.3),
)
print(json.dumps(asdict(fit), allow_nan=False))
```

The best candidate is near offset `0.237` and sigma `1.37` working-image pixels,
with fitted levels near `31` and `207`. The explicit `+0.5` constructs the
synthetic pixel-centre means; pass integer pixel indices to the fitter, which
applies its own centre convention. Do not add the shift to the indices too.

Read the whole report: `best` can be `None`, and an interior best candidate does
not settle ties, unfinished basins, local rank or the noise/optical assumptions.
Python `None` serializes as JSON `null`; it is not zero. Pooling several edge
fits requires the [all-edge readiness checks](psf-calibration.md#pool-fitted-edges-without-dropping-unresolved-attempts).
The supplied unit noise is an example assumption, not a measured uncertainty.
Successful synthetic recovery does not calibrate a physical camera.

## Errors and recovery

Handled input and operation refusals use a JSON `detail` string, for example
`{"detail":"Model not found. Rebuild it to create new exports."}`. Validation
messages include the field path, with at most three validation errors combined.
Clients must also handle transport errors and non-JSON responses from a host or
proxy; inspect the status before parsing a body. A 204 deletion has no JSON body.

| Status | Common cause | Recovery |
| --- | --- | --- |
| 403 | Local slicer-origin/client checks fail | Use the enabled workbench on the slicer's host; follow the launch setup |
| 404 | Missing model, format or artifact | Rebuild from retained inputs; use the returned download links |
| 409 | Busy clear-all operation, unsupported/unavailable AI model or slicer configuration | Resolve the stated cause; preserve the current inputs |
| 410 | Model was found but had expired | Rebuild; after cleanup the same ID can instead return 404 |
| 413 | Upload or body exceeds its limit | Reduce the encoded payload; image dimensions have separate checks |
| 422 | Invalid request, unreadable photo, weak trace or unusable geometry | Correct the named field or capture; do not retry unchanged input indefinitely |
| 429 | Trace/build/chat busy, storage full or slicer cooldown | Wait or clear reviewed completed exports; honor `Retry-After` when supplied |
| 502 / 503 | Unusable or unavailable local AI service | Check the local model service; regular CAD remains available |
| 504 | CAD or AI timeout | Reduce complexity or review the local model resource settings |

CAD and trace busy responses include `Retry-After: 3`; full model storage uses
`Retry-After: 60`. Other 429 responses need not include that header. Downloads
expire after one hour and may be released sooner by the browser. Clear-all is a
global operation; it is not appropriate for cleaning up a single example.

Requests that succeed can still contain warnings or unknown geometric fit.
Treat a successful trace/build, `launch_requested`, and an AI schema-valid
answer according to their separate meanings in [validation](validation.md),
[print planning](print-planning.md) and [data handling](privacy-security.md).
