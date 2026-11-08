"""Reproduce the handbook's synthetic calculations with cadkit (standard library only).

Usage, from any directory:

    python3 examples/calculate.py            # print and write calculation-results.json
    python3 examples/calculate.py --check    # fail if the committed JSON differs
    python3 examples/calculate.py --output other.json

The numbers are synthetic teaching values, not measurements. Every formula is
imported from ``cadkit.calc`` so the examples, the command line, and the tests
share one implementation.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cadkit import calc  # noqa: E402

DEFAULT_OUTPUT = HERE / "calculation-results.json"


def compute() -> dict:
    # Section 5: planar scale and first-order uncertainty.
    scale = calc.planar_scale(50.0, 1000.0)
    length = calc.scaled_length(640.0, scale)
    standard_uncertainty = calc.ratio_uncertainty(640.0, 2.0, 1000.0, 2.0, 50.0, 0.05)["u"]

    # Section 12: tessellation of a 10 mm radius at 0.02 mm chord error.
    radius, error = 10.0, 0.02
    segments = calc.min_segments(radius, error)
    actual_error = calc.chord_error(radius, segments)
    previous_error = calc.chord_error(radius, segments - 1)
    assert actual_error <= error < previous_error
    assert math.isclose(length, 32.0)

    # Section 16: nominal spur-gear pair.
    gear = calc.gear_pair(2.0, 20, 40)
    assert math.isclose(gear["center_distance"], 60.0)

    # Section 5: check a calibration against itself (known 50 x 90 mm rectangle).
    aspect = calc.aspect_check(50.0, 90.0, 400.0, 675.0)
    assert math.isclose(aspect["squat_percent"], 6.25)
    assert round(aspect["stretch_percent"], 1) == 6.7

    # Section 5: features off the reference plane, actual = plane-scale size x (Z + d) / Z.
    z_mm, delta_mm, plane_size_mm = 500.0, 60.0, 40.0
    depth_factor = calc.depth_factor(z_mm, delta_mm)
    corrected_size = plane_size_mm * depth_factor
    factor_low, factor_high = calc.depth_factor_range(350.0, 800.0, 30.0, 80.0)
    assert math.isclose(depth_factor, 1.12) and math.isclose(corrected_size, 44.8)
    assert round(factor_low, 2) == 1.04 and round(factor_high, 2) == 1.23

    # Section 5: camera distance from a 35 mm-equivalent focal length (diagonal definition).
    focal_px = calc.focal_px_from_35mm(26.0, 4000.0, 3000.0)
    camera_distance = calc.camera_distance(focal_px, 100.0, 500.0)
    assert round(focal_px) == 3005 and round(camera_distance) == 601

    # Section 3: rounding interval of a label printed to 0.01 inch.
    label_in = 3.25
    label = calc.rounding_uncertainty(label_in, "in", 2)
    assert math.isclose(label["value_mm"], 82.55) and math.isclose(label["half_interval_mm"], 0.127)
    assert round(label["standard_uncertainty_mm"], 3) == 0.073

    # Section 11: a slot coated on both faces.
    coat_per_face_mm = 0.08
    slot_width_loss_mm = calc.coating_loss(coat_per_face_mm, 2)
    assert math.isclose(slot_width_loss_mm, 0.16)

    return {
        "status": "synthetic teaching calculations, not measurements",
        "scale_mm_per_pixel": scale,
        "feature_length_mm": length,
        "standard_uncertainty_mm_independent_small_error_model": standard_uncertainty,
        "circle_radius_mm": radius,
        "allowed_chord_error_mm": error,
        "minimum_circle_segments": segments,
        "actual_chord_error_mm": actual_error,
        "previous_segment_count_error_mm": previous_error,
        "gear_module_mm": 2.0,
        "gear_teeth": [20, 40],
        "gear_pitch_diameters_mm": [gear["d1"], gear["d2"]],
        "gear_nominal_center_distance_mm": gear["center_distance"],
        "gear_output_input_speed_ratio": gear["speed_ratio"],
        "calibration_check_known_aspect": aspect["known_aspect"],
        "calibration_check_image_aspect": aspect["image_aspect"],
        "calibration_check_squat_percent": aspect["squat_percent"],
        "calibration_check_scale_mm_per_pixel_horizontal": aspect["scale_h"],
        "calibration_check_scale_mm_per_pixel_vertical": aspect["scale_v"],
        "calibration_check_vertical_stretch_percent": aspect["stretch_percent"],
        "off_plane_reference_distance_mm": z_mm,
        "off_plane_extra_depth_mm": delta_mm,
        "off_plane_depth_factor": depth_factor,
        "off_plane_corrected_size_mm": corrected_size,
        "off_plane_factor_range": [factor_low, factor_high],
        "camera_focal_length_px": focal_px,
        "camera_distance_mm": camera_distance,
        "label_inches": label_in,
        "label_mm": label["value_mm"],
        "label_rounding_half_interval_mm": label["half_interval_mm"],
        "label_rounding_standard_uncertainty_mm": label["standard_uncertainty_mm"],
        "coating_per_face_mm": coat_per_face_mm,
        "coated_slot_width_loss_mm": slot_width_loss_mm,
    }


def render(result: dict) -> str:
    return json.dumps(result, indent=2) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true",
                        help="compare with the output file instead of writing it")
    args = parser.parse_args(argv)
    text = render(compute())
    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
        if current != text:
            print(f"{args.output} is out of date; run python3 examples/calculate.py", file=sys.stderr)
            return 1
        print(f"{args.output.name} matches the calculations")
        return 0
    args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
