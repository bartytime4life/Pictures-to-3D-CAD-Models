"""The photo benchmark must report what a trace measured against what was entered.

The unit tests use hand-built geometry with known dimensions. The end-to-end test runs
the command on rendered photos (tests/synthetic.py), so its figures are regression
guards for the runner and say nothing about real photos.
"""

import io
import itertools
import json
import math
import random
from fractions import Fraction

import numpy as np
import pytest
from PIL import Image

from scripts import photo_benchmark as pb

MM_PER_PX = 0.25


def placed(points, angle_deg=17.0, shift=(180.0, 140.0)):
    """Design millimetres -> profile pixels: rotated, shifted and scaled."""
    a = math.radians(angle_deg)
    rotation = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return ((np.atleast_2d(points) @ rotation.T + shift) / MM_PER_PX).tolist()


def arc(centre, radius, start_deg, end_deg):
    angles = np.radians([start_deg, (start_deg + end_deg) / 2, end_deg])
    points = np.column_stack(
        [centre[0] + radius * np.cos(angles), centre[1] + radius * np.sin(angles)]
    )
    start, mid, end = placed(points)
    return {"kind": "arc", "start": start, "mid": mid, "end": end}


def line(a, b):
    start, end = placed([a, b])
    return {"kind": "line", "start": start, "end": end}


def circle(centre, diameter):
    return [{"kind": "circle", "center": placed(centre)[0], "radius": diameter / 2 / MM_PER_PX}]


def plate_profile():
    """A 120 x 70 plate with R8 corners, a D22 and two D6 holes and a 24 x 8 slot,
    turned 17 degrees."""
    outer = [
        line((-52, -35), (52, -35)),
        arc((52, -27), 8, -90, 0),
        line((60, -27), (60, 27)),
        arc((52, 27), 8, 0, 90),
        line((52, 35), (-52, 35)),
        arc((-52, 27), 8, 90, 180),
        line((-60, 27), (-60, -27)),
        arc((-52, -27), 8, 180, 270),
    ]
    slot = [
        line((17, -4), (33, -4)),
        arc((33, 0), 4, -90, 90),
        line((33, 4), (17, 4)),
        arc((17, 0), 4, 90, 270),
    ]
    holes = [circle((-20, 0), 22), circle((48, 25), 6), circle((-48, 25), 6), slot]
    return {
        "reference": {"mm_per_px": MM_PER_PX},
        "primitives": {"outer": outer, "holes": holes},
    }


def test_features_are_read_from_the_fitted_geometry_whatever_its_rotation():
    found = pb.features(plate_profile())
    assert found["outline"] == [pytest.approx((120, 70), abs=2e-3)]
    assert sorted(found["diameters"]) == [
        (pytest.approx(6), False),
        (pytest.approx(6), False),
        (pytest.approx(22), False),
    ]
    assert found["openings"] == [pytest.approx((24, 8), abs=2e-3)]
    assert sorted(found["radii"]) == pytest.approx([4, 4, 8, 8, 8, 8])
    assert sorted(found["centre_distances"]) == pytest.approx(
        [math.hypot(28, 25), math.hypot(68, 25), 96]
    )


def test_a_disc_is_both_an_outline_and_an_outside_diameter():
    disc = {
        "reference": {"mm_per_px": MM_PER_PX},
        "primitives": {"outer": circle((0, 0), 60), "holes": [circle((0, 0), 16)]},
    }
    found = pb.features(disc)
    assert found["outline"] == [pytest.approx((60, 60), abs=2e-3)]
    assert sorted(found["diameters"]) == [(pytest.approx(16), False), (pytest.approx(60), True)]
    assert found["openings"] == [] and found["centre_distances"] == []


def by_label(samples):
    out = {}
    for sample in samples:
        out.setdefault(sample["label"], []).append(sample)
    return out


def test_each_caliper_value_takes_the_nearest_unused_feature():
    found = {
        "outline": [(120.04, 69.97)],
        "diameters": [(21.97, False), (6.02, False), (5.99, False), (3.0, False), (60.1, True)],
        "openings": [(30.0, 8.0), (24.05, 7.98)],
        "radii": [],
        "centre_distances": [72.0, 96.01, 37.5],
    }
    measured = {
        "outline": [[120.0, 70.0]],
        "diameters": [6.0, 22.0, 6.0, 60.0, 10.0],
        "openings": [[24.0, 8.0]],
        "radii": [8.0],
        "centre_distances": [96.0],
    }
    rows = by_label(pb.samples(measured, found))
    assert [s["measured_mm"] for s in rows["Outline length"] + rows["Outline width"]] == [120.04, 69.97]
    assert sorted(s["measured_mm"] for s in rows["Ø6"]) == [5.99, 6.02]
    assert rows["Ø22"][0]["measured_mm"] == 21.97
    assert rows["Opening 24 × 8 length"][0]["measured_mm"] == 24.05
    assert rows["Opening 24 × 8 width"][0]["measured_mm"] == 7.98
    assert rows["Centres 96"][0]["measured_mm"] == 96.01
    # Nothing traced lies within reach of these two, and a miss is reported as one.
    assert rows["Ø10"][0]["measured_mm"] is None
    assert rows["R8"][0]["measured_mm"] is None
    # Which way each dimension moves when every boundary moves outward.
    assert rows["Outline length"][0]["edge"] == 2
    assert rows["Ø60"][0]["edge"] == 2
    assert rows["Ø22"][0]["edge"] == -2
    assert rows["Opening 24 × 8 width"][0]["edge"] == -2
    assert rows["Centres 96"][0]["edge"] == 0
    assert rows["R8"][0]["edge"] is None


def assignment_objective(costs, chosen):
    edges = [(i, j) for i, j in enumerate(chosen) if j is not None]
    assert len({j for _, j in edges}) == len(edges)
    assert all(costs[i][j] is not None for i, j in edges)
    return -len(edges), sum((Fraction(float(costs[i][j])) for i, j in edges), Fraction())


def exhaustive_assignment_objective(costs, columns):
    """Independent oracle: enumerate every partial injection, with no graph solver."""
    for count in range(min(len(costs), columns), -1, -1):
        totals = []
        for rows in itertools.combinations(range(len(costs)), count):
            for cols in itertools.permutations(range(columns), count):
                values = [costs[i][j] for i, j in zip(rows, cols)]
                if all(value is not None for value in values):
                    totals.append(sum((Fraction(float(value)) for value in values), Fraction()))
        if totals:
            return -count, min(totals)
    raise AssertionError("The empty assignment must always exist")


@pytest.mark.parametrize("rows,columns", list(itertools.product(range(6), repeat=2)))
def test_global_assignment_matches_an_exhaustive_independent_oracle(rows, columns):
    rng = random.Random(1_237 + rows * 31 + columns)
    for _ in range(12):
        costs = [
            [
                rng.choice([None, None, 0, 1, 3, 0.1, math.nextafter(0.1, math.inf)])
                for _ in range(columns)
            ]
            for _ in range(rows)
        ]
        chosen = pb.match(list(range(rows)), list(range(columns)), lambda i, j, costs=costs: costs[i][j])
        assert assignment_objective(costs, chosen) == exhaustive_assignment_objective(
            costs, columns
        )


@pytest.mark.parametrize(
    "expected,candidates,values",
    [
        ([6, 7], [6.4, 5], [5, 6.4]),  # greedy leaves 7 unmatched
        ([100, 101], [100.4, 99], [99, 100.4]),  # greedy matches both but costs 2.4, not 1.6
    ],
)
def test_global_size_assignment_repairs_both_greedy_failure_modes(expected, candidates, values):
    chosen = pb.match(expected, candidates, pb._scalar_cost)
    assert [candidates[j] for j in chosen] == values


def test_unique_correspondence_is_invariant_to_input_permutations_and_extra_candidates():
    for expected in itertools.permutations([6, 7, 10]):
        for candidates in itertools.permutations([6.4, 5, 10.1, 50]):
            chosen = pb.match(expected, candidates, pb._scalar_cost)
            assert {e: candidates[j] for e, j in zip(expected, chosen)} == {6: 5, 7: 6.4, 10: 10.1}


def test_paired_dimensions_use_global_assignment_without_relaxing_either_gate():
    expected, candidates = [(10, 5), (11, 5)], [(10.4, 5), (9, 5)]
    assert pb.match(expected, candidates, pb._pair_cost) == [1, 0]
    assert pb.match([(10, 5)], [(10, 7)], pb._pair_cost) == [None]
    assert pb.match([6], [7], pb._scalar_cost) == [0]
    assert pb.match([6], [math.nextafter(7, math.inf)], pb._scalar_cost) == [None]


def test_equal_costs_and_duplicate_sizes_have_deterministic_ties():
    for _ in range(4):
        assert pb.match([6, 7], [6.5, 6.5], pb._scalar_cost) == [0, 1]
        assert pb.match([6, 6, 6], [6, 6], pb._scalar_cost) == [0, 1, None]
    assert pb.match([1], [], pb._scalar_cost) == [None]
    assert pb.match([], [1], pb._scalar_cost) == []
    assert pb.match([6, 7], [50, 60], pb._scalar_cost) == [None, None]


def test_small_real_cost_differences_are_not_erased_by_tie_penalties_or_float_summation():
    costs = [[1.0, 1.0], [0.0, math.ulp(1.0) / 4]]
    chosen = pb.match([0, 1], [0, 1], lambda i, j: costs[i][j])
    assert chosen == [1, 0]
    assert assignment_objective(costs, chosen) == exhaustive_assignment_objective(costs, 2)


@pytest.mark.parametrize("value", [math.nan, math.inf, -1])
def test_invalid_matching_costs_are_refused(value):
    with pytest.raises(pb.ManifestError, match="finite and nonnegative"):
        pb.match([1], [1], lambda a, b: value)


@pytest.mark.parametrize("shape", [(129, 1), (1, 2049), (128, 1025)])
def test_matching_work_limits_refuse_instead_of_pruning_or_evaluating_costs(shape):
    def no_cost(a, b):
        raise AssertionError("Work limit must be checked before evaluating candidate costs")

    with pytest.raises(pb.ManifestError, match="work limit"):
        pb.match(list(range(shape[0])), list(range(shape[1])), no_cost)


def sample(expected, edge, error):
    return {
        "kind": "diameters",
        "label": f"Ø{expected:g}",
        "expected_mm": expected,
        "measured_mm": None if error is None else expected + error,
        "edge": edge,
    }


def test_scale_and_edge_offset_are_recovered_from_errors_that_hold_both():
    scale, offset = 0.002, 0.04
    design = [(120, 2), (70, 2), (22, -2), (6, -2), (96, 0), (50, 0)]
    found = [sample(size, edge, scale * size + edge * offset) for size, edge in design]
    # A radius and a missed dimension take no part.
    found += [{**sample(8, None, 0.5), "kind": "radii"}, sample(10, -2, None)]
    fit = pb.scale_and_edge(found)
    assert fit["scale_percent"] == pytest.approx(0.2)
    assert fit["edge_offset_mm"] == pytest.approx(0.04)
    assert fit["residual_mm"] == pytest.approx(0, abs=1e-9)


@pytest.mark.parametrize(
    "design",
    [
        [(120, 2), (70, 2), (22, -2)],  # too few
        [(96, 0), (50, 0), (108, 0), (30, 0)],  # centres alone hold no edge offset
        [(40, 2), (40, 2), (40.01, 2), (40, 2)],  # one size cannot separate the two
    ],
)
def test_scale_and_edge_offset_are_not_guessed_when_the_errors_cannot_hold_both(design):
    assert pb.scale_and_edge([sample(size, edge, 0.01) for size, edge in design]) is None


def test_a_row_reports_mean_spread_worst_and_misses():
    def photo(name, *errors):
        return {"file": name, "samples": [sample(6, -2, e) for e in errors]}

    rows = pb.rows_of(
        [photo("a.jpg", 0.01, 0.03), photo("b.jpg", 0.02, None), photo("c.jpg", -0.05, 0.02)]
    )
    assert len(rows) == 1
    row = rows[0]
    errors = [0.01, 0.03, 0.02, -0.05, 0.02]
    assert row["features"] == 2 and row["photos"] == 3 and row["missing"] == 1
    assert row["mean_error_mm"] == pytest.approx(np.mean(errors))
    assert row["spread_mm"] == pytest.approx(np.std(errors, ddof=1))
    assert row["worst_error_mm"] == pytest.approx(-0.05) and row["worst_photo"] == "c.jpg"
    single = pb.rows_of([photo("a.jpg", 0.01)])[0]
    assert single["spread_mm"] is None and single["mean_error_mm"] == pytest.approx(0.01)
    missed = pb.rows_of([photo("a.jpg", None)])[0]
    assert missed["mean_error_mm"] is None and missed["worst_error_mm"] is None


def test_the_sheet_proportion_figure_is_read_from_either_trace_note():
    assert pb.sheet_proportions(
        ["Fitted 1 circle(s).", "Sheet proportions check: the photo matches the chosen sheet within 0.12 %."]
    ) == pytest.approx(0.12)
    assert pb.sheet_proportions(
        ["The sheet's proportions in the photo differ from the chosen size by -5.9 % (width : height …)."]
    ) == pytest.approx(-5.9)
    assert pb.sheet_proportions(["Fitted 1 circle(s)."]) is None


def test_a_photo_is_traced_with_its_part_s_settings(tmp_path, monkeypatch):
    from backend import tracing

    calls = []

    def fake_trace(data, **settings):
        calls.append((data, settings))
        profile = plate_profile()
        profile["reference"].update(edge_blur_mm=0.1, lens_k1=-0.02, notes=["Fitted."])
        return {"profile": profile}

    monkeypatch.setattr(tracing, "trace_image", fake_trace)
    (tmp_path / "a.jpg").write_bytes(b"photo")
    settings = {"measured": {"diameters": [22.0]}, "light_part": True}
    record = pb.trace_photo(
        tmp_path / "a.jpg", {**settings, "sheet": "letter", "thickness_mm": 3.0}, snap=False
    )
    custom = {**settings, "sheet": [200.0, 300.0], "thickness_mm": None}
    pb.trace_photo(tmp_path / "a.jpg", custom, snap=True)
    assert calls[0] == (
        b"photo",
        {"inverted": True, "reference": "letter", "sheet_mm": None, "thickness_mm": 3.0, "snap": False},
    )
    assert calls[1][1] == {
        "inverted": True,
        "reference": "custom",
        "sheet_mm": (200.0, 300.0),
        "thickness_mm": None,
        "snap": True,
    }
    assert record["traced"] and record["file"] == "a.jpg"
    assert record["samples"][0]["measured_mm"] == pytest.approx(22)
    assert record["camera_height_mm"] is None and record["sheet_proportions_percent"] is None
    assert record["fit"] is None  # one dimension cannot hold a scale and an edge offset


def jpeg(colour=(128, 128, 128), size=(640, 480)):
    buffer = io.BytesIO()
    Image.new("RGB", size, colour).save(buffer, "JPEG")
    return buffer.getvalue()


def write_folder(folder, manifest, photos=("a.jpg",)):
    for name in photos:
        (folder / name).write_bytes(jpeg())
    text = manifest if isinstance(manifest, str) else json.dumps(manifest)
    (folder / pb.MANIFEST).write_text(text, encoding="utf-8")
    return folder


def part(**changes):
    return {"name": "disc", "photos": "a.jpg", "measured": {"diameters": [60]}, **changes}


def test_a_manifest_is_read_with_its_photos_resolved(tmp_path):
    manifest = {
        "sheet": [209.5, 297.4],
        "caliper_uncertainty_mm": 0.02,
        "parts": [
            part(photos=["a.jpg", "*.jpg"], measured={"outline": [70, 120.5], "openings": [[8, 24]]}),
            part(name="ring", sheet="letter", thickness_mm=3, light_part=True),
        ],
    }
    loaded = pb.load_manifest(write_folder(tmp_path, manifest, photos=("a.jpg", "b.jpg")))
    assert loaded["caliper_uncertainty_mm"] == 0.02
    disc, ring = loaded["parts"]
    assert [p.name for p in disc["photos"]] == ["a.jpg", "b.jpg"]  # listed once, in order
    assert disc["measured"] == {"outline": [[120.5, 70]], "openings": [[24, 8]]}
    assert disc["sheet"] == [209.5, 297.4] and disc["thickness_mm"] is None
    assert ring["sheet"] == "letter" and ring["thickness_mm"] == 3 and ring["light_part"] is True


@pytest.mark.parametrize(
    ("manifest", "reason"),
    [
        ("{not json", "not valid JSON"),
        ({"parts": []}, '"parts" list'),
        ({"parts": [part()], "sheets": "a4"}, "unknown setting 'sheets'"),
        ({"parts": [part(), part()]}, 'Two parts are named "disc"'),
        ({"parts": [part(name=" ")]}, 'needs a "name"'),
        ({"parts": [part(thicknes_mm=3)]}, "unknown setting 'thicknes_mm'"),
        ({"parts": [part(photos="missing-*.jpg")]}, "no photo matches"),
        ({"parts": [part(photos="")]}, "no photo matches"),
        ({"parts": [part(photos="../a.jpg")]}, "inside the benchmark folder"),
        ({"parts": [part(photos=[])]}, 'needs "photos"'),
        ({"parts": [part(measured={})]}, 'needs "measured"'),
        ({"parts": [part(measured={"diameter": [6]})]}, "unknown measurement 'diameter'"),
        ({"parts": [part(measured={"diameters": 6})]}, "must be a list"),
        ({"parts": [part(measured={"diameters": ["6"]})]}, "must be a number"),
        ({"parts": [part(measured={"diameters": [0]})]}, "must be above 0"),
        ({"parts": [part(measured={"diameters": [True]})]}, "must be a number"),
        ({"parts": [part(measured={"outline": [120, 70, 4]})]}, "[length, width] pairs"),
        ({"parts": [part(measured={"openings": [24, 8]})]}, "[length, width] pairs"),
        ({"parts": [part(thickness_mm=-1)]}, "thickness_mm must be above 0"),
        ({"parts": [part(light_part="yes")]}, "must be true or false"),
        ({"parts": [part()], "sheet": "a3"}, '"a4", "letter"'),
        ({"parts": [part(sheet=[210, 5])]}, "sheet side must be above 10"),
    ],
)
def test_a_manifest_that_cannot_be_used_says_why(tmp_path, manifest, reason):
    with pytest.raises(pb.ManifestError) as refusal:
        pb.load_manifest(write_folder(tmp_path, manifest))
    assert reason in str(refusal.value)


def test_a_folder_without_a_manifest_stops_the_command(tmp_path, capsys):
    assert pb.main([str(tmp_path)]) == 1
    assert f"No {pb.MANIFEST}" in capsys.readouterr().err


def test_manifest_measurement_limit_is_explicit_and_actionable(tmp_path):
    manifest = {"parts": [part(measured={"radii": [8.0] * 129})]}
    with pytest.raises(pb.ManifestError, match="at most 128 features per kind"):
        pb.load_manifest(write_folder(tmp_path, manifest))


def test_coverage_conserves_all_requested_scalars_across_parts_failures_and_missing_features(
    tmp_path, monkeypatch
):
    manifest = {
        "parts": [
            part(name="holes", photos=["good.jpg", "failed.jpg"], measured={"diameters": [6, 7]}),
            part(
                name="plate",
                photos="partial.jpg",
                measured={
                    "outline": [120, 70],
                    "openings": [[24, 8]],
                    "radii": [8],
                    "centre_distances": [50],
                },
            ),
        ]
    }
    write_folder(tmp_path, manifest, photos=("good.jpg", "failed.jpg", "partial.jpg"))

    def trace(path, part, snap, name):
        if name == "failed.jpg":
            return {"file": name, "traced": False, "reason": "Explicit failed-trace fixture"}
        found = {
            "outline": [(120.04, 70.02)] if name == "partial.jpg" else [],
            "diameters": [(6.4, False), (5, False)] if name == "good.jpg" else [],
            "openings": [],
            "radii": [8.03] if name == "partial.jpg" else [],
            "centre_distances": [],
        }
        return {
            "file": name,
            "traced": True,
            "samples": pb.samples(part["measured"], found),
            "fit": None,
            "edge_blur_mm": 0.1,
            "sheet_proportions_percent": 0.0,
        }

    monkeypatch.setattr(pb, "trace_photo", trace)
    report = pb.run(tmp_path)
    assert {
        key: report["summary"][key] for key in ("requested", "compared", "unmatched", "unavailable")
    } == {
        "requested": 10,
        "compared": 5,
        "unmatched": 3,
        "unavailable": 2,
    }
    assert report["summary"]["samples"] == 5 and report["summary"]["missing"] == 3
    for record in [
        *report["parts"],
        *(photo for part in report["parts"] for photo in part["photos"]),
    ]:
        counts = record["coverage"]
        assert (
            counts["requested"] == counts["compared"] + counts["unmatched"] + counts["unavailable"]
        )
    assert report["summary"]["worst_abs_error_mm"] == pytest.approx(1.0)
    table = pb.render(report)
    assert (
        "5 of 10 requested compared; 3 unmatched in successful traces; 2 unavailable in failed traces"
        in table
    )
    assert "Matched dimensions only" in table and "correspondence gate" in table
    assert "physical feature identity" in table and "not a propagated uncertainty" in table
    assert "2 dimensions unavailable" in table
    assert "smaller errors cannot be told" not in table


def test_a_run_in_which_nothing_traced_fails_and_says_why(tmp_path, capsys):
    write_folder(tmp_path, {"parts": [part(photos=["a.jpg", "set-*/a.jpg"])]})
    for name in ("set-1", "set-2"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "a.jpg").write_bytes(jpeg())
    assert pb.main([str(tmp_path)]) == 1
    printed = capsys.readouterr().out
    assert "0 of 3 photos traced" in printed
    assert (
        "0 of 3 requested compared; 0 unmatched in successful traces; 3 unavailable in failed traces"
        in printed
    )
    assert "No dimensions matched" in printed
    # Photos of the same name in different subfolders stay distinguishable.
    for name in ("a.jpg", "set-1/a.jpg", "set-2/a.jpg"):
        assert f"| {name} | | | | Not traced: " in printed


def test_the_example_is_not_written_over_existing_files(tmp_path, capsys):
    (tmp_path / "keep.txt").write_text("mine", encoding="utf-8")
    assert pb.main(["--example", str(tmp_path)]) == 1
    assert "not empty" in capsys.readouterr().err
    assert [p.name for p in tmp_path.iterdir()] == ["keep.txt"]


@pytest.fixture(scope="module")
def example_run(tmp_path_factory):
    """The command run on two rendered photos of the flat test plate, plus a blank
    photo and a caliper value for a hole the plate does not have."""
    folder = tmp_path_factory.mktemp("benchmark") / "photos"
    pb.write_example(folder, thickness=0.0, shots=pb.EXAMPLE_SHOTS[:2])
    manifest = json.loads((folder / pb.MANIFEST).read_text(encoding="utf-8"))
    manifest["sheet"] = [210.0, 297.0]  # A4, entered as a measured sheet
    manifest["parts"][0]["photos"].append("blank.jpg")
    manifest["parts"][0]["measured"]["diameters"].append(40.0)
    write_folder(folder, manifest, photos=("blank.jpg",))
    report, table = folder.parent / "report.json", folder.parent / "report.md"
    status = pb.main([str(folder), "--json", str(report), "--markdown", str(table)])
    return {
        "status": status,
        "folder": folder,
        "json": report.read_text(encoding="utf-8"),
        "markdown": table.read_text(encoding="utf-8"),
    }


def test_rendered_photos_are_measured_against_the_manifest(example_run):
    assert example_run["status"] == 0
    report = json.loads(example_run["json"])
    assert report["summary"]["photos"] == 3 and report["summary"]["traced"] == 2
    assert report["summary"]["missing"] == 2  # the absent Ø40, once per traced photo
    assert {
        key: report["summary"][key] for key in ("requested", "compared", "unmatched", "unavailable")
    } == {
        "requested": 51,
        "compared": 32,
        "unmatched": 2,
        "unavailable": 17,
    }
    assert report["summary"]["worst_abs_error_mm"] < 0.06
    (plate,) = report["parts"]
    assert "thickness_mm" not in json.loads((example_run["folder"] / pb.MANIFEST).read_text())
    rows = {row["label"]: row for row in plate["rows"]}
    assert list(rows) == [
        "Outline length",
        "Outline width",
        "Ø22",
        "Ø6",
        "Ø40",
        "Opening 24 × 8 length",
        "Opening 24 × 8 width",
        "R8",
        "Centres 96",
        "Centres 50",
        "Centres 108.24",
    ]
    absent = rows.pop("Ø40")
    assert absent["errors"] == [] and absent["missing"] == 2 and absent["mean_error_mm"] is None
    for label, row in rows.items():
        assert len(row["errors"]) == 2 * row["features"] and not row["missing"], label
        assert abs(row["mean_error_mm"]) < 0.05, (label, row["mean_error_mm"])
        assert row["spread_mm"] is not None and row["spread_mm"] < 0.03, (label, row["spread_mm"])
    assert rows["Ø6"]["features"] == 4 and rows["R8"]["features"] == 4
    # Distances between centres do not move with the edges, so they are the tightest.
    assert all(abs(rows[f"Centres {d}"]["mean_error_mm"]) < 0.01 for d in ("96", "50", "108.24"))
    assert abs(plate["fit"]["scale_percent"]["mean"]) < 0.02
    assert abs(plate["fit"]["edge_offset_mm"]["mean"]) < 0.02
    assert plate["fit"]["scale_percent"]["spread"] is not None


def test_each_photo_reports_its_conditions_or_why_it_failed(example_run):
    first, second, blank = json.loads(example_run["json"])["parts"][0]["photos"]
    assert [p["file"] for p in (first, second, blank)] == ["plate-1.jpg", "plate-2.jpg", "blank.jpg"]
    for photo in (first, second):
        assert photo["traced"] and 0.05 < photo["edge_blur_mm"] < 1
        # Read from the trace's own note; a reworded note must not go unnoticed.
        assert photo["sheet_proportions_percent"] is not None
        assert abs(photo["sheet_proportions_percent"]) < 0.5
        assert photo["fit"] is not None and photo["notes"]
    assert blank["traced"] is False and len(blank["reason"]) > 20
    assert "samples" not in blank


def test_the_report_holds_no_image_data_and_no_folder_path(example_run):
    text = example_run["json"]
    assert str(example_run["folder"].parent) not in text
    assert "data_url" not in text and "base64" not in text
    assert len(text) < 60_000


def test_the_printed_tables_show_readings_misses_and_failures(example_run):
    table = example_run["markdown"]
    assert "2 of 3 photos traced." in table
    assert (
        "32 of 51 requested compared; 2 unmatched in successful traces; 17 unavailable in failed traces"
        in table
    )
    assert "| Ø6 (×4) | 6.00 | 8 | " in table
    assert "| Ø40 | 40.00 | 0 | — | — | — | 2 |" in table
    assert "| blank.jpg | | | | Not traced: " in table
    assert "Traced; 1 dimension(s) unmatched" in table
    assert "Fitted scale term " in table and "between photos" in table
    assert "In-sample residual" in table and "do not identify physical causes" in table
    assert "Sheet: 210 × 297 mm. No thickness given." in table


def test_mean_errors_beyond_the_calipers_are_marked():
    def row(error):
        return {
            "kind": "diameters",
            "label": "Ø6",
            "expected_mm": 6.0,
            "features": 1,
            "errors": [error],
            "missing": 0,
            "photos": 1,
            "mean_error_mm": error,
            "spread_mm": None,
            "worst_error_mm": error,
            "worst_photo": "a.jpg",
        }

    report = {
        "snap": False,
        "caliper_uncertainty_mm": 0.03,
        "summary": {
            "photos": 0,
            "traced": 0,
            "samples": 0,
            "missing": 0,
            "requested": 0,
            "compared": 0,
            "unmatched": 0,
            "unavailable": 0,
        },
        "parts": [
            {
                "name": "p",
                "sheet": [200, 300],
                "thickness_mm": 2,
                "photos": [],
                "fit": None,
                "rows": [row(e)],
                "coverage": {"requested": 1, "compared": 1, "unmatched": 0, "unavailable": 0},
            }
            for e in (0.029, -0.031)
        ],
    }
    table = pb.render(report)
    assert "| Ø6 | 6.00 | 1 | +0.029 | — | +0.029 |" in table
    assert "| Ø6 | 6.00 | 1 | **-0.031** | — | -0.031 |" in table
    assert "Sheet: 200 × 300 mm. Thickness: 2 mm." in table
    assert "snapping was off" in table
