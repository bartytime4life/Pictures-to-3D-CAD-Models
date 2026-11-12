# Pictures to CAD

Turn a photograph of a **flat, constant-thickness part** into a scaled CAD solid. Review the traced outline beside an interactive 3D model, set scale from a real measurement and enter thickness, then export for your next tool.

The workbench is designed for plates, gaskets, spacers, and templates. It traces what is visible in the photograph; it does not recover hidden geometry or infer physical dimensions.

See [project status and evidence](docs/project-status.md) for the reviewed source
revision, pending changes, completed checks and remaining engineering work.

For reference-sheet tracing, photograph the whole flat sheet (A4, US Letter, or a sheet you have measured) and explicitly choose it as the **Scale reference**. A successful sheet trace sets scale from its stated size, estimates perspective and one radial lens correction, and fits lines, tangent arcs and circles. Entered thickness supports a side-wall/parallax correction under the method's assumptions. Ordinary tracing and the sample use measured-width scaling instead; they do not perform these corrections. See [reference-sheet tracing](docs/reference-sheet.md) for the mathematics and synthetic evidence, and the [engineering model](docs/engineering-model.md) for independent verification before fabrication.

Review the [initial-fit support check](docs/validation/fit-support.md) and
[known benchmark and camera-model limits](docs/validation/scientific-model-review.md)
before relying on small residuals or reported error percentiles. A successful
trace or valid CAD solid still needs comparison with the original outline and
independent dimensions. The [radial-domain and independent-renderer record](docs/validation/radial-inverse.md)
documents numerical safeguards and higher-order lens counterexamples. The
[directional-blur research](docs/validation/directional-spread-qualification.md)
also records missed cases; it does not supply a product accuracy status.

A separate [conditional corner-radius tool](docs/corner-feasibility.md) explores
which radii can explain explicitly bounded observations under a Gaussian model
with fixed or supplied bounded blur, and point or known uniform pixel-aperture
observations. It preserves unresolved regions and can reject an incompatible model;
it does not alter the workbench's trace or qualify a physical radius.

This repository contains two related tools:

| Component | Use it for | Entry point |
| --- | --- | --- |
| Photo-to-CAD workbench | Trace, measure, review, and export a flat part | `make start` after setup |
| Reference library and OpenSCAD workspace | Read the handbook, calculate dimensions, and design parameter-driven mounting plates or fit coupons | **OpenSCAD** in the app header, [offline library](reference-library/index.html), or [its guide](reference-library/README.md) |

![Pictures to CAD workbench showing the traced sample beside its generated CAD solid](docs/images/workbench.png)

Browser-rendered workbench with the demonstration part and its **Next step** guide. The source photo is generated sample imagery; the displayed solid is constructed from its traced outline using demonstration measurements. See the [documentation index](docs/README.md) for task-based navigation.

## Start the app

Use **Python 3.12** (setup finds `python3.12` even when `python3` is another version, or set `PICAD_PYTHON`), Node.js 22.12 or later (24 recommended), npm, and GNU Make. Setup uses [uv](https://docs.astral.sh/uv/) if available, or installs a pinned local copy. From this repository:

```bash
make setup
make start
```

Setup prepares the workbench and reference-library dependencies in separate local environments and builds the workbench interface. Startup runs the API and built interface together. No account, paid API, GPU, or third-party AI credential is required. Setup does not download Ollama models, browsers, OpenSCAD, or system fonts.

For workbench-only setup, use `make setup-app`. The existing `./scripts/setup.sh` and `./scripts/start.sh` commands remain supported and apply only to the workbench.

Open **http://127.0.0.1:8000** on the machine running the server. In a managed cloud environment, use the environment's supported browser or forwarding mechanism. A server running on a remote machine is not your device's localhost.

The app's **OpenSCAD** link opens the companion workspace in a separate tab and keeps the current traced part available. The same server serves the published library at `/reference-library/index.html#cad`; its handbook and browser tools also open offline from `reference-library/index.html`.

For development with frontend hot reload:

```bash
make dev
```

See [development and setup](docs/development.md) for prerequisites, commands, and troubleshooting.

## Bambu Studio and PrusaSlicer

After building, open **Choose an export** or **Review export**, then **Prepare in your slicer**. Choose **Bambu Studio** or **PrusaSlicer** and download a ZIP containing millimeter 3MF geometry, separate split-piece files, the editable recipe, and a hash-verified record of your printer/material plan. Select and review the actual printer, nozzle, filament and process settings in the slicer. Plain 3MF is also available as a regular export.

An optional local launcher can open the current geometry in a configured installed slicer. Run `make slicers` to inspect availability. Targets are Bambu Studio 2.9.1 and the requested PrusaSlicer 2.9.7; executable detection does not verify the installed version. See [slicer setup and use](docs/slicers.md). Setup does not install either application, and the workbench does not slice or start prints.

To check that a separate CAD application reads fitted exports as exact geometry, run `make freecad` with `FREECADCMD` set to FreeCAD's `freecadcmd` (FreeCAD is not installed by setup). It builds the synthetic reference-sheet plate and checks FreeCAD's import of its STEP and DXF against the plate's design; see [validation](docs/validation.md).

## Optional local AI guidance

Open **Local AI assistant** for help with capture, tracing, design changes, print planning, and export choices. Choose an installed Ollama model, ask a question, and review its answer. Suggestions show their proposed settings before an explicit **Apply**, with undo available. You still enter measured dimensions and decide when to build and export.

The assistant uses your question, measurements, trace and design settings, warnings, and built-part dimensions; it does not receive the photograph, outline, or mesh. It runs on the same machine as the CAD backend, with no paid API or cloud-model fallback. The regular CAD workflow works without it.

For the included Linux x86_64 setup:

```bash
./scripts/ollama.sh install
./scripts/ollama.sh serve
```

Keep that terminal running. In another terminal, download the initial small model:

```bash
./scripts/ollama.sh pull qwen3:1.7b
```

Refresh the assistant's connection after the download. This is a provisional CPU-friendly starting model, not a measured quality winner. Check the service and model availability in your own environment; an installed runtime does not establish answer quality. See [local AI setup and controls](docs/ollama.md) and the [model comparison plan](docs/ollama-models.md).

## Try the complete workflow

The **Next step** guide explains the current task and takes you to its controls.
After an edit, **Update preview** rebuilds the model for inspection; **Choose an
export** opens the downloads once that model matches the settings. Missing
measurements and invalid design settings have a direct correction path. The guide is deterministic application state, not AI advice. It describes input and digital-model readiness, not engineering acceptance. The main **Build model** or **Update model** button also builds, then opens the export review; use the guide's preview action when you want to remain beside the model.

1. **Start with the sample.** The supplied demonstration image uses the ordinary outline-tracing and CAD-building pipeline, with 80 mm width and 4 mm thickness supplied for the demonstration. It does not exercise reference-sheet correction.
2. **Choose a photo.** Upload a PNG, JPEG, WebP, HEIC, or AVIF containing one flat part against a contrasting background. Phone photos up to 70 megapixels and 32 MiB are accepted as the camera saved them. For the best result, lay the part on a sheet of paper, photograph the whole sheet, and choose that sheet as the **Scale reference** before uploading.
3. **Review the outline.** Check the boundary and every through-hole. **Trace** or **Adjust outline** opens tracing controls. Ordinary tracing offers automatic/manual contrast and foreground inversion; sheet tracing measures contrast locally and exposes design-intent snapping instead. Read the trace notes before applying the result.
4. **Set the dimensions.** With a reference sheet, the width comes from the sheet; measure the part's width as an independent check. Otherwise enter the measured outside width, or open **Use a known feature**, mark two endpoints, enter their real separation, and apply the scale. Enter measured thickness separately; with a sheet and the photo still available, building re-traces when thickness changes to apply the side-wall/parallax correction. Use the optional **Independent height check** to compare another measurement before design resizing. Enter an allowed deviation and a justified measurement error bound for a conditional within/outside/inconclusive decision; [engineering model and verification](docs/engineering-model.md) explains its mathematics and limits.
5. **Choose design and print settings.** Keep the measured size or set explicit XY and thickness scales, preview a color and material, choose a printer or custom volume, and decide whether to keep one piece or generate straight-cut parts.
6. **Inspect and export.** Rotate the model, compare it with the photograph, and use **Create preview** or **Update preview** in the guide to inspect a fresh build. Review each piece's geometric bed fit, then choose **Choose an export** or **Review export**. A previous model is retained after editable changes, but its geometry cannot be downloaded as though it represented those changes.

The sample's dimensions are demonstration inputs, not measurements recovered from the photograph. Measure your own part before using its output.

Design scales preserve those source measurements: an 80 mm reference width at 125% requests a 100 mm design, while the entered reference remains 80 mm. Thickness scale is separate. Geometry-detail approximation may alter the resulting outline, so check the built dimensions. Color and material affect the approximate preview and saved plan; they do not simulate strength or select a filament spool.

Printer fit searches all in-plane rotations of each built polygon on a clear rectangular bed. Open a part's fit result to see the suggested counterclockwise turn and rotated footprint. Fitted curves use a conservative enclosing rectangle or an outer enclosure built from exact curve supports; inconclusive checks ask for slicer review. Suggested turns are saved in handoff manifests and are not applied to geometry exports. Review supports, adhesion, machine clearances, and material behavior in your slicer. See [print planning](docs/print-planning.md).

When a built polygon part exceeds the selected bed, **Design & print** can suggest a supported straight-cut grid with the fewest fitting pieces. **Use suggested split** changes the cut settings; **Update preview** generates pieces for inspection, or **Update model** builds and opens export review. Your measured size stays the same. The search considers up to four rows and columns, with at most eight cells and actual pieces; it checks each piece separately and adds no joints or assembly clearance.

The bundled searchable [printer catalog](docs/printer-catalog.md) covers 429 model groups across 70 manufacturer/profile families, with nozzle-specific source profiles and links. It works offline. Hardware capabilities absent from those sources are shown as unknown; custom printer dimensions remain available.

## What you can export

The export dialog shows **CAD & 3D printing** downloads first. Expand **Drawings &
source files** for DXF, SVG, PDF, and OpenSCAD.

| Format | Use it for | What it preserves |
| --- | --- | --- |
| STEP | Opening solids in CAD software | Solid geometry in assembled positions; a fitted reference-sheet outline has true cylindrical faces for its arcs and circles; not the original feature history |
| STL | Slicing or mesh workflows | Triangle surfaces in assembled positions; millimeter coordinates, no color |
| 3MF | Importing geometry into a slicer | Millimetre units and separate mesh objects in assembled positions |
| DXF | A flat profile for a CAD or CAM workflow | The planar boundary and holes; `LINE`, `ARC` and `CIRCLE` entities for a fitted outline |
| SVG | A laser cutter's software or a vector editor | The same planar boundary and holes at one unit per millimetre; arcs and circles for a fitted outline |
| PDF | Printing the outline at 1:1 to lay the real part on | The outline and holes at true size on a page that fits A4 and US Letter, a 100 mm ruler along each axis to check the print, and a centre mark in each round hole |
| OpenSCAD | Editing the built profile in scripted CAD | Final scaled profile, holes, thickness, and selectable split pieces in assembled positions; fitted circles stay `circle()` calls and non-circular fitted arcs are sampled into polygons |
| Parts ZIP | Importing generated pieces separately | A STEP, STL and 3MF per piece, plus a manifest |
| Slicer handoff ZIP | Preparing a Bambu Studio or PrusaSlicer import | Geometry, split pieces, recipe, printer/material planning notes, instructions and payload hashes |
| Save project JSON | Restoring the workbench settings and browser measurement notes | Outline, source measurements, optional endpoint reference and independent-height decision inputs, and design/print settings. The browser saves version 3 for fitted/reference-sheet profiles and version 2 for ordinary polygons; version 1 imports remain supported. Photos are excluded |

To measure the reference-sheet tracer on your own photos, run `make photo-benchmark PHOTOS=folder` on a folder of photos and the dimensions you measured with calipers. It reports each dimension's error and its spread between repeat shots; see [the photo benchmark](docs/photo-benchmark.md). No result from real photos is recorded yet.

Use the browser's **Save project** or **Save editable project recipe** to retain known-feature endpoints, independent height and height-decision inputs. The backend recipe inside a slicer handoff preserves geometry/build settings and reference-sheet evidence, but does not include those browser-only measurement notes. Save both when you need both. See [export formats and dimensional checks](docs/exports.md) before transferring a part to fabrication software.

OpenSCAD source export works without installing OpenSCAD. Open the downloaded `.scad` in OpenSCAD to edit its thickness, apply an additional XY scale, or select a split piece. Ordinary and split outlines use polygon extrusions; a fitted single-part export retains circle primitives and samples other fitted arcs. Neither route recovers the original CAD constraints or feature history. For a new plate with deliberately dimensioned holes, use the companion [OpenSCAD workspace](reference-library/index.html#cad) and its [native build guide](reference-library/OPENSCAD.md).

## Honest limits

- A single image supplies a 2D outline. Thickness is entered by the user; recesses, sloped walls, threads, and hidden features are not reconstructed.
- One outside width or two-point reference sets uniform scale. It does not correct perspective, lens distortion, or an out-of-plane part. A reference sheet estimates perspective and one radial lens coefficient in the sheet's plane, and the parallax of a vertical-walled part of the entered thickness. Its edges are measured in linear light, decoding the photo as sRGB. The second edge pass follows a locally linear paper-side shadow slope; nonlinear shadows and a camera's own tone mapping remain limits. Near-frontal camera height can be inferred from suitable holes assumed round; without that evidence or EXIF, an assumed lens remains necessary. The recorded errors come from rendered photographs with exact ground truth. [The photo benchmark](docs/photo-benchmark.md) measures real photos against calipers, and no such result is recorded yet.
- A reference sheet's stated size sets the scale. The workbench checks the sheet's proportions against the photo, but not its absolute size: measure your sheet.
- Tracing approximates pixel boundaries. Smooth-looking geometry is not evidence of manufacturing accuracy. Sharp-corner radius notes describe resolution under an assumed blur model; measure small fillets that matter for fit.
- Relative detail can simplify the CAD outline; it does not recover missing image detail or establish a minimum printable wall thickness.
- Split exports use straight cuts without joinery, kerf, or assembly tolerances. Combined STEP/STL/3MF exports show the assembled geometry, not separated parts arranged on a print bed.
- The browser sends images to the app's backend. On a cloud host, that means uploading to that host; processing is not browser-only.
- This release is a single-user workbench, not a hosted account or collaboration service.

## Documentation

Start with the [documentation index](docs/README.md) for capture, engineering, export, development and evidence routes.

- [Capture and calibration guide](docs/capture-guide.md)
- [Engineering model and independent verification](docs/engineering-model.md)
- [Reference-sheet tracing: method, mathematics and evidence](docs/reference-sheet.md)
- [Photo benchmark: your photos against your calipers](docs/photo-benchmark.md)
- [Export formats](docs/exports.md)
- [Print planning, materials, and split parts](docs/print-planning.md)
- [Printer catalog, provenance, and updates](docs/printer-catalog.md)
- [Development and setup](docs/development.md)
- [Optional local AI: setup and controls](docs/ollama.md)
- [Local model choices and comparison](docs/ollama-models.md)
- [Architecture and API](docs/architecture.md)
- [API examples and error recovery](docs/api-examples.md)
- [Project status and evidence](docs/project-status.md)
- [Data handling and security boundaries](docs/privacy-security.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Research and design decisions](docs/research.md)
- [Scope and roadmap](docs/roadmap.md)
- [Validation results](docs/validation.md)
- [Guided workbench review](docs/validation/guided-workbench.md)
- [Visual QA history and review index](design-qa.md)

## Reference library

Revision 7 adds an editable OpenSCAD workspace for mounting plates and fit coupons, with SCAD/CSV/SVG downloads, saved browser drafts, and checked native build records. The library retains 88 annotated sources, independent measurement worksheets, and portable photo backup/restore.

[`reference-library/`](reference-library/README.md) is the companion reference for work beyond one flat part. Open `reference-library/index.html` in a browser; it works offline. It covers:

- **Handbook:** 23 chapters on capture, scale and calibration, reconstruction workflows, CAD drawings, print design, and validation
- **Source catalog:** 88 annotated sources, each labeled with its depth of review
- **Toolkit:** 14 calculators and a route finder, with the same arithmetic available as `python3 -m cadkit` from the `reference-library/` directory
- **Photos:** an offline reference-photo workspace. Add photos in batches, label viewpoints, keep notes, and estimate a flat dimension from a known length. Protect unsaved edits, back up originals and notes to a folder, restore a reference set, and export image-derived measurements. Photos stay in that browser's local storage and are separate from the workbench's uploads.
- **OpenSCAD:** parameter-driven mounting plates and clearance coupons, live dimensional drawings, evidence notes, saved drafts, and downloadable SCAD/CSV/SVG files. The local `cadkit openscad` commands render and independently check native meshes, preserve build provenance, and keep earlier exports after a failed build. See [OpenSCAD instructions](reference-library/OPENSCAD.md).
- **Worksheets and examples:** project worksheets and an OpenSCAD example pipeline
- **Mesh check for workbench exports:** `python3 -m cadkit meshcheck model.stl --expect-mm 80` independently checks an exported STL for closure, manifoldness, and orientation, and reports its genus (through-holes) for comparison with the workbench's hole count. See [export checks](docs/exports.md#check-an-stl-independently).

The root `make build-library` and `make test-library` commands operate on this component. Its own Makefile and [CI workflow](.github/workflows/reference-library.yml) remain available. See [its README](reference-library/README.md) and [verification record](reference-library/VERIFICATION.md).

Photos and saved browser drafts belong to that browser and page origin. Opening the served library does not automatically import data saved while using its offline file. Use the Photos backup/restore tools and download CAD parameters before moving between browsers or page addresses.

## Checks

From the repository root:

```bash
make test
make lint
```

`make test` runs the workbench's Python tests, frontend type check/build, and browser scenarios, followed by the reference library's Python/Node tests and its browser checks (the page, Photos workspace, portable backup/restore, and OpenSCAD workspace) over loopback HTTP, plus native OpenSCAD checks when available. `make lint` runs the workbench Python and frontend/browser-source lint/format checks. Use `make test-app` or `make test-library` to work on one component; `make` lists the available commands.

Browser checks use an installed Chromium or Google Chrome; if neither is available, run `npx playwright install chromium`. Native OpenSCAD checks may skip when OpenSCAD is absent; `make setup` does not install it. Those skips do not validate native rendering. See [development prerequisites](docs/development.md) for browser, PDF/font, and OpenSCAD requirements. The [validation report](docs/validation.md) distinguishes recorded successful runs from checks that have not yet run. A successful synthetic fixture does not establish dimensional accuracy for an arbitrary real-world photograph.

Separate GitHub Actions workflows validate the [workbench](.github/workflows/ci.yml) and [reference library](.github/workflows/reference-library.yml). Recorded results apply to their stated commits; see the validation report for execution evidence.

## License

[MIT](LICENSE). Dependencies retain their own licenses. Bundled printer-profile data has its own [source attribution and license record](data/PRINTER_SOURCES.md). The demonstration photograph is generated example content, not a certified reference object.
