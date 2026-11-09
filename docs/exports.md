# Export formats and dimensional checks

Choose the output according to the receiving tool. All generated geometry uses **millimeters internally**. Confirm the receiving program's import settings rather than relying on a file extension to establish units.

## STEP: CAD solids

Use STEP when continuing in a solid-modeling CAD application. The file contains the generated boundary representation of the extruded part and its through-holes. In split mode, the combined file contains the generated pieces in their assembled positions.

STEP does not carry this application's original editable feature history. The receiving tool may support direct edits, but that is different from recovering a named sketch, constraints, or an extrusion feature. Keep the project recipe if you want to change width or thickness in this workbench later.

The traced boundary is a polygonal approximation. A hole that looks circular in the photograph is not automatically fitted to an exact analytic circle, and STEP export does not change that approximation into an exact measured feature.

After import, check the bounding-box width, height, thickness, number of solids, and hole topology. Single-piece mode produces one valid solid with positive volume. Split mode produces the reported valid piece solids; inspect the pieces separately rather than assuming the assembly view shows a print-bed arrangement.

## STL: a triangle mesh

Use STL for a mesh or slicing workflow. Its triangles approximate the solid's surface. Mesh resolution affects the representation of curved boundaries, not the fidelity of the original photograph.

STL commonly has no reliable unit metadata. Import its coordinates as **millimeters**. A model that appears 25.4 times too large or too small usually indicates an inch/millimeter mismatch.

STL has no standard color/material representation. The chosen color and material are stored as preview/recipe/planning choices, not a filament assignment inside the STL. Combined split-mode STL retains assembled piece positions. Use individual part files when arranging pieces in a slicer.

Check that the receiving tool reports a closed mesh and that holes remain open. A printable mesh is not a declaration that the part is strong enough, dimensionally suitable, or ready for a particular printer and material.

### Check an STL independently

The [reference library](../reference-library/README.md) in this repository includes `cadkit meshcheck`, a standard-library STL checker that shares no code with the CadQuery exporter. Run it from `reference-library/`, giving the largest dimension you expect in millimeters:

```bash
python3 -m cadkit meshcheck ~/Downloads/model.stl --expect-mm 80
```

It reports extents, volume, boundary and non-manifold edges, non-manifold vertices, orientation, connected components, and genus. For a flat part, genus is the number of through-holes, so compare it with the hole count shown in the workbench. A missing or extra through-hole changes the genus even when the outline looks right. The unit hint flags a likely inch, centimeter, or meter mix-up. The command exits with status 0 only for a closed, manifold, consistently oriented mesh with no degenerate triangles. Add `--json` for machine-readable output. See the [`cadkit` notes](../reference-library/cadkit/README.md#mesh-check-notes).

The workbench test suite runs this checker on combined exports, on a traced photograph with round holes, and on every piece in a split bundle (`tests/test_mesh_interop.py`). Like the receiving tool's check, a pass is a geometry result, not evidence of strength or fit.

## DXF: a planar profile

Use DXF for the 2D boundary and interior cutouts. It describes a flat profile, not the extruded thickness, toolpaths, cutting order, kerf compensation, or machine settings.

Confirm millimeter units, closed contours, and the separation between the outer boundary and holes in the receiving CAD/CAM software. Decide how to compensate for the manufacturing process there.

In split mode, DXF records each piece's planar outline at its assembled position. Shared cuts can appear on both adjacent pieces; review duplicates and cutting order in CAM. The app does not supply kerf compensation or toolpaths.

## Parts ZIP: individual pieces

Split mode adds a parts ZIP containing `part-01.step`, `part-01.stl`, subsequent numbered piece pairs, and `manifest.json`. These are actual generated solids and their meshes. The splitter supports at most eight cells and eight resulting connected pieces; a complex outline can produce more than one piece inside a cell and may be rejected if it exceeds that bound.

Each individual part file is translated so its minimum X and Y coordinates and its bottom Z coordinate are zero. Translation preserves its dimensions and shape. Import STL coordinates as **millimeters** and arrange each piece in the slicer yourself; the archive is not a slicer project or automatically packed build plate.

The manifest identifies `format: "pictures-to-cad-parts"`, `version: 1`, and `units: "mm"`. It records the design choices, assembled dimensions, total volume, and each part's filenames, dimensions, volume, geometric fit result, and `assembly_offset_mm`. Add that offset to an individual part's coordinates to reconstruct the combined assembly.

The combined STEP/STL keep the pieces touching at their original assembled coordinates. **Separate pieces** in the viewer moves their actual meshes apart for inspection only; it does not change export positions. Use that view to inspect cut faces, then use the numbered part files for separate placement.

The cuts create no alignment pins, joints, glue allowance, clearance, or kerf compensation. Check how the pieces will be joined and whether splitting preserves the intended function. A per-piece bed-fit result does not assess strength, supports, adhesion, or material/printer compatibility.

## Project JSON: the workbench recipe

Use **Save project** to download a version 2 JSON recipe. Restore it through **Photo → Browse files**, using the same chooser as an image. The app rebuilds from the source outline, measured inputs, and saved design/print settings; restoration does not require re-tracing a photograph. Version 1 recipes still import with default design settings.

Save before refreshing or leaving the page. The workbench does not provide automatic project persistence; a fresh page starts with the sample.

The project recipe preserves the traced coordinates, measured width/thickness, XY/thickness design scales, geometry-detail mode, color/material choices, printer settings, and split plan needed to regenerate the result. Design percentages remain separate from the source measurements. Color/material choices also appear in a split bundle's manifest; STEP, STL, and DXF do not encode them. The recipe is not a substitute for the original physical measurement, nor a general-purpose CAD exchange format.

Keep a separately named copy of the original photo when provenance matters. The recipe **does not include the photograph**. A restored project therefore displays an outline-only source view; upload a photograph if you want to trace again.

## Keep revisions consistent

Changing a photo, outline, reference width, thickness, or other geometry setting makes the previous result outdated. Rebuild the model before exporting it. If a rebuild fails, an earlier preview may remain visible to help recovery, but it must not be presented as the result of the new settings.

The preview and download links returned by a successful build belong to that build. The interface releases superseded builds, and remaining temporary server artifacts expire after one hour. Download files and recipes you want to keep; old links are not an archive. If the result has expired or been cleared, rebuild the current settings to obtain fresh links.

## A practical import checklist

1. Confirm the expected units.
2. Compare the complete width and thickness with the measured inputs multiplied by the explicit design percentages; inspect any outline change from geometry-detail approximation.
3. Check a second measured dimension against the physical part.
4. Verify that every intended through-hole is open.
5. Check for unexpected disconnected bodies or closed-over openings.
6. Save the original recipe alongside any downstream CAD edits.

Automated tests exercise known fixtures and export re-imports. See [validation results](validation.md) for the checks actually run; they do not replace checks on your own photograph.
