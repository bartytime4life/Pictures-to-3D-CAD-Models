# Bambu Studio, PrusaSlicer, QIDI Studio, OrcaSlicer and UltiMaker Cura

The workbench prepares a built part for five slicers. Use **Prepare for slicing** above the workbench to edit the process plan and inspect each built piece on the rectangular bed envelope. Rebuild after changes, then choose **Review slicer handoff**. You can also open **Review export → Prepare in your slicer**, choose **Bambu Studio**, **PrusaSlicer**, **QIDI Studio**, **OrcaSlicer** or **UltiMaker Cura**, and download the handoff ZIP. The integration targets **Bambu Studio 2.9.1**, the requested **PrusaSlicer 2.9.7**, **QIDI Studio 2.07.02.73** (shown as 2.7.2.73), **OrcaSlicer 2.5.1** and **UltiMaker Cura 5.14.0**. These are target releases, not a claim about the installed program.

## Take the current part into a slicer

1. Review the model's dimensions, holes and design settings, then build it. Geometry changes require a fresh build before exporting.
2. Open **Choose an export** or **Review export**, choose your slicer and download its handoff ZIP. Plain **3MF**, STEP and STL are under **CAD & 3D printing**; DXF, SVG, PDF and OpenSCAD are under **Drawings & source files**.
3. Extract the ZIP and import `model.3mf` into your slicer as geometry. Coordinates are millimetres. If the slicer asks whether to import another application's project settings, choose geometry only.
4. For split output, use the individual `part-XX.3mf` files when arranging separate pieces. They start at XY zero with their bottom at Z zero. The combined `model.3mf` retains the assembly's coordinates with separate objects; touching split faces are not an arranged printing plate. STL alternatives are included.
5. Select the exact printer, nozzle, build plate and filament inside the slicer. Review `process-plan.json` and enter its planned layer height, wall count, infill, support placement and adhesion in the native process settings. Arrange the pieces, check dimensions and fine features, review supports and orientation, slice, and inspect the layer preview. Save the native slicer project there to retain its reviewed settings.

The ZIP contains the geometry, editable workbench recipe, `process-plan.json`, instructions and `manifest.json`. The manifest records built dimensions, part positions, the resolved printer/material/process plan and SHA-256 hashes. It does not include the original photograph. Printer, nozzle, material, preview color and process settings remain planning notes; they do not install a native preset, assign filament or create supports, infill, walls or a raft in the geometry.

## Plan the slicing process

**Prepare for slicing** stores layer height (0.05–1.2 mm, no larger than the chosen nozzle), wall count (1–12), infill (0–100%), supports (none, build plate only or everywhere), and adhesion (none, brim or raft). These are a starting plan to review against the exact native printer and material profile. They do not predict quality, strength, print duration or material consumption. **Quick prototype**, **Everyday** and **Fine surface** supply editable starting points; compare the chosen values with the native profile before printing.

The bed inspection rotates the current piece's mesh over the rectangular margin envelope. **Preview turn**, **Grid**, **Margin**, **Dimensions** and **Reset view** only change that inspection. The saved geometric fit result remains separate, and exported orientation stays unchanged. A suggested turn is available after a supported positive fit; other pieces return to their original angle. See the [science guide](science.md#bed-containment-and-orientation).

Older recipes without process fields open with 0.2 mm layers, three walls, 15% infill, no supports and no added adhesion. For a nozzle smaller than 0.2 mm, the missing layer-height default is capped at that nozzle diameter. An explicitly supplied layer height larger than the nozzle is rejected. Changing the process plan does not alter the modeled solid; rebuilding binds the new plan to the exported recipe and handoff package.

The ZIP's server-generated recipe preserves the source profile, size and design,
including sheet/fitted data when present. Browser-held known-feature endpoints,
independent height and height-decision inputs stay in the browser-saved recipe.
Use **Save project** or **Download recipe** from a saved snapshot to keep those
notes. Print attempts are recorded on the snapshot. See [recipe contents](exports.md#project-json-the-workbench-recipe)
and the [Project library workflow](workflows.md#save-snapshots-and-record-prints).

The standards-based 3MF includes millimetre units, separate mesh objects and their positions. It contains no printer settings, temperatures, AMS/MMU assignments, painting, supports or machine instructions. A slicer project saved by any of these applications can carry application-specific settings beyond this interchange geometry.

## Open an installed slicer directly

Direct opening is an optional feature for a workbench running on your own computer. The download workflow works independently.

Install the intended official program, check its version in the application's About screen, and configure the workbench's local launcher before starting the server:

```bash
export PICAD_ENABLE_SLICER_LAUNCH=1
export PICAD_BAMBU_STUDIO='/absolute/path/to/BambuStudio'
export PICAD_PRUSA_SLICER='/absolute/path/to/prusa-slicer'
export PICAD_QIDI_STUDIO="$HOME/Applications/QIDIStudio_v02.07.02.73_Ubuntu24.AppImage"
export PICAD_ORCA_SLICER='/absolute/path/to/OrcaSlicer'
export PICAD_CURA='/absolute/path/to/UltiMaker-Cura'
make start
```

Set only the program paths you use. Each variable must contain one absolute executable path, including an AppImage if applicable. Arguments and shell commands are not accepted. Standard executable names on `PATH` (`bambu-studio`, `prusa-slicer`, `qidi-studio`) and usual macOS/Windows application locations are also checked.

OrcaSlicer additionally checks `orca-slicer`, `OrcaSlicer` and `orcaslicer` on `PATH`, plus executable `OrcaSlicer_*.AppImage` files in `~/Applications`. Cura checks `cura`, `UltiMaker-Cura` and `ultimaker-cura`, plus `UltiMaker-Cura-*.AppImage` there. The explicit environment path is the dependable option for nonstandard, versioned or platform-specific installations. The new Windows/macOS path candidates have not been verified against installed applications.

On Linux, an executable AppImage kept in `~/Applications` is found without any setting: `Bambu_Studio_*.AppImage`, `PrusaSlicer-*.AppImage` or `QIDIStudio_*.AppImage`. With several, the last by name is used; QIDI and Bambu pad their version numbers, so that is the newest. Downloads and the desktop are deliberately not searched, so a file that merely arrives there is never started. To use an AppImage kept elsewhere, set its variable. The QIDI Studio macOS location is taken from its source (`QIDIStudio.app/Contents/MacOS/QIDIStudio`). Its Windows folder (`QIDIStudio\qidi-studio.exe` under Program Files) has not been checked against an installer, so on Windows set `PICAD_QIDI_STUDIO` if it is not found.

Run `make slicers` for a read-only availability check. `GET /api/slicers` performs the same check without starting any program. **Executable found** does not mean its installed version has been verified. The interface labels that distinction explicitly.

When an installed program and the launcher are available, choose the selected program's **Open in…** button. All five registered slicers use this explicit action to request GUI opening with the current 3MF. The server accepts it only from a same-origin JSON request over HTTP on loopback. HTTPS loopback and remote workbenches use the ZIP download workflow; open the extracted geometry in the intended installed slicer.

The launcher keeps a local copy under `.local/slicer-handoffs/<id>/`, so closing the workbench or clearing temporary model exports cannot remove the file while the slicer imports it. These copies remain until you remove them yourself. `PICAD_SLICER_HANDOFF_DIR` selects another server-side folder. Launch failures retain a prepared copy when one was created. A successful request means a process was started; check the slicer's window to verify import. The workbench does not automate slicing or contact a printer.

## Official installation sources

- [Bambu Studio 2.9.1](https://github.com/bambulab/BambuStudio/releases/tag/v02.09.01.70) provides official platform downloads. The [project repository](https://github.com/bambulab/BambuStudio) links its documentation and supported distributions.
- [PrusaSlicer 2.9.7](https://github.com/prusa3d/PrusaSlicer/releases/tag/version_2.9.7) is the requested release. Its [release assets](https://github.com/prusa3d/PrusaSlicer/releases/expanded_assets/version_2.9.7), checked November 9, 2026, list Windows and macOS binaries and source archives; that release page supplies no Linux binary. This integration does not silently install another version or invent a Linux download URL. Use an official distribution matching the intended release when available and verify its version locally.
- [QIDI Studio 2.07.02.73](https://github.com/QIDITECH/QIDIStudio/releases/tag/v2.07.02.73) (AGPL-3.0), released October 19, 2026, provides Windows, macOS and Ubuntu 22/24 AppImage downloads from its [project repository](https://github.com/QIDITECH/QIDIStudio). GitHub publishes each asset's SHA-256; check a download with `sha256sum`. The Ubuntu 24 AppImage is `b0f39d5f11a3ccae0d353c19ce17e4822c7e18beb4c0432a6994737c18a276f8`, 127,400,440 bytes. QIDI Studio is derived from Bambu Studio and opens standard 3MF geometry.
- [OrcaSlicer 2.5.1](https://github.com/OrcaSlicer/OrcaSlicer/releases/tag/v2.5.1) is the new Orca target, checked November 16, 2026 against the official release page. Its release includes Linux AppImage, Windows and macOS downloads. This integration has not verified native import or slicing in OrcaSlicer.
- [UltiMaker Cura 5.14.0](https://github.com/Ultimaker/Cura/releases/tag/5.14.0) is the new Cura target, checked November 16, 2026 against the official release page. Its [release assets](https://github.com/Ultimaker/Cura/releases/expanded_assets/5.14.0) include Linux AppImage, Windows and macOS downloads. Import the handoff as geometry, not as a Cura project with settings. Native import and slicing remain unverified.

No program is bundled, downloaded, installed or upgraded by `make setup`. A stale desktop shortcut or a differently named download does not establish that the target release is installed. Installation and native import are separate from the geometry and handoff checks below.

## What is checked

Tests independently read the 3MF package and XML, inspect object/build references, and check each object's millimetre bounds, closed and consistently oriented mesh, hole topology and volume against the built solid. Indexed vertices are deduplicated within each object, keeping split objects separate. The handoff tests verify every archived payload hash, intended settings, file references and normalized part positions. Browser tests exercise real downloads, program selection, missing-program states, explicit launch requests, stale-result protection and mobile accessibility. Launcher tests use mocks; they do not start a slicer window.

### Recorded QIDI Studio import checks

When QIDI Studio is installed, `tests/test_qidi_import.py` runs the real program's command line, `--info`, which loads a model the way the program does and reports each object's size, volume, facet count and whether it is manifold. An AppImage runs unpacked (`APPIMAGE_EXTRACT_AND_RUN=1`), so the check also works where FUSE mounting is unavailable. The tests skip when QIDI Studio is not found. With QIDI Studio 2.07.02.73 (the official Ubuntu 24 AppImage, hash above), all three checks passed:

- **Single part:** the handoff ZIP's `model.3mf` and its `model.stl` fallback import as one manifold object at the built size, with QIDI's volume equal to the built solid's.
- **Split into two pieces:** the combined `model.3mf` imports as two separate manifold objects, each at its piece's built size, with volumes summing to the whole; each `part-XX.3mf` imports at its piece's size. QIDI reports every object about its own centre, so positions are covered by the 3MF writer's own tests.
- **Relief:** the moon relief's 3MF imports manifold at 100 mm wide and 4 mm thick, with exactly as many facets as the app wrote (361,136).

These checks establish the exported geometry, QIDI Studio's import of it, and the integration behavior. Native Bambu Studio, PrusaSlicer, OrcaSlicer and Cura imports, slicing in any of the five, physical fit and printing remain unverified until performed with the actual programs, printer and material.

## Reference material

- [Bambu Studio command-line usage](https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage) documents opening 3MF/STL and the full configurations needed for automated slicing.
- [QIDI Studio command line](https://github.com/QIDITECH/QIDIStudio/blob/v2.07.02.73/src/QIDIStudio.cpp) defines `--info`, which the import tests use; run the program with `--help` to list its options.
- [PrusaSlicer supported formats](https://help.prusa3d.com/article/supported-file-formats_1772) covers geometry import. STEP is triangulated when imported.
- [PrusaSlicer 2.9.7 CLI actions](https://github.com/prusa3d/PrusaSlicer/blob/version_2.9.7/src/CLI/ProcessActions.cpp) distinguish geometry export from resolved slicing configuration. The workbench uses GUI handoff without slicing actions or user-supplied post-processing scripts.
- [3MF Core specification](https://github.com/3MFConsortium/spec_core/blob/master/3MF%20Core%20Specification.md) defines the package, units and mesh representation used by the geometry exporter.
