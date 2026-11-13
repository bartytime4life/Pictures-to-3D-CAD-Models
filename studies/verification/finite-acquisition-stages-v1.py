#!/usr/bin/env python3
"""Capture a declared synthetic acquisition chain; never fit or alter a trace.

Numerical imports and all scientific work occur only inside ``run_scene`` after
configuration and fresh-directory validation. The caller owns the prospective
plan, source admission and complete scene census. This helper returns JSON-ready
metadata; every saved NPZ member is a numeric, non-object array.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = Path(__file__).resolve()
PLANE_SIZE = (64.0, 64.0)
SOURCE_SHAPE = (96, 96)
MARGIN = 16.0
ARC_VERTICES = 8193
Q_VALUES = (1.0, 1.25)
CONFIG_KEYS = {"name", "radius", "fraction", "normal_degrees", "centre", "blur"}
SOURCE_PATHS = (
    "studies/verification/finite-acquisition-stages-v1.py",
    "tests/synthetic.py",
    "backend/__init__.py",
    "backend/sheet.py",
    "backend/tone.py",
)


def _sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _sha_file(path):
    return _sha_bytes(Path(path).read_bytes())


def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite JSON number")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} is outside binary64") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _config(config):
    if not isinstance(config, dict) or set(config) != CONFIG_KEYS:
        raise ValueError("scene config must contain exactly " + ", ".join(sorted(CONFIG_KEYS)))
    name = config["name"]
    if not isinstance(name, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", name) is None:
        raise ValueError("name must be a safe scene identifier of 1..80 characters")
    radius = _number(config["radius"], "radius")
    fraction = _number(config["fraction"], "fraction")
    angle = _number(config["normal_degrees"], "normal_degrees")
    if not 0 < radius <= 32 or not -1 < fraction < 1 or abs(angle) > 36000:
        raise ValueError(
            "require 0 < radius <= 32, -1 < fraction < 1 and |normal_degrees| <= 36000"
        )
    centre = config["centre"]
    if not isinstance(centre, (list, tuple)) or len(centre) != 2:
        raise ValueError("centre must be two finite numbers")
    centre = [_number(v, "centre") for v in centre]
    if any(c - radius < 0 or c + radius > 64 for c in centre):
        raise ValueError("the complete declared disk must lie inside the 64 x 64 plane")
    blur = config["blur"]
    if blur not in ("isotropic", "directional"):
        raise ValueError("blur must be isotropic or directional")
    return {
        "name": name,
        "radius": radius,
        "fraction": fraction,
        "normal_degrees": angle,
        "centre": centre,
        "blur": blur,
    }


def _destination(output_dir):
    path = Path(output_dir).absolute()
    if path.exists() or path.is_symlink():
        raise ValueError("output directory must be new; existing paths and symlinks are refused")
    if not path.parent.is_dir():
        raise ValueError("output directory parent must already exist")
    return path


def _source_snapshot():
    return {name: _sha_file(ROOT / name) for name in SOURCE_PATHS}


def _exclusive(path, data):
    with Path(path).open("xb") as stream:
        stream.write(data)


def _array_record(array):
    if array.dtype.hasobject or array.dtype.kind not in "biuf" or not array.flags.c_contiguous:
        raise ValueError("saved stage arrays must be C-contiguous numeric arrays")
    return {
        "dtype": array.dtype.str,
        "shape": list(array.shape),
        "c_order_bytes_sha256": _sha_bytes(array.tobytes(order="C")),
    }


def _archive(path, arrays, np):
    records = {name: _array_record(array) for name, array in arrays.items()}
    with Path(path).open("xb") as stream:
        np.savez_compressed(stream, **arrays)
    return {"file": Path(path).name, "sha256": _sha_file(path), "arrays": records}


def _kernel_moments(kernel, np, coordinate_unit):
    """Moments of the represented coefficient array, normalized by its saved sum."""
    weights = np.asarray(kernel, dtype=np.float64)
    height, width = weights.shape
    yy, xx = np.mgrid[:height, :width].astype(np.float64)
    xx -= (width - 1) / 2
    yy -= (height - 1) / 2
    total = float(np.sum(weights, dtype=np.float64))
    if not math.isfinite(total) or total <= 0 or not np.all(np.isfinite(weights)):
        raise ArithmeticError("represented kernel has no finite positive sum")
    mx = float(np.sum(weights * xx, dtype=np.float64) / total)
    my = float(np.sum(weights * yy, dtype=np.float64) / total)
    dx, dy = xx - mx, yy - my
    covariance = [
        [float(np.sum(weights * dx * dx) / total), float(np.sum(weights * dx * dy) / total)],
        [float(np.sum(weights * dx * dy) / total), float(np.sum(weights * dy * dy) / total)],
    ]
    return {
        "coefficient_sum": total,
        "mean": [mx, my],
        "covariance": covariance,
        "coordinate_unit": coordinate_unit,
        "definition": "central coefficient moments divided by the represented coefficient sum",
    }


def _smoothing_comparison(before, actual, post_kernel, cv2, np):
    explicit = cv2.filter2D(before, -1, post_kernel, borderType=cv2.BORDER_REFLECT_101)
    # Kernel radius three: compare only complete, non-border stencils. No fitted
    # numerical tolerance or equality claim is made by this metadata helper.
    difference = actual[3:-3, 3:-3].astype(np.float64) - explicit[3:-3, 3:-3]
    return {
        "interior_half_open_xy": [3, 3, before.shape[1] - 3, before.shape[0] - 3],
        "max_abs_difference": float(np.max(np.abs(difference))),
        "whole_max_abs_difference": float(
            np.max(np.abs(actual.astype(np.float64) - explicit.astype(np.float64)))
        ),
        "whole_exact_array_equal": bool(np.array_equal(actual, explicit)),
        "exact_array_equal": bool(np.array_equal(actual[3:-3, 3:-3], explicit[3:-3, 3:-3])),
        "comparison": "GaussianBlur((0,0),.7) versus filter2D(getGaussianKernel(7,.7) outer)",
        "claim": "saved arithmetic comparison only; no bitwise equivalence assumed",
    }


def _operation(report, label, function, *args, **kwargs):
    """Retain attempted/completed declared stage calls, including a failed call."""
    record = {"name": label, "completed": False}
    report["stage_calls"].append(record)
    result = function(*args, **kwargs)
    record["completed"] = True
    return result


def run_scene(config, output_dir):
    """Save one fixed, known-map acquisition scene and return JSON-ready metadata.

    Config keys are ``name,radius,fraction,normal_degrees,centre,blur``. Geometry
    uses plane pixel units; blur is ``isotropic`` (sigma1.2) or ``directional``
    (major3,minor1,30degrees) in source pixels. The source has uniform background
    encoded230 and material encoded40, with no sheet/table boundary. q is fixed
    to1 and1.25 rectified pixels per plane unit. Output is a NEW directory.

    A failure after directory creation is saved in scene.json and returned with
    status=failed, preserving completed archives and source snapshots. The caller
    must check status and source_unchanged; this helper never turns a failure into
    a completed scene. It performs no inverse or geometric localization.
    """
    config = _config(config)
    output = _destination(output_dir)
    before = _source_snapshot()
    output.mkdir()  # Exclusive directory reservation also closes the preflight race.
    report = {
        "format": "pictures-to-cad-finite-acquisition-stages",
        "version": 1,
        "status": "started",
        "config": config,
        "config_sha256": _sha_bytes(_json_bytes(config)),
        "source_hashes_before": before,
        "source_hashes_after": {},
        "source_unchanged": False,
        "source_artifacts": {},
        "rows": [
            {
                "q": q,
                "M": [[1.0, 0.0, 16.5], [0.0, 1.0, 16.5], [0.0, 0.0, 1.0]],
                "k1": 0.0,
                "plane_size": list(PLANE_SIZE),
                "fields_file": filename,
                "status": "not_attempted",
            }
            for q, filename in zip(Q_VALUES, ("q-1.npz", "q-1p25.npz"), strict=True)
        ],
        "stage_calls": [],
        "work_scope": {"inverse_optimizer_calls": 0, "new_full_photo_traces": 0},
    }
    source_arrays = {}
    pending_fields = []
    np = None
    stage = "numerical_imports"
    try:
        import cv2
        import numpy as np
        import PIL
        import shapely
        from PIL import Image
        from shapely import affinity
        from shapely.geometry import Polygon

        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from backend import sheet, tone

        # tests is a namespace directory, so an installed regular `tests`
        # package can shadow it. Bind the declared generator file directly.
        spec = importlib.util.spec_from_file_location(
            "finite_acquisition_source_synthetic_v1", ROOT / "tests/synthetic.py"
        )
        if spec is None or spec.loader is None:
            raise ImportError("cannot load the declared tests/synthetic.py source")
        synthetic = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = synthetic
        spec.loader.exec_module(synthetic)

        for module, name in (
            (sheet, "backend/sheet.py"),
            (tone, "backend/tone.py"),
            (synthetic, "tests/synthetic.py"),
        ):
            if Path(module.__file__).resolve() != (ROOT / name).resolve():
                raise ValueError(f"imported module is outside the source snapshot: {name}")
        report["versions"] = {
            "numpy": np.__version__,
            "opencv": cv2.__version__,
            "pillow": PIL.__version__,
            "shapely": shapely.__version__,
            "python": sys.version,
        }
        stage = "source_geometry"
        radians = math.radians(config["normal_degrees"])
        normal = np.array([math.cos(radians), math.sin(radians)])
        tangent = np.array([-normal[1], normal[0]])
        first = math.acos(config["fraction"])
        angle = np.linspace(first, 2 * math.pi - first, ARC_VERTICES)
        contour = np.asarray(config["centre"]) + config["radius"] * (
            np.cos(angle)[:, None] * normal + np.sin(angle)[:, None] * tangent
        )
        polygon = Polygon(contour)
        if not polygon.is_valid or polygon.is_empty or polygon.area <= 0:
            raise ArithmeticError("declared tessellated D is not a valid positive polygon")
        coverage = _operation(
            report,
            "source_coverage",
            synthetic.coverage,
            affinity.translate(polygon, MARGIN, MARGIN),
            1.0,
            0.0,
            0.0,
            SOURCE_SHAPE,
        )
        coverage = np.ascontiguousarray(coverage, dtype=np.float32)
        source_arrays["coverage"] = coverage
        levels = [float(synthetic.srgb_to_linear(230)), float(synthetic.srgb_to_linear(40))]
        light = np.ascontiguousarray(
            levels[0] * (1.0 - coverage.astype(np.float64))
            + levels[1] * coverage.astype(np.float64),
            dtype=np.float32,
        )
        source_arrays["source_linear"] = light
        report["levels_linear"] = levels
        report["source_geometry"] = {
            "plane_size": list(PLANE_SIZE),
            "source_shape": list(SOURCE_SHAPE),
            "source_margin": MARGIN,
            "arc_vertices": ARC_VERTICES,
            "normal": normal.tolist(),
            "contour_sha256": _sha_bytes(np.ascontiguousarray(contour).tobytes()),
            "coordinate_unit": "plane_pixel",
            "source_pixel_index_convention": "coverage index i centred at plane i-margin; geometric source centre i+.5",
            "source_light": "float32(background*(1-float64(coverage))+material*float64(coverage))",
            "source_light_record": _array_record(light),
            "encoded_levels": [230, 40],
        }
        stage = "optical_filter"
        if config["blur"] == "isotropic":
            one = _operation(report, "optical_kernel", cv2.getGaussianKernel, 11, 1.2)
            kernel = np.ascontiguousarray(one @ one.T)
            nominal = [[1.44, 0.0], [0.0, 1.44]]
            kernel_definition = "getGaussianKernel(11,1.2) outer product"
        else:
            kernel = np.ascontiguousarray(
                _operation(report, "optical_kernel", synthetic.rotated_gaussian, 3.0, 1.0, 30.0)
            )
            theta = math.radians(30.0)
            rotation = np.array(
                [[math.cos(theta), -math.sin(theta)], [math.sin(theta), math.cos(theta)]]
            )
            nominal = (rotation @ np.diag([9.0, 1.0]) @ rotation.T).tolist()
            kernel_definition = "tests.synthetic.rotated_gaussian(3,1,30); float32 coefficients"
        source_arrays["kernel"] = kernel
        optical = np.ascontiguousarray(
            _operation(
                report,
                "optical_filter",
                cv2.filter2D,
                light,
                -1,
                kernel,
                borderType=cv2.BORDER_REFLECT_101,
            ),
            dtype=np.float32,
        )
        source_arrays["optical_linear"] = optical
        post_one = _operation(report, "post_kernel", cv2.getGaussianKernel, 7, 0.7)
        post_kernel = np.ascontiguousarray(post_one @ post_one.T)
        source_arrays["post_kernel"] = post_kernel
        kernel_moments = _kernel_moments(kernel, np, "source_pixel")
        post_moments = _kernel_moments(post_kernel, np, "rectified_pixel")
        report.update(
            kernel_covariance=kernel_moments["covariance"],
            post_kernel_covariance=post_moments["covariance"],
            nominal_optical_covariance=nominal,
            kernels={
                "optical": {"definition": kernel_definition, **kernel_moments},
                "post": {"definition": "getGaussianKernel(7,.7) outer product", **post_moments},
                "border": "BORDER_REFLECT_101",
                "correlation_convention": "cv2.filter2D; both represented kernels are centrosymmetric",
            },
        )
        stage = "png_roundtrip"
        encoded = (
            np.clip(_operation(report, "linear_to_srgb", synthetic.linear_to_srgb, optical), 0, 255)
            .round()
            .astype(np.uint8)
        )
        png_rgb = np.ascontiguousarray(np.repeat(encoded[:, :, None], 3, axis=2))
        source_arrays["png_rgb"] = png_rgb
        buffer = io.BytesIO()
        Image.fromarray(png_rgb).save(buffer, "PNG")
        png_bytes = buffer.getvalue()
        _exclusive(output / "source.png", png_bytes)
        report["source_artifacts"]["png"] = {
            "file": "source.png",
            "sha256": _sha_bytes(png_bytes),
        }
        stage = "png_decode"
        with Image.open(io.BytesIO(png_bytes)) as image:
            decoded_rgb = np.array(image.convert("RGB"), dtype=np.uint8, copy=True)
        rgb_equal = bool(np.array_equal(decoded_rgb, png_rgb))
        report["source_artifacts"]["png"].update(
            lossless_rgb_equal=rgb_equal, decoded_rgb_record=_array_record(decoded_rgb)
        )
        if not rgb_equal:
            raise ValueError("lossless PNG roundtrip changed encoded RGB samples")
        stage = "decoded_linear_mix"
        decoded = np.ascontiguousarray(
            _operation(report, "decoded_linear_mix", tone.linear_mix, decoded_rgb), dtype=np.float32
        )
        source_arrays["decoded_linear"] = decoded
        stage = "source_archive"
        report["source_artifacts"]["arrays"] = _archive(output / "source.npz", source_arrays, np)
        report["source_difference"] = {
            "max_abs_decoded_minus_optical": float(
                np.max(np.abs(decoded.astype(np.float64) - optical.astype(np.float64)))
            ),
            "unit": "linear_light_level_0_to_255_scale",
        }
        matrix = np.array(report["rows"][0]["M"])
        for row in report["rows"]:
            q, filename = row["q"], row["fields_file"]
            row["status"] = "started"
            arrays = {}
            pending_fields.append((row, arrays))
            stage = f"rectify_q_{q:g}"
            uq_rect = _operation(
                report,
                f"unquantized_rectify_q_{q:g}",
                sheet.rectify_gray,
                optical,
                matrix,
                0.0,
                PLANE_SIZE,
                q,
            )
            arrays["unquantized_rectified"] = np.ascontiguousarray(uq_rect)
            row["shape"] = list(uq_rect.shape)
            png_rect = _operation(
                report,
                f"png_rectify_q_{q:g}",
                sheet.rectify_gray,
                decoded,
                matrix,
                0.0,
                PLANE_SIZE,
                q,
            )
            arrays["png_rectified"] = np.ascontiguousarray(png_rect)
            stage = f"smooth_q_{q:g}"
            uq_final = _operation(
                report,
                f"unquantized_smooth_q_{q:g}",
                cv2.GaussianBlur,
                uq_rect,
                (0, 0),
                0.7,
                borderType=cv2.BORDER_REFLECT_101,
            )
            arrays["unquantized_final"] = np.ascontiguousarray(uq_final)
            png_final = _operation(
                report,
                f"png_smooth_q_{q:g}",
                cv2.GaussianBlur,
                png_rect,
                (0, 0),
                0.7,
                borderType=cv2.BORDER_REFLECT_101,
            )
            arrays["png_final"] = np.ascontiguousarray(png_final)
            stage = f"archive_q_{q:g}"
            row["stage_arrays"] = _archive(output / filename, arrays, np)
            row["smoothing_comparison"] = {}
            stage = f"unquantized_post_comparison_q_{q:g}"
            row["smoothing_comparison"]["unquantized"] = _operation(
                report,
                f"unquantized_explicit_post_q_{q:g}",
                _smoothing_comparison,
                uq_rect,
                uq_final,
                post_kernel,
                cv2,
                np,
            )
            stage = f"png_post_comparison_q_{q:g}"
            row["smoothing_comparison"]["png"] = _operation(
                report,
                f"png_explicit_post_q_{q:g}",
                _smoothing_comparison,
                png_rect,
                png_final,
                post_kernel,
                cv2,
                np,
            )
            row["status"] = "complete"
        report["status"] = "complete"
    except Exception as exc:  # noqa: BLE001 -- retain a failed scene; never mark it complete.
        report["status"] = "failed"
        report["error"] = {"stage": stage, "type": type(exc).__name__, "message": str(exc)}
        for row in report["rows"]:
            if row["status"] != "complete":
                row["error"] = report["error"].copy()
                if row["status"] == "started":
                    row["status"] = "failed"
    finally:
        # Preserve every completed numeric stage even if a later operation fails.
        # Partial archives have distinct fresh names and never replace a complete
        # or partially written original artifact.
        if np is not None:
            pending_archives = []
            if source_arrays and "arrays" not in report["source_artifacts"]:
                pending_archives.append(
                    (
                        report["source_artifacts"],
                        "partial_arrays",
                        "source-partial.npz",
                        source_arrays,
                    )
                )
            for row, arrays in pending_fields:
                if arrays and "stage_arrays" not in row:
                    filename = Path(row["fields_file"]).stem + "-partial.npz"
                    pending_archives.append((row, "partial_stage_arrays", filename, arrays))
            for holder, key, filename, arrays in pending_archives:
                try:
                    holder[key] = _archive(output / filename, arrays, np)
                except Exception as exc:  # noqa: BLE001 -- retain original and artifact failures.
                    report.setdefault("partial_archive_errors", []).append(
                        {"file": filename, "type": type(exc).__name__, "message": str(exc)}
                    )
        try:
            report["source_hashes_after"] = _source_snapshot()
            report["source_unchanged"] = before == report["source_hashes_after"]
        except OSError as exc:
            report["source_binding_error"] = {"type": type(exc).__name__, "message": str(exc)}
        if not report["source_unchanged"]:
            report["status"] = "failed"
        report["stage_call_counts"] = {
            "attempted": len(report["stage_calls"]),
            "completed": sum(record["completed"] for record in report["stage_calls"]),
            "scope": "declared coverage/kernel/filter/transfer/rectification calls, not scalar arithmetic operations",
        }
        report["metadata_file"] = "scene.json"
        _exclusive(output / "scene.json", _json_bytes(report))
    return report


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("JSON number is outside finite binary64")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path, help="one scene JSON configuration")
    parser.add_argument(
        "--output-dir", required=True, type=Path, help="NEW directory; parent exists"
    )
    args = parser.parse_args(argv)
    try:
        _destination(args.output_dir)
        if args.config.stat().st_size > 64 * 1024:
            raise ValueError("configuration exceeds 64 KiB")
        config = json.loads(
            args.config.read_bytes(),
            object_pairs_hook=_pairs,
            parse_float=_finite_float,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"nonfinite JSON: {value}")
            ),
        )
        _config(config)
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    report = run_scene(config, args.output_dir)
    sys.stdout.buffer.write(_json_bytes(report))
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
