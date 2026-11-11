"""Reference-sheet tracing, fitted geometry and exact exports, against rendered ground truth.

Photos come from tests/synthetic.py: a 120 x 70 mm plate (R8 corners, 4 x D6 holes, a
D22 bore, a 24 x 8 slot) on an A4 sheet, photographed by a 2400 x 1800 pinhole camera
with radial distortion, uneven light, a soft shadow, blur, noise and JPEG compression.
Coverage is exact, so these are measurement-error tests, not snapshot tests. The
thresholds are regression guards at this resolution (about 0.2 mm per photo pixel); a
synthetic pass is not a real-world accuracy claim.
"""

import collections
import io
import json
import math

import cv2
import ezdxf
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend import app as api
from backend import edges, fitting, sheet
from backend.models import Profile
from tests import synthetic as S

CASES = {
    "overhead": {"tilt": (0.0, 0.0, 4.0), "k1": 0.0, "shadow": 0.0, "gradient": 0.0},
    "tilted": {},
    "tilted-thick": {"thickness": 4.0},
    "moderate-thick": {"tilt": (9.0, -4.0, 4.0), "thickness": 4.0},
    "frontal-thick-exif": {"tilt": (0.0, 0.0, 4.0), "thickness": 4.0, "exif_focal_35mm": 29},
    "frontal-thick": {"tilt": (0.0, 0.0, 4.0), "thickness": 4.0},
    "light-part-dark-sheet": {"tones": (200.0, 45.0, 215.0, 185.0), "shadow": 0.0},
}
# Maximum absolute errors (mm) a passing trace must stay within.
LIMITS = {"small": 0.03, "bore": 0.05, "slot": 0.06, "position": 0.05, "outer": 0.05}


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    api.JOB_ROOT = tmp_path_factory.mktemp("sheet-jobs")
    with TestClient(api.app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def photos():
    cache = {}

    def get(name):
        if name not in cache:
            cache[name] = S.render(**CASES[name])
        return cache[name]

    return get


def trace(client, data, **fields):
    form = {k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in fields.items()}
    return client.post("/api/trace", files={"file": ("photo.jpg", data, "image/jpeg")}, data=form)


def traced(client, photos, name, **fields):
    data, truth = photos(name)
    response = trace(client, data, reference="a4", **fields)
    assert response.status_code == 200, response.text
    return response.json(), truth


def within_limits(errors):
    return {k: round(v, 4) for k, v in errors.items() if v > LIMITS[k]}


@pytest.mark.parametrize("name", ["overhead", "tilted"])
def test_sheet_trace_is_metric_fitted_and_within_limits(client, photos, name):
    result, truth = traced(client, photos, name)
    profile = result["profile"]
    assert within_limits(S.feature_errors(profile)) == {}
    reference = profile["reference"]
    assert reference["kind"] == "a4" and reference["sheet_mm"] == [210.0, 297.0]
    assert abs(reference["lens_k1"] - truth["k1"]) < 0.004
    kinds = [[s["kind"] for s in ring] for ring in profile["primitives"]["holes"]]
    assert sorted(map(tuple, kinds)) == sorted(
        [("circle",)] * 5 + [("line", "arc", "line", "arc")]
    ) or sorted(map(tuple, kinds)) == sorted([("circle",)] * 5 + [("arc", "line", "arc", "line")])
    outer = collections.Counter(s["kind"] for s in profile["primitives"]["outer"])
    assert outer == {"line": 4, "arc": 4}
    # Every profile point lies inside the returned display image.
    w, h = result["image"]["width"], result["image"]["height"]
    for ring in [profile["outer"], *profile["holes"]]:
        assert all(0 <= x <= w and 0 <= y <= h for x, y in ring)
    assert any("Scaled from the A4 sheet" in w for w in result["warnings"])


def test_full_frame_photo_needs_a_crop_without_a_sheet_reference(client, photos):
    data, _ = photos("tilted")
    response = trace(client, data)
    assert response.status_code == 422
    assert "touches the image edge" in response.json()["detail"]


def test_thickness_correction_removes_side_wall_parallax(client, photos):
    data, truth = photos("tilted-thick")
    plain = trace(client, data, reference="a4").json()["profile"]
    circles = sum(
        len(ring) == 1 and ring[0]["kind"] == "circle" for ring in plain["primitives"]["holes"]
    )
    outer = np.array(plain["outer"]) * plain["reference"]["mm_per_px"]
    (_, _), (rw, rh), _ = cv2.minAreaRect(outer.astype(np.float32))
    # Uncorrected: visible walls widen the outline and turn round holes into lenses.
    assert circles < 5 or max(abs(max(rw, rh) - 120), abs(min(rw, rh) - 70)) > 0.4
    result, _ = traced(client, photos, "tilted-thick", thickness_mm=4)
    profile = result["profile"]
    assert within_limits(S.feature_errors(profile)) == {}
    reference = profile["reference"]
    assert reference["thickness_mm"] == 4 and reference["focal_source"] == "sheet"
    true_height = abs(truth["camera_centre_mm"][2])
    assert abs(reference["camera_height_mm"] - true_height) < 0.01 * true_height


def narrow_wall_bound(reference):
    """Analytic bound (edges.two_step_refine): when the visible walls are too narrow to
    measure their tone, an edge facing the camera may read up to 0.2 sigma into the part."""
    assert any("Side walls are visible but narrower" in note for note in reference["notes"])
    return 0.2 * reference["edge_blur_mm"]


def test_moderate_tilt_measures_the_wall_tone_and_refines_narrow_wall_bands(client, photos):
    """At 9 degrees the walls span 0-4 sigma: their tone is measured where wide and the
    narrow bands are refined with the two-step model (without it, D6 errors were 0.039 mm
    and the slot 0.060 mm in the same photo)."""
    result, _ = traced(client, photos, "moderate-thick", thickness_mm=4)
    reference = result["profile"]["reference"]
    assert not any("Side walls are visible but narrower" in note for note in reference["notes"])
    assert within_limits(S.feature_errors(result["profile"])) == {}


def test_frontal_photo_uses_exif_focal_length_for_thickness(client, photos):
    result, truth = traced(client, photos, "frontal-thick-exif", thickness_mm=4)
    reference = result["profile"]["reference"]
    assert reference["focal_source"] == "exif"
    assert abs(reference["camera_height_mm"] - abs(truth["camera_centre_mm"][2])) < 10
    bound = narrow_wall_bound(reference)
    errors = S.feature_errors(result["profile"])
    assert {k: v for k, v in errors.items() if v > LIMITS[k] + bound} == {}


def test_frontal_photo_without_exif_assumes_a_phone_lens_and_says_so(client, photos):
    result, _ = traced(client, photos, "frontal-thick", thickness_mm=4)
    reference = result["profile"]["reference"]
    assert reference["focal_source"] == "assumed"
    assert any("typical phone lens was assumed" in note for note in reference["notes"])
    # The assumed 26 mm lens differs from the true 28.6 mm, so the camera height and the
    # thickness correction are about 9 % off: allow half as much again as the limits,
    # on top of the narrow-wall bound that also applies to this frontal view.
    bound = narrow_wall_bound(reference)
    errors = S.feature_errors(result["profile"])
    assert {k: v for k, v in errors.items() if v > 1.5 * LIMITS[k] + bound} == {}


def test_light_part_on_dark_sheet(client, photos):
    result, _ = traced(client, photos, "light-part-dark-sheet", inverted=True)
    assert within_limits(S.feature_errors(result["profile"])) == {}


def test_missing_sheet_is_explained_or_falls_back(client):
    image = Image.new("RGB", (400, 300), "white")
    from PIL import ImageDraw

    ImageDraw.Draw(image).rectangle([100, 80, 300, 220], fill="black")
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    response = trace(client, buffer.getvalue(), reference="a4")
    assert response.status_code == 422
    assert "No reference sheet was found" in response.json()["detail"]
    response = trace(client, buffer.getvalue(), reference="letter", fallback=True)
    assert response.status_code == 200
    body = response.json()
    assert "reference" not in body["profile"] and "primitives" not in body["profile"]
    assert any("traced without one" in w for w in body["warnings"])


def test_the_wrong_sheet_size_is_detected_from_its_proportions(client, photos):
    data, _ = photos("tilted")
    right = trace(client, data, reference="a4").json()
    assert any("matches the chosen sheet within 0.0" in n for n in right["profile"]["reference"]["notes"])
    wrong = trace(client, data, reference="letter").json()
    warning = next(w for w in wrong["warnings"] if "proportions in the photo differ" in w)
    assert "measured 0.707" in warning  # 210 / 297, the A4 sheet actually photographed


def hostile_images():
    """Untrusted inputs a reference-sheet trace must answer with a 422, never a 500."""
    rng = np.random.default_rng(0)
    images = {
        "blank": np.full((600, 800, 3), 255, np.uint8),
        "noise": rng.integers(0, 256, (600, 800, 3), dtype=np.uint8),
        "tiny": np.full((20, 20, 3), 128, np.uint8),
    }
    empty_sheet = np.full((600, 800, 3), 90, np.uint8)
    cv2.rectangle(empty_sheet, (200, 100), (600, 500), (240, 240, 240), -1)
    images["empty sheet"] = empty_sheet
    crossing = empty_sheet.copy()
    cv2.rectangle(crossing, (150, 250), (330, 330), (40, 40, 40), -1)  # part over the sheet edge
    images["part over the sheet edge"] = crossing
    stripes = np.zeros((600, 800, 3), np.uint8)
    stripes[:, ::7] = 255
    images["stripes"] = stripes
    return images


@pytest.mark.parametrize("name", list(hostile_images()))
def test_reference_trace_failures_are_recoverable(client, name):
    _, data = cv2.imencode(".png", hostile_images()[name])
    response = trace(client, data.tobytes(), reference="a4", thickness_mm=3)
    assert response.status_code == 422, response.text
    assert response.json()["detail"]


def test_custom_sheet_needs_both_sides(client, photos):
    data, _ = photos("overhead")
    response = trace(client, data, reference="custom", sheet_width_mm=210)
    assert response.status_code == 422
    response = trace(client, data, reference="custom", sheet_width_mm=210, sheet_height_mm=297)
    assert response.status_code == 200
    assert response.json()["profile"]["reference"]["kind"] == "custom"


def test_snapping_can_be_turned_off(client, photos):
    data, _ = photos("tilted")
    snapped = trace(client, data, reference="a4").json()["profile"]["reference"]["notes"]
    plain = trace(client, data, reference="a4", snap=False).json()["profile"]["reference"]["notes"]
    assert any("made exactly parallel" in n for n in snapped)
    assert any("Rotated" in n for n in snapped)
    assert not any("made exactly parallel" in n or "Rotated" in n for n in plain)


@pytest.fixture(scope="module")
def fitted_build(client, photos):
    result, _ = traced(client, photos, "tilted-thick", thickness_mm=4)
    profile = result["profile"]
    width = result["bounds"]["width"] * profile["reference"]["mm_per_px"]
    response = client.post(
        "/api/build",
        json={"profile": profile, "width_mm": width, "thickness_mm": 4, "name": "Plate", "design": {}},
    )
    assert response.status_code == 200, response.text
    return profile, response.json()


def test_fitted_build_is_aligned_exact_and_reports_its_geometry(fitted_build):
    _, model = fitted_build
    assert model["geometry"] == {"kind": "fitted", "lines": 6, "arcs": 6, "circles": 5}
    assert abs(model["dimensions"]["width"] - 120) < LIMITS["outer"]
    assert abs(model["dimensions"]["height"] - 70) < LIMITS["outer"]
    assert model["hole_count"] == 6
    assert math.isclose(model["volume_mm3"], S.part_local().area * 4, rel_tol=0.005)


def test_fitted_exports_carry_true_circles_and_arcs(client, fitted_build, tmp_path):
    _, model = fitted_build
    step = client.get(model["downloads"]["step"]).text
    assert step.count("CYLINDRICAL_SURFACE") == 11  # 5 holes, 4 corners, 2 slot ends
    dxf_path = tmp_path / "profile.dxf"
    dxf_path.write_bytes(client.get(model["downloads"]["dxf"]).content)
    drawing = ezdxf.readfile(dxf_path)
    assert drawing.units == ezdxf.units.MM
    counts = collections.Counter(e.dxftype() for e in drawing.modelspace())
    assert counts == {"LINE": 6, "ARC": 6, "CIRCLE": 5}
    radii = sorted(round(e.dxf.radius, 2) for e in drawing.modelspace() if e.dxftype() == "CIRCLE")
    assert radii[:4] == [radii[0]] * 4 and abs(radii[0] - 3.0) < LIMITS["small"]
    scad = client.get(model["downloads"]["scad"]).text
    assert scad.count("circle(r =") == 5 and "polygon(points" in scad
    stl = client.get(model["downloads"]["stl"]).content
    assert len(stl) > 84


def test_fitted_recipe_is_version_3_and_restores(client, fitted_build):
    profile, model = fitted_build
    recipe = client.get(model["downloads"]["project"]).json()
    assert recipe["version"] == 3
    assert recipe["profile"]["primitives"] == profile["primitives"]
    assert recipe["profile"]["reference"]["thickness_mm"] == 4
    assert "rectified on a reference sheet" in recipe["provenance"]
    assert "scale from the sheet" in recipe["provenance"]
    rebuilt = client.post(
        "/api/build",
        json={k: recipe[k] for k in ("profile", "width_mm", "thickness_mm", "name", "design")},
    )
    assert rebuilt.status_code == 200
    assert rebuilt.json()["geometry"] == model["geometry"]


def test_split_output_falls_back_to_the_traced_polygon(client, fitted_build):
    profile, model = fitted_build
    response = client.post(
        "/api/build",
        json={
            "profile": profile,
            "width_mm": model["dimensions"]["width"],
            "thickness_mm": 4,
            "design": {"output_mode": "split", "split_columns": 2},
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["geometry"] == {"kind": "polygon"}
    assert any("Exact arcs and circles are exported only for single-piece" in w for w in body["warnings"])


def disc_profile(radius_px=100.0):
    outer = [
        (radius_px + radius_px * math.cos(2 * math.pi * k / 200), radius_px + radius_px * math.sin(2 * math.pi * k / 200))
        for k in range(200)
    ]
    circle = {"kind": "circle", "center": [radius_px, radius_px], "radius": radius_px}
    return {"outer": outer, "primitives": {"outer": [circle]}}


@pytest.mark.parametrize("diameter_mm", [2, 20, 60])
def test_small_fitted_discs_pass_the_solid_check(client, diameter_mm):
    # The sampled check polygon is inscribed, so its area falls short by about
    # (4/3) * sagitta / radius: more than a fixed 1e-4 for radii under ~13 mm.
    response = client.post(
        "/api/build",
        json={"profile": disc_profile(), "width_mm": diameter_mm, "thickness_mm": 3, "design": {}},
    )
    assert response.status_code == 200, response.text
    assert response.json()["geometry"] == {"kind": "fitted", "lines": 0, "arcs": 0, "circles": 1}


def test_fitted_recipe_without_design_still_carries_design_settings(client):
    response = client.post("/api/build", json={"profile": disc_profile(), "width_mm": 40, "thickness_mm": 3})
    assert response.status_code == 200, response.text
    recipe = client.get(response.json()["downloads"]["project"]).json()
    assert recipe["version"] == 3
    assert isinstance(recipe["design"], dict) and recipe["design"]
    rebuilt = client.post(
        "/api/build", json={k: recipe[k] for k in ("profile", "width_mm", "thickness_mm", "design")}
    )
    assert rebuilt.status_code == 200, rebuilt.text


def _mutated(profile, change):
    copy = json.loads(json.dumps(profile))
    change(copy)
    return copy


@pytest.mark.parametrize(
    "change",
    [
        pytest.param(lambda p: p["primitives"]["outer"][0].update(end=[0.0, 0.0]), id="open-ring"),
        pytest.param(
            lambda p: next(r for r in p["primitives"]["holes"] if r[0]["kind"] == "circle")[0].update(
                radius=next(r for r in p["primitives"]["holes"] if r[0]["kind"] == "circle")[0]["radius"] * 1.3
            ),
            id="circle-not-the-traced-hole",
        ),
        pytest.param(lambda p: p["primitives"]["holes"].pop(), id="hole-count"),
        pytest.param(
            lambda p: p["primitives"]["outer"].append({"kind": "circle", "center": [1, 1], "radius": 1}),
            id="circle-mixed-into-a-ring",
        ),
        pytest.param(lambda p: p["primitives"]["outer"][0].update(kind="spline"), id="unknown-kind"),
        pytest.param(lambda p: p["reference"].update(mm_per_px=-1), id="bad-reference"),
        pytest.param(lambda p: p["primitives"].update(extra=1), id="extra-field"),
    ],
)
def test_invalid_fitted_geometry_is_rejected(client, fitted_build, change):
    profile, model = fitted_build
    response = client.post(
        "/api/build",
        json={
            "profile": _mutated(profile, change),
            "width_mm": model["dimensions"]["width"],
            "thickness_mm": 4,
        },
    )
    assert response.status_code == 422


def test_nonfinite_primitive_values_are_rejected(client, fitted_build):
    profile, model = fitted_build
    body = json.dumps(
        {"profile": profile, "width_mm": model["dimensions"]["width"], "thickness_mm": 4}
    ).replace(f'"radius": {profile["primitives"]["holes"][0][0].get("radius", 1)}', '"radius": NaN', 1)
    response = client.post(
        "/api/build", content=body, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422


# ----------------------------------------------------------------------- unit checks


def disc_image(radius, sigma, size=None):
    from shapely.geometry import Point, Polygon, box

    w = size or int(2 * radius + 60)
    material = Polygon(
        box(12, 12, w - 12, w - 12).exterior, [Point(w / 2 + 0.3, w / 2 - 0.2).buffer(radius, 1024).exterior]
    )
    image = (236 - 188 * S.coverage(material, 1.0, 0.5, 0.5, (w, w))).astype(np.float32)
    return cv2.GaussianBlur(image, (0, 0), sigma) if sigma else image, (w / 2 + 0.3, w / 2 - 0.2)


@pytest.mark.parametrize("radius,sigma", [(30, 1.0), (30, 1.95), (110, 1.95)])
def test_half_level_edges_and_blur_correction_are_unbiased(radius, sigma):
    image, centre = disc_image(radius, sigma)
    rings, measured_sigma, _ = edges.subpixel_rings((image < 142).astype(np.uint8), image, 1.0)
    hole = next(r for r in rings if not r["outer"])["points"]
    cx, cy, r, _, _ = fitting.fit_circle(hole)
    corrected = fitting.blur_corrected_radius(r, measured_sigma)
    assert abs(measured_sigma - sigma) < 0.08
    assert abs(corrected - radius) < 0.01
    assert math.hypot(cx - centre[0], cy - centre[1]) < 0.01


def test_rounded_rectangle_fits_four_lines_and_tangent_arcs():
    import shapely
    from shapely.geometry import box

    shape = box(-50, -30, 50, 30).buffer(-8).buffer(8, 128)
    # Uniform spacing and edge noise, like a traced sub-pixel ring.
    ring = np.asarray(shapely.segmentize(shape.exterior, 0.5).coords)[:-1]
    ring = ring + np.random.default_rng(1).normal(0, 0.05, ring.shape)
    prims = fitting.fit_ring(ring, 0.15, 5.0)
    assert [p.kind for p in prims].count("line") == 4
    notes, axis = fitting.snap_axes([prims])
    fitting.refit_lines(ring, prims)
    fitting.fit_fillets(ring, prims, 0.15)
    notes += fitting.equalise_radii([prims])
    radii = [p.data["r"] for p in prims if p.kind == "arc"]
    assert len(radii) == 4 and all(abs(r - 8) < 0.05 for r in radii)
    assert abs(axis) < math.radians(0.1)
    polygon = np.array(fitting.sample_segments(fitting.segments(prims), 0.001))
    from shapely.geometry import Polygon

    assert abs(Polygon(polygon).area - shape.area) / shape.area < 1e-3


def test_camera_pose_recovers_a_known_camera():
    k, rotation, t = S.camera((18.0, -7.0, 3.0))
    matrix = k @ np.column_stack([rotation[:, 0], rotation[:, 1], t])
    pose = sheet.camera_pose(matrix / matrix[2, 2], (2400, 1800))
    centre = -rotation.T @ t
    assert pose["focal_source"] == "sheet"
    assert abs(pose["focal_px"] - k[0, 0]) < 1e-6 * k[0, 0]
    assert np.allclose(pose["centre_mm"], centre, atol=1e-6)


def test_thickness_correction_is_a_homothety_about_the_nadir():
    points = np.array([[100.0, 0.0], [0.0, 100.0], [-100.0, 0.0]])
    normals = np.array([[1.0, 0.0], [0.0, -1.0], [1.0, 0.0]])  # away, toward, toward
    corrected, top = edges.correct_thickness(points, normals, np.zeros(2), 400.0, 4.0)
    assert top.tolist() == [True, False, False]
    assert np.allclose(corrected[0], [99.0, 0.0]) and np.allclose(corrected[1:], points[1:])


def test_profile_without_fitted_geometry_is_unchanged():
    profile = Profile(outer=[(0, 0), (10, 0), (10, 5), (0, 5)])
    assert profile.model_dump(exclude_none=True) == {"outer": [(0, 0), (10, 0), (10, 5), (0, 5)], "holes": []}
