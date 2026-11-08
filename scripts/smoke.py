"""Check the running app using its real sample, CAD worker, and STEP download."""

import os
from pathlib import Path

import httpx


def main():
    root = Path(__file__).resolve().parent.parent
    base_url = os.environ.get("PICAD_BASE_URL", "http://127.0.0.1:8000")
    model_id = None
    with httpx.Client(base_url=base_url, timeout=90) as client:
        try:
            health = client.get("/api/health").raise_for_status().json()
            assert health["status"] == "ok"
            assert "Pictures to CAD" in client.get("/").raise_for_status().text
            traced = (
                client.post(
                    "/api/trace",
                    files={
                        "file": (
                            "sample.png",
                            (root / "frontend/public/sample.png").read_bytes(),
                            "image/png",
                        )
                    },
                )
                .raise_for_status()
                .json()
            )
            assert len(traced["profile"]["holes"]) == 3
            model = (
                client.post(
                    "/api/build",
                    json={
                        "profile": traced["profile"],
                        "width_mm": 80,
                        "thickness_mm": 4,
                        "name": "Startup check",
                        "revision": "smoke",
                    },
                )
                .raise_for_status()
                .json()
            )
            model_id = model["id"]
            assert model["hole_count"] == 3
            assert abs(model["dimensions"]["width"] - 80) < 1e-6
            assert abs(model["dimensions"]["thickness"] - 4) < 1e-6
            assert model["volume_mm3"] > 0
            step = client.get(model["downloads"]["step"]).raise_for_status().content
            assert step.startswith(b"ISO-10303-21;")
            print(
                "PASS: served interface, traced sample with 3 openings, built 80 mm × 4 mm solid, downloaded STEP."
            )
        finally:
            if model_id:
                client.delete(f"/api/models/{model_id}").raise_for_status()


if __name__ == "__main__":
    main()
