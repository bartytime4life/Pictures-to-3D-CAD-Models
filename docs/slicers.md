# Bambu Studio and PrusaSlicer

The workbench prepares a built part for either slicer. Open **Review export → Prepare in your slicer**, choose **Bambu Studio** or **PrusaSlicer**, and download the handoff ZIP. The current integration targets **Bambu Studio 2.9.1** and the requested **PrusaSlicer 2.9.7**. These are target releases, not a claim about the installed program.

## Take the current part into a slicer

1. Review the model's dimensions, holes and design settings, then build it. Geometry changes require a fresh build before exporting.
2. Open **Choose an export** or **Review export**, choose your slicer and download its handoff ZIP. Plain **3MF**, STEP and STL are under **CAD & 3D printing**; DXF, SVG, PDF and OpenSCAD are under **Drawings & source files**.
3. Extract the ZIP and import `model.3mf` into your slicer as geometry. Coordinates are millimetres. If the slicer asks whether to import another application's project settings, choose geometry only.
4. For split output, use the individual `part-XX.3mf` files when arranging separate pieces. They start at XY zero with their bottom at Z zero. The combined `model.3mf` retains the assembly's coordinates with separate objects; touching split faces are not an arranged printing plate. STL alternatives are included.
5. Select the exact printer, nozzle, build plate, filament and process settings inside the slicer. Arrange the pieces, check dimensions and fine features, review supports and orientation, slice, and inspect the layer preview. Save the native slicer project there to retain its reviewed settings.

Check fit-critical fitted radii, hole positions and arc/line joins in STEP or
DXF before slicing; [the curve-check guide](exports.md#verify-critical-arc-geometry)
describes the remaining export limitation and recovery path. A successful mesh
import or geometric bed-fit result does not establish those dimensions.

The ZIP contains the geometry, editable workbench recipe, instructions and `manifest.json`. The manifest records built dimensions, part positions, the resolved printer/material plan and SHA-256 hashes. It does not include the original photograph. Its printer ID, nozzle, material and preview color remain planning notes; they do not install a native preset or assign filament.

The ZIP's server-generated recipe preserves the source profile, size and design,
including sheet/fitted data when present. Browser-held known-feature endpoints,
independent height and height-decision inputs are not sent to that recipe. Use
**Save project** as a separate download to keep those optional measurement notes;
see [recipe contents](exports.md#project-json-the-workbench-recipe).

The standards-based 3MF includes millimetre units, separate mesh objects and their positions. It contains no printer settings, temperatures, AMS/MMU assignments, painting, supports or machine instructions. A slicer project saved by either application can carry application-specific settings beyond this interchange geometry.

## Open an installed slicer directly

Direct opening is an optional feature for a workbench running on your own computer. The download workflow works independently.

Install the intended official program, check its version in the application's About screen, and configure the workbench's local launcher before starting the server:

```bash
export PICAD_ENABLE_SLICER_LAUNCH=1
export PICAD_BAMBU_STUDIO='/absolute/path/to/BambuStudio'
export PICAD_PRUSA_SLICER='/absolute/path/to/prusa-slicer'
make start
```

Set only the program paths you use. Each variable must contain one absolute executable path, including an AppImage if applicable. Arguments and shell commands are not accepted. Standard executable names on `PATH` and usual macOS/Windows application locations are also checked.

Run `make slicers` for a read-only availability check. `GET /api/slicers` performs the same check without starting either program. **Executable found** does not mean its installed version has been verified. The interface labels that distinction explicitly.

When an installed program and the launcher are available, choose **Open in Bambu Studio** or **Open in PrusaSlicer**. This explicit action requests GUI opening with the current 3MF. The server accepts it only from a same-origin JSON request on loopback. A remote browser connected to a hosted workbench should download the ZIP and open its own installed slicer.

The launcher keeps a local copy under `.local/slicer-handoffs/<id>/`, so closing the workbench or clearing temporary model exports cannot remove the file while the slicer imports it. These copies remain until you remove them yourself. `PICAD_SLICER_HANDOFF_DIR` selects another server-side folder. Launch failures retain a prepared copy when one was created. A successful request means a process was started; check the slicer's window to verify import. The workbench does not automate slicing or contact a printer.

## Official installation sources

- [Bambu Studio 2.9.1](https://github.com/bambulab/BambuStudio/releases/tag/v02.09.01.70) provides official platform downloads. The [project repository](https://github.com/bambulab/BambuStudio) links its documentation and supported distributions.
- [PrusaSlicer 2.9.7](https://github.com/prusa3d/PrusaSlicer/releases/tag/version_2.9.7) is the requested release. Its [release assets](https://github.com/prusa3d/PrusaSlicer/releases/expanded_assets/version_2.9.7), checked November 9, 2026, list Windows and macOS binaries and source archives; that release page supplies no Linux binary. This integration does not silently install another version or invent a Linux download URL. Use an official distribution matching the intended release when available and verify its version locally.

Neither program is bundled, downloaded, installed or upgraded by `make setup`. A stale desktop shortcut or a differently named download does not establish that the target release is installed. Installation and native import are separate from the geometry and handoff checks below.

## What is checked

Tests independently read the 3MF package and XML, inspect object/build references, and check each object's millimetre bounds, closed and consistently oriented mesh, hole topology and volume against the built solid. Indexed vertices are deduplicated within each object, keeping split objects separate. The handoff tests verify every archived payload hash, intended settings, file references and normalized part positions. Browser tests exercise real downloads, program selection, missing-program states, explicit launch requests, stale-result protection and mobile accessibility. Launcher tests use mocks; they do not run installed slicers.

These checks establish the exported geometry and integration behavior. Native Bambu Studio and PrusaSlicer imports, slicing, physical fit and printing remain unverified until performed with the actual programs, printer and material.

## Reference material

- [Bambu Studio command-line usage](https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage) documents opening 3MF/STL and the full configurations needed for automated slicing.
- [PrusaSlicer supported formats](https://help.prusa3d.com/article/supported-file-formats_1772) covers geometry import. STEP is triangulated when imported.
- [PrusaSlicer 2.9.7 CLI actions](https://github.com/prusa3d/PrusaSlicer/blob/version_2.9.7/src/CLI/ProcessActions.cpp) distinguish geometry export from resolved slicing configuration. The workbench uses GUI handoff without slicing actions or user-supplied post-processing scripts.
- [3MF Core specification](https://github.com/3MFConsortium/spec_core/blob/master/3MF%20Core%20Specification.md) defines the package, units and mesh representation used by the geometry exporter.
