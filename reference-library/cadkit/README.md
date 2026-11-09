# cadkit: calculators and checks for the handbook

`cadkit` is a small Python package that implements the handbook's arithmetic and file checks. It uses only the standard library and runs on Python 3.10 or later. Run it from the `reference-library` directory:

```bash
python3 -m cadkit --help
python3 -m cadkit <command> --help
```

Lengths are in millimetres unless an option says otherwise. Every numeric command accepts `--json`. Exit codes are `0` for success, `1` when a check fails (for example a mesh that is not closed, or a register with problems), and `2` for invalid input. Invalid input includes impossible or out-of-range values, results too large to represent, malformed JSON or STL, and a path that is missing, unreadable, a directory, or not writable. It prints one `error: …` line on standard error, never a traceback.

The results are arithmetic on the inputs you give. They are not measurements, and they inherit every assumption the handbook states for each formula.

## Commands

| Command | Handbook section | What it computes |
| --- | --- | --- |
| `scale` | 5 | mm/pixel from a reference; optional feature length |
| `uncertainty` | 5 | first-order uncertainty of `L = p × Lref / pref` |
| `aspect` | 5 | reference-rectangle proportion check and implied stretch |
| `depth` | 5 | off-plane factor `(Z + Δ) / Z`, corrected size, factor range |
| `camera` | 5 | focal length in pixels and camera distance from a 35 mm-equivalent focal length |
| `homography` | 5 | normalized-DLT plane homography, residuals, local mm/pixel at a point |
| `label` | 3 | rounding interval and standard uncertainty `a/√3` of a printed value |
| `evidence` | 3 | weakest evidence class among inputs |
| `units` | 2 | ranked unit interpretations for an imported extent |
| `chord` | 12 | segment count for a chord error, or the error for a count |
| `coating` | 11 | slot width lost to coatings |
| `coupon` | 15 | diametral clearance series for a hole coupon |
| `gear` | 16 | nominal spur-gear pair relations and an undercut warning |
| `wind` | 16 | first wind-power estimate `0.5 ρ A v³ Cp` |
| `meshcheck` | 2, 12, 18 | STL extents, area, volume, closed-ness, vertex manifoldness, orientation, components, genus (through-holes) |
| `params` | 17 | load and validate a design-parameter register |
| `new-project` | 4 | scaffold the minimum project folder from the templates |
| `route` | 1 | recommend a handbook workflow for an input and a goal (same rules as the HTML route finder) |
| `version` | | print the package version |

## Examples

These outputs were produced by the commands shown.

```text
$ python3 -m cadkit scale --known-mm 50 --reference-px 1000 --feature-px 640
scale: 0.05 mm/px
feature length: 32 mm (planar assumption)

$ python3 -m cadkit uncertainty --p 640 --up 2 --pref 1000 --upref 2 --lref 50 --ulref 0.05
length L: 32 mm
standard uncertainty u(L): 0.122963 mm (0.3843 %)
2u: 0.245927 mm (approximate 95 % only if near-normal)
model: first-order, independent inputs; omits perspective, distortion, bias, correlation

$ python3 -m cadkit chord --radius 10 --error 0.02
segments: 50
chord error: 0.0197327 mm at radius 10 mm
flat-to-flat diameter: 19.9605 mm
error with 49 segments: 0.0205461 mm

$ python3 -m cadkit depth --z 500 --delta 60 --size 40 --z-range 350 800 --delta-range 30 80
depth factor (Z + delta) / Z: 1.12
corrected size: 44.8 mm
factor range: 1.038 to 1.229

$ python3 -m cadkit gear --module 2 --teeth 12 40
pitch diameters: 24 mm, 80 mm
nominal centre distance: 52 mm
speed ratio w2/w1: -0.3
nominal relations only: no tooth profile, backlash, strength, or profile shift
warning: z1 = 12 is below the theoretical undercut limit 2/sin^2(alpha) = 17.1 for unshifted full-depth teeth; use profile shift or a validated generator.

$ python3 -m cadkit units --observed 0.06 --expected-mm 60
    0.00 %  x1000       file units are m
   69.52 %  x304.8      file units are ft
   97.46 %  x25.4       file units are in
   99.00 %  x10         file units are cm
   99.90 %  x1          file units are mm (no change)
best: file units are m -> 60 mm

$ python3 -m cadkit evidence measured image-derived proposed
derived value class: inferred

$ python3 -m cadkit route --input photo-set --goal editable
start: Workflow C: photographs to a printable organic mesh (section 8)
       Reconstruct, scale from a measured distance, clean conservatively, simplify deliberately.
then : Workflow D: mesh or point cloud to engineering surfaces (section 9)
       Segment regions, fit planes and cylinders, rebuild freeform patches only where needed.
check: Change a major parameter and regenerate to test the constraints
read:  capture-meshroom, capture-colmap, meshlab-docs, cadquery-docs, freecad-techdraw
calculators: scale, units, chord
warning: A photogrammetry mesh is not editable CAD; rebuild the important features (Workflow D).
```

A homography from four corners of a 50 × 40 mm rectangle imaged at 1000 × 800 pixels (`pts.json` holds `[[[0,0],[0,0]],[[1000,0],[50,0]],[[1000,800],[50,40]],[[0,800],[0,40]]]`):

```text
$ python3 -m cadkit homography --points pts.json --at 500 400
H =
  [ 0.05,  0,  0]
  [ 0,  0.05,  0]
  [ 0,  0,  1]
points: 4; RMS residual 7.803518e-15; max 1.087226e-14 (plane units)
at [500.0, 400.0]: maps to [25.0, 20.0]; local scale u 0.05, v 0.05 units/px (4.441e-14 % anisotropy)
warning: Exactly four point pairs: the homography reproduces them exactly, so residuals are zero by construction and are not accuracy evidence. Add well-distributed control points and reserve an independent check length.
```

`--points` takes a JSON file path or inline JSON, either as `[[[u, v], [x, y]], ...]` or as `{"src": [[u, v], ...], "dst": [[x, y], ...]}`. Any other shape is invalid input.

`--at` must be a finite pixel on the same side of the plane's vanishing line as the control points, that is, where the homogeneous `w = h31 u + h32 v + h33` has the control points' sign. A pixel on or beyond that line does not image the plane, although the formula would still map it to a confident-looking position and scale. `homography` therefore refuses it with exit code 2 and reports no mapping or local scale. The browser calculator shows the same error.

Checking the plate rendered by `examples/build_plate.py`:

```text
$ python3 -m cadkit meshcheck examples/output/two-hole-plate.stl --expect-mm 60
file: examples/output/two-hole-plate.stl
triangles: 220; welded vertices: 108; components: 1
extents: 60 x 30 x 4 (file units)
surface area: 4367.62; volume: 7044.57
watertight: True (boundary edges 0, non-manifold edges 0)
manifold: True (non-manifold vertices 0)
orientation consistent: True; degenerate triangles: 0
through-holes (genus): 2
hint: Largest extent 60 mm agrees with the expected 60 mm (within 0.5 %).
status: pass
```

Start a new project folder:

```bash
python3 -m cadkit new-project ../my-bracket --name "Shelf bracket"
```

It creates `inputs-third-party/`, `originals/`, `preprocessing/`, `calibration/`, `measurements/`, `reconstruction/`, `cad/`, `drawings/`, `print-exports/`, and `validation/`, each with a short README. It also copies the worksheets and registers into place and writes `README.md` and `source-manifest.csv`. It refuses to write into a non-empty directory.

## Python API

```python
import sys; sys.path.insert(0, "reference-library")   # or run from reference-library/
from cadkit import calc, homography, stl, params, scad, routes

calc.min_segments(10, 0.02)                    # 50
calc.ratio_uncertainty(640, 2, 1000, 2, 50, 0.05)["u"]   # 0.1229634...
calc.weakest_evidence(["measured", "proposed"])          # 'inferred'
H = homography.fit(src_pixels, dst_mm)          # 3x3, H[2][2] == 1
homography.local_scale(H, (u, v))               # (mm/px along u, mm/px along v)
report = stl.analyze(stl.read_stl("part.stl"))  # dict of checks
reg = params.load_register("examples/plate-parameters.csv")
scad.render("examples/two-hole-plate.scad", "out.stl", params.to_openscad_defines(reg))
```

| Module | Main functions |
| --- | --- |
| `calc` | `planar_scale`, `scaled_length`, `scale_report`, `ratio_uncertainty`, `chord_error`, `min_segments`, `chord_report`, `depth_factor`, `depth_factor_range`, `depth_report`, `focal_px_from_35mm`, `camera_distance`, `camera_report`, `aspect_check`, `rounding_uncertainty`, `coating_loss`, `clearance_series`, `gear_pair`, `wind_power`, `wind_report`, `normalize_evidence`, `weakest_evidence`, `suggest_unit_conversion` |
| `homography` | `fit`, `apply`, `residuals`, `jacobian`, `local_scale`, `fit_report`, `jacobi_eigen` |
| `stl` | `read_stl`, `analyze`, `unit_hints`, `write_stl_ascii`, `write_stl_binary`, `box` |
| `params` | `load_register`, `validate`, `values`, `to_openscad_defines`, `Param` |
| `scad` | `find_openscad`, `version`, `format_define`, `render`, `RenderResult` |
| `project` | `new_project`, `slugify`, `FOLDERS`, `PLACEMENT` |
| `routes` | `load_routes`, `recommend`, `all_recommendations` |

Single-number functions are plain formulas. Functions that return a dictionary include a `warnings` list. Warnings never change a result. Invalid input raises `ValueError` with a message. That includes malformed point lists, a homography `at` point beyond the vanishing line, and a result too large to represent, such as a `wind_power` or `ratio_uncertainty` overflow.

## Conventions shared with the browser calculators

The offline page's calculators (`assets/js/cadcalc.js`) follow the same formulas and thresholds, and `tests/node/cadcalc.test.mjs` runs both implementations on the same inputs:

| Rule | Value | Where |
| --- | --- | --- |
| Short reference warning | reference under 200 px | `scale`, `uncertainty` |
| Extrapolation warning | feature longer than 3 × the reference | `scale`, `uncertainty` |
| Large depth correction warning | \|Δ\| / Z over 0.2 | `depth` |
| Excessive segment count warning | more than 720 segments | `chord` |
| Proportion mismatch warning | reference aspect differs by more than 1 % | `aspect` |
| Full-frame diagonal | `hypot(36, 24)` = 43.2666 mm | `camera` |
| Gear undercut limit | `2 / sin²(pressure angle)`, 17.1 teeth at 20° | `gear` |
| Gear pressure angle | strictly between 0° and 90°; other values are rejected | `gear` |
| Betz limit | `Cp` above 16/27 is rejected | `wind` |
| Rotor diameter | zero or negative is rejected | `wind` |
| Overflow | a result too large to represent is rejected, not reported as infinity | `uncertainty`, `wind` |
| Homography query point | finite, and on the control points' side of the plane's vanishing line | `homography` |
| Clearance rounding | values rounded to 1e-6 mm; exact binary ties such as 0.0078125 go to the even digit, as in Python's `round` | `coupon` |

Evidence classes, from strongest to weakest, are `measured`, `image-derived`, `inferred`, and `unknown`. A derived value takes the weakest class among its inputs. Register labels map onto the four classes as follows: `confirmed` counts as measured, `estimated` as image-derived, and `nominal`, `proposed`, and `synthetic` as inferred. Matching ignores case and treats spaces as hyphens. Unrecognized labels raise an error.

`units` considers files authored in mm, cm, m, in, or ft and read as millimetres (factors 1, 10, 1000, 25.4, 304.8). It also considers the reverse mistake: millimetre geometry already scaled up as if it were another unit (factors 1/10 to 1/304.8). Candidates are ranked by relative error against the expected size.

## Mesh-check notes

- Binary STL is recognized by its exact size (`84 + 50 × triangle count`), so a binary file whose header begins with `solid` is still read correctly.
- ASCII STL is read line by line. Each `vertex` line must hold three numbers, and each `facet` … `endfacet` block exactly three vertices. A coordinate that is not a number (`1,5`, `1D+01`), a NaN or infinite coordinate, or a facet with the wrong vertex count is invalid input (exit code 2), and the message names the line. Non-finite coordinates in a binary file are rejected the same way.
- Vertices closer than `--weld-tol` (default 1e-6 file units, straight-line distance) are welded before topology is checked. A spatial hash searches neighbouring cells, so two nearly coincident points are merged even when they straddle a cell boundary. The tolerance must be a positive finite number no larger than 1e100, and large enough that every coordinate divided by it stays finite; `--weld-tol 1e-320` on a 10 mm part is rejected.
- `watertight` means every edge is shared by exactly two faces. `manifold` adds the vertex test: the faces around each vertex must form a single fan, so two shells that touch only at a corner fail even though every edge has two faces. `orientation_consistent` means each shared edge is traversed once in each direction. None of these checks rules out self-intersections.
- `status: pass` (exit code 0) requires a watertight, manifold, consistently oriented mesh with no degenerate triangles. `--allow-open` reports the same result but exits 0.
- Volume uses the divergence theorem about the bounding-box centre. A negative volume indicates inward-facing normals.
- `genus` is reported for closed, manifold, consistently oriented meshes as `(2 × components − χ) / 2`. For a plate it equals the number of through-holes, so the two-hole plate reports 2.
- A triangle is degenerate when fewer than three distinct vertices remain after welding (a collapsed face) or when its area is at most `weld_tol²` (a sliver). Collapsed faces are excluded from the topology checks. Slivers keep three welded vertices, so their edges still count in the edge, vertex, and component checks. Both kinds are counted in `degenerate_triangles` and fail `status`.

## Tests

```bash
python3 -m unittest discover -s tests/python -v
```

Run this from `reference-library`. Tests that render with OpenSCAD are skipped when OpenSCAD is not found. Set `CADKIT_OPENSCAD` to point at a specific executable.
