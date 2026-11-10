# OpenSCAD in this project

OpenSCAD owns the repeatable mechanical parts of the photo-to-CAD workflow: measured outlines, mounting holes, and fit-test coupons. Photographs supply reference information; reviewed dimensions drive the CAD. Character surfaces and organic reconstruction still need a mesh or sculpting workflow.

## Start in the browser

Open [the library's OpenSCAD tab](index.html#cad). Choose a **two-hole mounting plate** or a **diametral clearance coupon**, then adjust its dimensions. The live drawing is a dimensional sketch; OpenSCAD produces the actual solid.

1. Start with the synthetic defaults, or replace each governing value with a reviewed dimension. Keep its evidence class and source. An image-derived estimate stays image-derived until independent evidence supports a different classification.
2. Resolve any wall, hole-spacing, tessellation, or notch errors. Downloads are unavailable while the configuration is invalid.
3. Download the **OpenSCAD file** and **parameter CSV**. Download the SVG if you want a dimensional reference drawing. An SVG viewer may scale its display; use the written dimensions, not an on-screen ruler.
4. Open the `.scad` file in OpenSCAD. Adjust literal parameters in its Customizer if needed. Press **F5** to preview, **F6** to render, inspect the console, and choose **File → Export → Export as STL**.
5. Treat a changed Customizer configuration as a new parameter revision. Update the parameter CSV before using the checked build below; the build reads the CSV, not unsaved GUI edits or a separate Customizer preset.

The browser writes files only through explicit downloads. It does not install software or launch a native application. The native renderer runs through OpenSCAD itself or the command below. There is no server upload or cloud conversion.

## Build and verify locally

Run from the `reference-library` directory:

```bash
python3 -m cadkit openscad doctor
```

The executable is discovered on `PATH`, or selected with `CADKIT_OPENSCAD`. This project was tested with the installed **OpenSCAD 2021.01** on November 9, 2026. The doctor checks the executable and version; it is not a printer qualification.

Move the downloaded plate CSV into this directory, or supply its full path:

```bash
python3 -m cadkit openscad build --model plate --params plate-parameters.csv --output-dir output/my-plate-01 --preview
```

For the coupon:

```bash
python3 -m cadkit openscad build --model coupon --params coupon-parameters.csv --output-dir output/my-coupon-01 --preview
```

Omit `--params` to use the explicitly synthetic teaching defaults. `--preview` creates a real OpenSCAD PNG; on headless Linux it needs `xvfb-run`. Omit that flag to build just the STL and records. Use `--json` for a complete machine-readable result.

Choose a **new output directory for every build**. Existing directories are refused. A failed render, failed geometry check, or failed requested preview never replaces an earlier build. No automatic cleanup removes successful builds.

Personal build directories under `output/` are excluded from the portable library archive. The bundled `examples/openscad-starter/` builds contain only synthetic defaults.

| Output | Purpose |
| --- | --- |
| `source.scad` | Self-contained mechanical source with the effective values |
| `parameters.csv` | Input register, including evidence, units, and source/rationale |
| `model.stl` | Binary STL; this workflow declares its coordinates to be millimetres |
| `preview.png` | Optional rendered view of this exact build |
| `validation-results.csv` | Expected and actual mesh checks, with tolerances |
| `build.json` | Complete input/output hashes, model revision, parameters, versions, command, checks, and scope |
| `render.log`, `preview.log` | OpenSCAD diagnostics; preview log exists only when requested |

The build accepts the selected model's numeric parameters only. Unknown fields, blank required values, invalid units, missing rationale, or unsupported ranges are rejected before rendering. Millimetres are required for lengths; counts use unit `1`. There is no implicit inch conversion. The CSV is the governing source for this build; the library's built-in model template supplies geometry.

## The two parts

**Mounting plate.** Overall length, width, thickness, hole diameter and centre spacing are editable. The minimum-wall rule checks the end walls, side walls and web between holes. Hole polygons are inscribed, matching the handbook's tessellation example: the clear opening across polygon flats is slightly smaller than the vertex-circle diameter. The drawing shows nominal circles. Do not assume a tight fastener fit from the nominal diameter.

**Clearance coupon.** The first hole near the corner notch has the smallest diametral clearance: `hole diameter − nominal pin diameter`. The hole series increments by the chosen step. Polygon radii are enlarged so their flats preserve the requested nominal opening. The browser/CLI version uses no text labels, keeps the index notch, and enables polygon compensation. Use the SVG/CSV to identify the series. Print using the intended material, orientation, layer settings and finish, and test with the real pin.

Both models limit tessellation to 720 segments per hole; the coupon accepts 1–100 holes. These are computational bounds, not manufacturing recommendations.

## Ready-to-inspect synthetic builds

The following are actual default OpenSCAD outputs, kept with their parameter and verification records:

- **Plate:** [source](examples/openscad-starter/plate/source.scad), [STL](examples/openscad-starter/plate/model.stl), [render](examples/openscad-starter/plate/preview.png), [build record](examples/openscad-starter/plate/build.json).
- **Coupon:** [source](examples/openscad-starter/coupon/source.scad), [STL](examples/openscad-starter/coupon/model.stl), [render](examples/openscad-starter/coupon/preview.png), [build record](examples/openscad-starter/coupon/build.json).

The local checker reads the actual STL and checks extents, polygon-volume expectation, closedness, orientation, components, non-manifold edges and vertices, degeneracy, number of through-holes, and each hole's ring vertices and radius. The revision hash covers the complete template, parameter CSV and shared schema. Output hashes let another person check that the files still match the receipt.

Passing establishes agreement with the stated geometry. **No real object was measured, no model was sliced or printed, and physical fit, strength and print quality remain untested.** The synthetic defaults are examples, not accepted dimensions for a personal project.

## Sources and implementation

- [OpenSCAD documentation](https://openscad.org/documentation.html) links the official project to its user manual.
- [Customizer syntax](https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Customizer): literal parameters, groups, ranges and presets. The bridge uses literal values and avoids mixing `-p/-P` presets with conflicting `-D` values.
- [OpenSCAD CLI manual source](https://github.com/openscad/openscad/blob/master/doc/openscad.1.in): output formats, parameter overrides, and rendered PNGs. Development documentation can differ from an installed release; check the installed executable.
- [User interface](https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/The_OpenSCAD_User_Interface): preview and full render.
- [STL export](https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/STL_Import_and_Export): export workflow and geometry considerations.

`assets/data/openscad-models.json` supplies model parameters to both browser and Python. `cad-models.js` prepares downloads and drawings; `cadkit/openscad.py` builds and independently checks the mesh. `cadkit/scad.py` stages individual renders and atomically replaces the destination only on success. No new runtime dependency is needed for STL builds beyond the existing OpenSCAD executable.
