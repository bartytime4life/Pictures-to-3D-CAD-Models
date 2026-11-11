"""Reference-sheet tracing, fitted geometry and exact exports, against rendered ground truth.

Photos come from tests/synthetic.py: a 120 x 70 mm plate (R8 corners, 4 x D6 holes, a
D22 bore, a 24 x 8 slot) on an A4 sheet, photographed by a 2400 x 1800 pinhole camera
with radial distortion, uneven light, a soft shadow, blur, noise and JPEG compression.
Light is mixed and blurred in linear light and saved through the sRGB tone curve.
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
from tests import readers
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


@pytest.mark.parametrize(("name", "corner"), [("overhead", 20.0), ("tilted", 25.0)])
def test_large_corner_radii_trace_as_arcs(client, monkeypatch, name, corner):
    """The test plate with R20 or R25 corners in place of R8. The breakpoint chords of
    so large an arc are over 3 mm long and pass the line test. Without the chord test
    in fitting.fit_ring the outline comes back as a polyline of 67 (overhead) or 77
    (tilted) straight segments instead of four lines and four arcs."""
    monkeypatch.setitem(S.PART, "corner", corner)
    data, _ = S.render(**CASES[name])
    response = trace(client, data, reference="a4")
    assert response.status_code == 200, response.text
    profile = response.json()["profile"]
    outer = profile["primitives"]["outer"]
    assert collections.Counter(s["kind"] for s in outer) == {"line": 4, "arc": 4}
    mm = profile["reference"]["mm_per_px"]
    radii = [
        fitting.arc_geometry(s["start"], s["mid"], s["end"])[1] * mm for s in outer if s["kind"] == "arc"
    ]
    assert max(abs(r - corner) for r in radii) < LIMITS["outer"]
    assert within_limits(S.feature_errors(profile)) == {}


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
    narrow bands are refined with the two-step model. Without a shadow that takes this
    photo's D22 error from 0.014 to 0.002 mm and its slot from 0.040 to 0.017 mm; with
    the 25 % shadow used here, the shadow's opposite bias hides the gain
    (docs/reference-sheet.md)."""
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


def test_without_a_shadow_the_tilted_trace_is_several_times_tighter(client):
    """Tone curve, lens, perspective, blur, noise and JPEG together leave under 0.02 mm
    (0.03 mm on position). The rest of the tilted photo's error is its shadow."""
    data, _ = S.render(shadow=0.0)
    response = trace(client, data, reference="a4")
    assert response.status_code == 200, response.text
    tight = {"small": 0.01, "bore": 0.015, "slot": 0.02, "position": 0.03, "outer": 0.015}
    errors = S.feature_errors(response.json()["profile"])
    assert {k: v for k, v in errors.items() if v > tight[k]} == {}


def test_a_deep_shadow_biases_edges_by_a_bounded_amount(client):
    """Known sensitivity, not a target. A soft shadow slopes the paper's brightness
    next to an edge, and the mid-level then sits too far out. The error grows with the
    shadow's depth: this one removes 47 % of the light (25 % darker in the saved photo)
    and roughly doubles the errors of the usual 25 % shadow."""
    data, _ = S.render(shadow=0.47)
    response = trace(client, data, reference="a4")
    assert response.status_code == 200, response.text
    bound = {"small": 0.04, "bore": 0.07, "slot": 0.08, "position": 0.05, "outer": 0.07}
    errors = S.feature_errors(response.json()["profile"])
    assert {k: v for k, v in errors.items() if v > bound[k]} == {}
    assert errors["bore"] > LIMITS["bore"]  # tighten the bounds when this is improved


def test_a_camera_saving_with_a_plain_gamma_stays_within_limits(client):
    """The tracer decodes photos as sRGB. A camera that saves with a plain 2.2 gamma
    differs slightly from that curve and costs about 0.01-0.02 mm."""
    data, _ = S.render(gamma=2.2, **CASES["overhead"])
    response = trace(client, data, reference="a4")
    assert response.status_code == 200, response.text
    assert within_limits(S.feature_errors(response.json()["profile"])) == {}


@pytest.mark.parametrize(
    "table,paper,part,mixed",
    [
        pytest.param((60, 60, 60), (220, 220, 220), (40, 40, 40), False, id="grey-part"),
        # Pure green and this grey have the same luminance but 70 grey levels between them
        # in the saved photo, on which the part is found.
        pytest.param((120, 120, 120), (220, 220, 220), (0, 255, 0), True, id="green-part"),
        pytest.param((0, 255, 0), (220, 220, 220), (40, 40, 40), False, id="green-table"),
    ],
)
def test_parts_and_sheets_that_differ_in_colour_are_measured_on_the_channels_that_differ(
    client, table, paper, part, mixed
):
    """A part the tracer can find must also be measurable. Luminance alone loses the
    green part's boundary and the sheet's edge on the green table."""
    response = trace(client, S.colour_photo(table, paper, part), reference="a4")
    assert response.status_code == 200, response.text
    profile = response.json()["profile"]
    scale = profile["reference"]["mm_per_px"]
    (outer,), ((hole,),) = profile["primitives"]["outer"], profile["primitives"]["holes"]
    assert outer["kind"] == hole["kind"] == "circle"
    assert abs(2 * outer["radius"] * scale - 60) < 0.01
    assert abs(2 * hole["radius"] * scale - 16) < 0.01
    assert any("colour mix" in note for note in profile["reference"]["notes"]) == mixed


def test_a_photo_above_16_megapixels_is_reduced_in_linear_light_and_stays_accurate(client):
    data = S.colour_photo((60, 60, 60), (220, 220, 220), (40, 40, 40), ppm=13.0)
    response = trace(client, data, reference="a4")
    assert response.status_code == 200, response.text
    body = response.json()
    assert any("18-megapixel photo was reduced" in warning for warning in body["warnings"])
    scale = body["profile"]["reference"]["mm_per_px"]
    (outer,), ((hole,),) = body["profile"]["primitives"]["outer"], body["profile"]["primitives"]["holes"]
    assert abs(2 * outer["radius"] * scale - 60) < 0.01
    assert abs(2 * hole["radius"] * scale - 16) < 0.01


def test_a_two_colour_part_keeps_the_boundary_of_its_smaller_colour(client):
    """A pale pink plate with a green patch holding a hole, on a 220 grey sheet. Both
    colours are measurable in luminance. A mix chosen from the plate's main colour is
    green alone, in which the patch equals the sheet: the plate then read 66 mm wide,
    not 80, and lost its hole, with no error."""
    data = S.two_colour_photo((120, 120, 120), (220, 220, 220), (220, 180, 220), (40, 220, 40))
    response = trace(client, data, reference="a4")
    assert response.status_code == 200, response.text
    profile = response.json()["profile"]
    scale = profile["reference"]["mm_per_px"]
    (_, _), (width, height), _ = cv2.minAreaRect(
        (np.array(profile["outer"]) * scale).astype(np.float32)
    )
    assert abs(max(width, height) - 80) < 0.03 and abs(min(width, height) - 50) < 0.03
    ((hole,),) = profile["primitives"]["holes"]
    assert hole["kind"] == "circle" and abs(2 * hole["radius"] * scale - 8) < 0.02
    assert not any("colour mix" in note for note in profile["reference"]["notes"])


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
    assert model["parts"][0]["bed_fit"]["basis"] == "bounding_box"
    assert model["parts"][0]["bed_fit"]["status"] == "fits"


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


def test_fitted_drawings_hold_the_solid_s_profile_with_true_arcs(client, fitted_build):
    _, model = fitted_build
    size = (model["dimensions"]["width"], model["dimensions"]["height"])
    area = model["volume_mm3"] / model["dimensions"]["thickness"]
    region, root = readers.svg_region(client.get(model["downloads"]["svg"]).text)
    # The SVG encloses the same area as the exact solid's face, at the same size.
    assert region.area == pytest.approx(area, rel=2e-5)
    x0, y0, x1, y1 = region.bounds
    assert (x1 - x0, y1 - y0) == pytest.approx(size, abs=1e-4)
    assert len(region.interiors) == 6
    outline, holes = root.findall(f"{readers.SVG}g")
    assert outline[0].get("d").count(" A ") == 4 and outline[0].get("d").count(" L ") == 4
    radii = sorted(float(c.get("r")) for c in holes.findall(f"{readers.SVG}circle"))
    assert len(radii) == 5 and radii[:4] == [radii[0]] * 4 and abs(radii[0] - 3.0) < LIMITS["small"]
    (slot,) = holes.findall(f"{readers.SVG}path")
    assert slot.get("d").count(" A ") == 4  # two half-turn ends, each written as two arcs

    page, content = readers.pdf_parts(client.get(model["downloads"]["pdf"]).content)
    assert page == pytest.approx((210.0, 279.4), abs=1e-3)
    closed, strokes, _ = readers.pdf_paths(content)
    outer, *inner = sorted((readers.Polygon(ring) for ring in closed), key=lambda p: -p.area)
    assert len(inner) == 6
    assert outer.area - sum(hole.area for hole in inner) == pytest.approx(area, rel=2e-5)
    x0, y0, x1, y1 = outer.bounds
    assert (x1 - x0, y1 - y0) == pytest.approx(size, abs=1e-4)
    assert [readers.length(s) for s in strokes if readers.length(s) > 50] == pytest.approx([100, 100])
    # Two crossing marks in each of the five round holes.
    assert sum(readers.length(s) < 6 and readers.length(s) not in (1.5, 3.0) for s in strokes) == 10


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


@pytest.mark.parametrize("radius_mm,sigma_px", [(8.0, 1.6), (4.0, 1.6), (2.5, 2.2)])
def test_blurred_fillets_keep_their_radius_when_snapped(radius_mm, sigma_px):
    """A rendered 120 x 70 mm plate with rounded corners at 5 px/mm, blurred, traced and
    fitted as backend.reference does with design-intent snapping on. Fitting the
    fillets without the blur in their model reads them about four blur shrinks large."""
    from shapely.geometry import box

    ppm = 5.0
    part = box(10, 10, 130, 80).buffer(-radius_mm).buffer(radius_mm, 1024)
    image = (236 - 188 * S.coverage(part, ppm, 0.0, 0.0, (450, 700))).astype(np.float32)
    image = cv2.GaussianBlur(image, (0, 0), sigma_px)
    rings, sigma, _ = edges.subpixel_rings((image < 142).astype(np.uint8), image, ppm)
    points = next(r for r in rings if r["outer"])["points"]
    tolerance = max(0.03, 0.15 * sigma / ppm) * ppm

    def fitted(blur):
        prims = fitting.fit_ring(points, tolerance, 3.0 * ppm)
        fitting.snap_axes([prims])
        fitting.refit_lines(points, prims)
        fitting.fit_fillets(points, prims, tolerance, blur)
        fitting.correct_blur(prims, sigma)
        radii = np.array([p.data["r"] for p in prims if p.kind == "arc"]) / ppm
        assert len(radii) == 4
        return radii - radius_mm

    shrink = (sigma / ppm) ** 2 / (2 * radius_mm)
    assert np.abs(fitted(sigma)).max() < 0.01
    assert fitted(0.0).min() > 3 * shrink > 0.02


def snapped_fit_of_rendered(part, ppm, sigma_px, size):
    """Render `part` (mm) at `ppm`, blur it, trace it and fit it as backend.reference does
    with snapping on. Returns (primitives in pixels, measured blur in pixels)."""
    image = (236 - 188 * S.coverage(part, ppm, 0.0, 0.0, size)).astype(np.float32)
    image = cv2.GaussianBlur(image, (0, 0), sigma_px)
    rings, sigma, _ = edges.subpixel_rings((image < 142).astype(np.uint8), image, ppm)
    points = next(r for r in rings if r["outer"])["points"]
    tolerance = max(0.03, 0.15 * sigma / ppm) * ppm
    extent_mm = float(np.ptp(points, axis=0).max()) / ppm
    prims = fitting.fit_ring(points, tolerance, min(max(0.025 * extent_mm, 1.0), 3.0) * ppm)
    assert prims is not None
    fitting.snap_axes([prims])
    fitting.refit_lines(points, prims, margin=3 * sigma)
    fitting.fit_fillets(points, prims, tolerance, sigma)
    fitting.correct_blur(prims, sigma)
    return prims, sigma


@pytest.mark.parametrize(
    ("sides", "turn_deg", "radius_mm"),
    [(6, 0.0, 3.0), (8, 22.5, 4.0), (8, 10.0, 4.0), (12, 0.0, 4.0)],
)
def test_wide_corner_fillets_keep_their_radius_within_the_reported_uncertainty(sides, turn_deg, radius_mm):
    """Rendered regular polygons with filleted corners of 120, 135 and 150 degrees,
    0.32 mm blur. Each fillet's radius is within twice its reported standard deviation
    and 0.12 mm. Before the exact corner model they carried no uncertainty. An octagon with
    its edges on the pixel axes and diagonals reads 0.07 mm small: the tracer places
    those edges about 0.03 px apart, which a 135 degree corner magnifies twelve times
    (fitting.EDGE_SYS_SD carries it into the reported uncertainty)."""
    from shapely.geometry import Polygon

    ppm = 5.0
    turn = math.radians(turn_deg)
    corners = [
        (70 + 45 * math.cos(turn + 2 * math.pi * k / sides), 55 + 45 * math.sin(turn + 2 * math.pi * k / sides))
        for k in range(sides)
    ]
    part = Polygon(corners).buffer(-radius_mm).buffer(radius_mm, 1024)
    prims, _ = snapped_fit_of_rendered(part, ppm, 1.6, (575, 725))
    arcs = [p for p in prims if p.kind == "arc"]
    assert len(arcs) == sides
    for p in arcs:
        error = abs(p.data["r"] / ppm - radius_mm)
        assert error < 2 * p.data["r_sd"] / ppm and error < 0.12
        assert round(p.data["corner_deg"]) == round(180 - 360 / sides)


@pytest.mark.parametrize(("radius_mm", "sigma_px"), [(4.0, 1.6), (8.0, 1.6), (3.0, 2.5)])
def test_inside_and_outside_fillets_of_an_l_shaped_plate(radius_mm, sigma_px):
    """A rendered L-shaped plate with every corner filleted, the inside one included.
    The blurred indicators of a corner and of its complement sum to one, so the traced
    edge and the exact corner model are the same for an inside fillet as for an
    outside one: all six radii read within 0.01 mm."""
    from shapely.geometry import box

    ppm = 5.0
    plate = box(10, 10, 130, 90).difference(box(60, 45, 140, 100))
    part = plate.buffer(radius_mm, 1024).buffer(-2 * radius_mm, 1024).buffer(radius_mm, 1024)
    prims, _ = snapped_fit_of_rendered(part, ppm, sigma_px, (500, 725))
    radii = np.array([p.data["r"] for p in prims if p.kind == "arc"]) / ppm
    assert len(radii) == 6 and np.abs(radii - radius_mm).max() < 0.01


@pytest.mark.parametrize(("sides", "turn", "sigma_px"), [(4, 0.0, 1.6), (4, 0.0, 2.5), (6, 0.2, 1.6), (3, 0.1, 1.6)])
def test_sharp_corners_are_traced_sharp(sides, turn, sigma_px):
    """Rendered plates with sharp corners. Blur rounds a sharp corner; on main each was
    fitted as a fillet of R0.4 to R1.1 mm. With the exact corner model the corner is
    sharp, its edges meet, and the note bounds any fillet there well under a millimetre."""
    from shapely.geometry import Polygon, box

    ppm = 5.0
    if sides == 4:
        part = box(10, 10, 130, 80)
    else:
        part = Polygon([(70 + 45 * math.cos(turn + 2 * math.pi * k / sides), 55 + 45 * math.sin(turn + 2 * math.pi * k / sides)) for k in range(sides)])
    prims, sigma = snapped_fit_of_rendered(part, ppm, sigma_px, (575, 725))
    assert [p.kind for p in prims] == ["line"] * sides
    (note,) = fitting.undetermined_radii([prims], sigma, scale=1 / ppm)
    assert note.startswith(f"{sides} corner(s) traced as sharp")
    assert max(p.data["sharp_bound"] for p in prims) / ppm < 0.5


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


def blurred_outline(part, sigma_px, ppm):
    """The outer ring traced from a rendered, blurred part (a shapely polygon in mm),
    with the measured blur and the tolerance backend.reference would fit it to. All
    three are in pixels."""
    from shapely import affinity

    x0, y0, x1, y1 = part.bounds
    part = affinity.translate(part, 10 - x0, 10 - y0)
    shape = (int((y1 - y0 + 20) * ppm), int((x1 - x0 + 20) * ppm))
    image = (236 - 188 * S.coverage(part, ppm, 0.0, 0.0, shape)).astype(np.float32)
    image = cv2.GaussianBlur(image, (0, 0), sigma_px)
    rings, sigma, _ = edges.subpixel_rings((image < 142).astype(np.uint8), image, ppm)
    points = next(r for r in rings if r["outer"])["points"]
    return points, sigma, max(0.03, 0.15 * sigma / ppm) * ppm


@pytest.mark.parametrize(
    ("radius_mm", "sigma_px", "size_mm", "min_line_mm", "ppm"),
    [
        (20.0, 1.6, (120.0, 70.0), 3.0, 5.0),
        (30.0, 1.6, (120.0, 70.0), 3.0, 5.0),
        (25.0, 1.0, (120.0, 70.0), 3.0, 5.0),
        (6.0, 2.0, (36.0, 24.0), 1.0, 10.0),
    ],
)
def test_corners_whose_chords_pass_for_lines_are_fitted_as_arcs(
    radius_mm, sigma_px, size_mm, min_line_mm, ppm
):
    """A rendered plate with rounded corners, blurred, traced and fitted as
    backend.reference does, with and without design-intent snapping. In every case the
    longest chord a breakpoint leaves on a corner, sqrt(12 R tol), is over min_line:
    R20 and R30 at a 0.34 mm blur, R25 at 0.23 mm, and R6 on a 36 mm plate, whose
    min_line is 1 mm. Every radius reads within 0.01 mm. Without the chord test in
    fit_ring none of these rings comes out as four lines and four arcs."""
    from shapely.geometry import box

    part = box(0, 0, *size_mm).buffer(-radius_mm).buffer(radius_mm, 2048)
    points, sigma, tolerance = blurred_outline(part, sigma_px, ppm)
    assert math.sqrt(12 * radius_mm * tolerance / ppm) > min_line_mm
    for snap in (False, True):
        prims = fitting.fit_ring(points, tolerance, min_line_mm * ppm)
        assert [p.kind for p in prims] == ["line", "arc"] * 4
        if snap:
            fitting.snap_axes([prims])
            fitting.refit_lines(points, prims)
            fitting.fit_fillets(points, prims, tolerance, sigma)
        fitting.correct_blur(prims, sigma)
        radii = np.array([p.data["r"] for p in prims if p.kind == "arc"]) / ppm
        assert np.abs(radii - radius_mm).max() < 0.01
        # Opposite edges are the plate's height and width apart: no edge took in a chord.
        lines = [p for p in prims if p.kind == "line"]
        apart = []
        for near, far in ((lines[0], lines[2]), (lines[1], lines[3])):
            normal = np.array([-near.data["d"][1], near.data["d"][0]])
            apart.append(abs((np.asarray(far.data["c"]) - np.asarray(near.data["c"])) @ normal) / ppm)
        assert np.abs(np.sort(apart) - sorted(size_mm)).max() < 0.01


def test_blurred_facets_are_not_taken_for_an_arc():
    """A plate with one corner turned by five 3.2 mm facets in 15 degree steps, rendered
    at 5 px/mm with a 0.34 mm blur and turned 8 degrees. The facets bow 0.10 mm from a
    circle, twice the tolerance, so all five stay lines beside the plate's four edges.
    The blur rounds the joins between facets, and those rounded joins are too short to
    define a circle for the facets next to them."""
    from shapely import affinity
    from shapely.geometry import Polygon

    step = math.radians(15)
    corner = np.cumsum([(3.2 * math.cos(k * step), -3.2 * math.sin(k * step)) for k in range(1, 6)], axis=0)
    plate = Polygon([(-60, 0), (0, 0), *map(tuple, corner), (corner[-1][0], -60), (-60, -60)])
    points, _, tolerance = blurred_outline(affinity.rotate(plate, 8, origin="centroid"), 1.6, 5.0)
    assert 3.2 * step / 8 > 2 * tolerance / 5.0
    min_line = min(max(0.025 * float(np.ptp(points, axis=0).max()), 5.0), 15.0)  # as backend.reference
    prims = fitting.fit_ring(points, tolerance, min_line)
    assert [p.kind for p in prims].count("line") == 9


@pytest.mark.parametrize(("flat_mm", "turn_deg"), [(6.0, 0), (4.0, 0), (10.0, 0), (6.0, 2), (4.0, 5), (10.0, 45)])
def test_a_stub_cut_off_a_straight_edge_is_fitted_as_part_of_it(flat_mm, turn_deg):
    """A plate with four sharp corners whose top edge runs into an R30 arc of 60 degrees
    and then a short flat, rendered at 5 px/mm with a 0.23 mm blur and fitted as
    backend.reference does, with and without design-intent snapping. In each case a
    breakpoint falls on a straight edge 1.8 to 2.4 mm from a sharp corner, within
    min_line, and the stub it cuts off is too short to be a line. Fitted as one arc with
    the corner's blur-rounded join, the stub left the whole outline a polyline. As part
    of its edge it leaves five lines and five arcs. The R30 arc reads within 0.03 mm.
    Each right-angle corner is rounded by the blur alone, to under 0.6 mm, where the
    stub and the corner together had been an arc of 1.3 to 3.2 mm; with snapping, the
    exact corner model traces it sharp, with a bound under 0.6 mm on any fillet there.
    The outline encloses the plate's area within 0.03 %."""
    from shapely import affinity
    from shapely.geometry import Polygon

    ppm, radius = 5.0, 30.0
    angles = np.linspace(math.pi / 2, math.pi / 6, 600)
    arc = [(70 + radius * math.cos(t), 80 - radius + radius * math.sin(t)) for t in angles]
    # The flat runs on from the end of the arc, tangent to it, to the right-hand edge.
    corner = (arc[-1][0] + flat_mm * math.sin(angles[-1]), arc[-1][1] - flat_mm * math.cos(angles[-1]))
    plate = Polygon([(0, 0), (corner[0], 0), corner, *arc[::-1], (0, 80)])
    points, sigma, tolerance = blurred_outline(affinity.rotate(plate, turn_deg, origin="centroid"), 1.0, ppm)
    min_line = min(max(0.025 * float(np.ptp(points, axis=0).max()), 5.0), 15.0)  # as backend.reference
    for snap in (False, True):
        prims = fitting.fit_ring(points, tolerance, min_line)
        assert [p.kind for p in prims] == ["line", "arc"] * 5
        if snap:
            fitting.snap_axes([prims])
            fitting.refit_lines(points, prims)
            fitting.fit_fillets(points, prims, tolerance, sigma)
        fitting.correct_blur(prims, sigma)
        assert [p.kind for p in prims].count("line") == 5
        assert abs(max(p.data["r"] for p in prims if p.kind == "arc") / ppm - radius) < 0.03
        # Each right angle: a blur-rounded arc, or (snapped, fitting.fit_fillets) a sharp
        # corner with the bound on any fillet there, kept by the edge after it.
        square, m = [], len(prims)
        for k, before in enumerate(prims):
            if before.kind != "line":
                continue
            between, after = prims[(k + 1) % m], prims[(k + 2) % m]
            if between.kind == "line" and abs(before.data["d"] @ between.data["d"]) < 0.1:
                square.append(between.data["sharp_bound"] / ppm)
            elif between.kind == "arc" and after.kind == "line" and abs(before.data["d"] @ after.data["d"]) < 0.1:
                square.append(between.data["r"] / ppm)
        assert len(square) == 3 and max(square) < 0.6
        if snap:
            assert [p.kind for p in prims].count("arc") < 5
        outline = Polygon(fitting.sample_segments(fitting.segments(prims), 0.01))
        assert outline.is_valid and abs(outline.area / ppm**2 / plate.area - 1) < 3e-4


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
