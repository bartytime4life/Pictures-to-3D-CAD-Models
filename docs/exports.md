# Export formats and dimensional checks

[Documentation index](README.md) · [Guided workbench review](validation/guided-workbench.md)

Choose the output according to the receiving tool. All generated geometry uses **millimeters internally**. Confirm the receiving program's import settings rather than relying on a file extension to establish units.

Open **Choose an export** or **Review export** for the current build. **CAD & 3D
printing** contains STEP, STL, 3MF, and Parts ZIP when available. Expand **Drawings
& source files** for DXF, SVG, PDF, and OpenSCAD. The disclosure works with the
keyboard as well as a pointer.

When settings change, use **Update preview** in the next-step guide or **Update
model** in the measurement controls before exporting. An earlier preview may
remain visible for comparison, but its geometry downloads and printer-fit result
are withheld until a successful current build. Export readiness describes the
digital revision, not physical fit or manufacturing acceptance.

## STEP: CAD solids

Use STEP when continuing in a solid-modeling CAD application. The file contains the generated boundary representation of the extruded part and its through-holes. In split mode, the combined file contains the generated pieces in their assembled positions.

A single-piece build extrudes its accepted fitted lines, arcs and circles.
Accepted circles and arcs become exact cylindrical faces that downstream CAD
can dimension and edit; boundaries retained as traced outlines remain polygonal.
The export dialog reports the accepted primitive counts. A fitted radius is
model-derived geometry, and **Recover design intent** can deliberately adjust
it; it is not an independently measured physical radius. Split output still
uses the traced polygon.

STEP does not carry this application's original editable feature history. The receiving tool may support direct edits, but that is different from recovering a named sketch, constraints, or an extrusion feature. Keep the project recipe if you want to change width or thickness in this workbench later.

For polygon-only profiles, the traced boundary remains a polygonal approximation in STEP. For fitted profiles, accepting an analytic circle changes its digital representation; it does not establish that the photographed feature is perfectly round or that its radius is an exact physical measurement.

After import, check the bounding-box width, height, thickness, number of solids, and hole topology. Single-piece mode produces one valid solid with positive volume. Split mode produces the reported valid piece solids; inspect the pieces separately rather than assuming the assembly view shows a print-bed arrangement.

### Verify critical arc geometry

For fit-critical curves, measure the actual STEP or DXF radius, centre position,
hole spacing and joins between arcs and lines in CAD. Overall dimensions and a
valid solid do not check every curve.

Final arc assembly preserves the final fitted centre and radius. It chooses
shared endpoints using the source-end evidence and a uniquely resolved
endpoint-movement rule; see [the assembly method](architecture.md#circle-consistent-final-assembly).
This is a digital construction rule, not evidence that the fitted circle matches
the physical part.

Nearly touching or disjoint curves, ambiguous joins, missing source evidence,
and numerical or work limits can leave that construction unresolved. The
affected boundary is then kept as a traced outline with an explicit notice,
instead of emitting an arc on a different circle. Other accepted analytic
boundaries, including fitted holes, remain available with the sheet scale and
corrections. The fitted counts and radius/design notes refer to accepted final
geometry. A retained boundary exports as straight segments and has no accepted
analytic radius. This also applies with **Recover design intent** turned off.
The [canonical-arc record](validation/canonical-arcs.md) separates the repair,
retained cases and remaining model limits.

Compare these features with independent physical measurements. If they disagree,
rebuild the critical curves in CAD from reviewed dimensions, or use an ordinary
polygon trace from a suitable front-on capture with measured scale. Preserve the
original recipe and record downstream CAD edits as a new revision; those edits
do not update the workbench's recipe or printer-fit result.

## 3MF and slicer handoffs

The **3MF** export contains millimeter geometry with separate objects for split output. Each object uses welded mesh indices and retains its assembly position. Individual split pieces in the Parts ZIP and slicer packages are normalized to XY zero and Z zero. A neutral 3MF does not contain printer, filament, process, support or multi-material settings.

Choose **Bambu Studio** or **PrusaSlicer** in the export dialog for a tailored ZIP with geometry, editable recipe, part files, instructions and SHA-256 manifest. Choose native presets and review placement in the receiving slicer. See [slicer integration](slicers.md) for optional local opening and version/install boundaries.

Also use **Save project** if you need the endpoint-reference and independent-height
notes entered in the browser. The handoff ZIP's server-generated `project.json`
contains the build profile, source dimensions and design settings, including
fitted/reference-sheet profile data when present. It does not include the
browser's separate `reference_calibration`, `measured_height_mm` or `height_check`
fields.

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

It reports extents, volume, boundary and non-manifold edges, non-manifold vertices, orientation, connected components, and genus. For one connected, closed extrusion of a planar profile, genus is the number of through-holes. A missing or extra through-hole changes it even when the outline looks right. Inspect split pieces individually: a cut can open a hole onto a cut face, and touching assembled meshes need not form one manifold surface. The unit hint flags a likely inch, centimeter, or meter mix-up. Unless `--allow-open` is given, the command exits with status 0 only for a closed, manifold, consistently oriented mesh with no degenerate triangles. Add `--json` for machine-readable output. See the [`cadkit` notes](../reference-library/cadkit/README.md#mesh-check-notes).

The workbench test suite runs this checker on combined exports, on a traced photograph with round holes, and on every piece in a split bundle (`tests/test_mesh_interop.py`). Like the receiving tool's check, a pass is a geometry result, not evidence of strength or fit.

## DXF: a planar profile

Use DXF for the 2D boundary and interior cutouts. It describes a flat profile, not the extruded thickness, toolpaths, cutting order, kerf compensation, or machine settings. A fitted single-piece outline is written as `LINE`, `ARC` (counter-clockwise start and end angles) and `CIRCLE` entities on the `OUTLINE` and `HOLES` layers instead of polylines.

Confirm millimeter units, closed contours, and the separation between the outer boundary and holes in the receiving CAD/CAM software. Decide how to compensate for the manufacturing process there.

In split mode, DXF records each piece's planar outline at its assembled position. Shared cuts can appear on both adjacent pieces; review duplicates and cutting order in CAM. The app does not supply kerf compensation or toolpaths.

## SVG: the same profile for cutters and vector editors

Use SVG for a laser or vinyl cutter's software, or for a vector editor. It holds the same closed loops as the DXF, unfilled, with a 0.1 mm black stroke, in two groups named `outline` and `holes`.

One user unit is one millimetre. The file states its width and height in millimetres and a view box of the same numbers, with a 1 mm blank border round the part. After import, measure the outline: it should have the width and height the export dialog shows. A program that ignores the stated millimetres shows the part at another scale.

A fitted single-piece outline is written as lines, circular arcs (`A` path commands) and `<circle>` elements. An arc longer than a third of a turn is written as two or more arcs: an SVG arc is defined by its end points, and near a half turn it loses accuracy to the rounding of those points. Other outlines are closed polygons. In split mode each piece appears at its assembled position.

Like the DXF, the SVG is a flat profile. It holds no thickness, toolpaths, cutting order or kerf compensation.

## PDF: a 1:1 drawing to print

Use the PDF to check the outline against the real part before cutting or printing anything. Print it, lay the part on the paper, and look at every edge and hole. It also works as a paper template: each round hole carries a centre mark.

- **Print at 100 %**, which print dialogs also call "actual size". Do not fit the page to the paper.
- **Measure both rulers.** The page has a 100 mm ruler along each axis. A printer can scale the two directions differently, so measure both. If one reads 99.5 mm, every dimension in that direction is 0.5 % small.
- **The page fits A4 and US Letter.** It is 210 × 279.4 mm, the area the two sizes share, and is turned on its side for a wide part. A part too large for it gets a page as large as the part needs; print that on a larger printer, or let the print dialog tile it.
- **The print is a visual check, not a gauge.** Paper swells and shrinks with humidity, and a printed line has a width. Use calipers for dimensions that matter.

The drawing holds lines only, with no fill or thickness. In split mode it shows the pieces in their assembled positions.

## OpenSCAD: editable profile extrusion

Choose **OpenSCAD** in the export dialog to download `model.scad`. For a fitted single-piece outline, circular boundaries stay `circle(r = …, $fn = …)` calls inside a `difference()`; other fitted boundaries become sampled polygons. The sampling targets 0.005 mm chord error, with 24–720 facets for a circle and at most 720 subdivisions per arc. The cap can make the actual chord error larger for large radii; it is not a universal approximation bound. Source generation uses the workbench's effective design percentages and final profiles. Polygon output includes geometry-detail approximation and any split cuts; a fitted single-piece outline retains its fitted geometry regardless of the detail setting. Generating this source does not require an OpenSCAD installation.

Open the file in OpenSCAD, then preview and render it. `thickness_mm` is the effective built thickness, `xy_scale = 1` preserves the exported XY dimensions, and `part_index = 0` displays the whole assembly. In split mode, set `part_index` to a numbered piece to inspect or export only that piece. Selected pieces keep their assembled coordinates; place them in your slicer. The combined source unions touching pieces for display/rendering; use the selector or the Parts ZIP when separate pieces are needed.

The source retains editable extrusion values and fitted circle radii where available; OpenSCAD renders its circles with facets, and sampled boundaries remain polygons. It does not recover sketch constraints, threads, hidden features, or the original CAD feature history. Changes made in OpenSCAD do not update the saved workbench recipe or its printer-fit result. Recheck the new dimensions, holes, closure, and fit after edits; material and preview color are not encoded in SCAD.

For a new plate with explicit hole diameters and spacing, the companion [OpenSCAD workspace](../reference-library/index.html#cad) provides parameter-driven mounting plates and fit coupons. It opens from the workbench header in a separate tab. Its [native workflow](../reference-library/OPENSCAD.md) records mesh checks and build provenance; synthetic passing geometry does not establish physical fit, strength, or printing success.

## Parts ZIP: individual pieces

Split mode adds a parts ZIP containing `part-01.step`, `part-01.stl`, `part-01.3mf`, subsequent numbered piece files, and `manifest.json`. These are actual generated solids and their meshes. The splitter supports at most eight cells and eight resulting connected pieces; a complex outline can produce more than one piece inside a cell and may be rejected if it exceeds that bound.

Each individual part file is translated so its minimum X and Y coordinates and its bottom Z coordinate are zero. Translation preserves its dimensions and shape. Import STL coordinates as **millimeters** and arrange each piece in the slicer yourself; the archive is not a slicer project or automatically packed build plate.

The manifest identifies `format: "pictures-to-cad-parts"`, `version: 1`, and `units: "mm"`. It records the design choices, assembled dimensions, total volume, and each part's filenames, dimensions, volume, geometric fit result, and `assembly_offset_mm`. Add that offset to an individual part's coordinates to reconstruct the combined assembly.

The combined STEP/STL/3MF keep the pieces touching at their original assembled coordinates. **Separate pieces** in the viewer moves their actual meshes apart for inspection only; it does not change export positions. Use that view to inspect cut faces, then use the numbered part files for separate placement.

The cuts create no alignment pins, joints, glue allowance, clearance, or kerf compensation. Check how the pieces will be joined and whether splitting preserves the intended function. A per-piece bed-fit result does not assess strength, supports, adhesion, or material/printer compatibility.

## Project JSON: the workbench recipe

Use **Save project** in the header, or **Save editable project recipe** in Export, to download a JSON recipe: version 2 for a polygon-only profile, or version 3 when the profile contains fitted primitives or reference-sheet evidence. Restore it through **Photo → Browse files**, using the same chooser as an image. The app rebuilds from the source outline, measured inputs, and saved design/print settings; restoration does not require re-tracing a photograph. Versions 1, 2 and 3 import; version 1 uses default design settings.

Save before refreshing or leaving the page. The workbench does not provide automatic project persistence; a fresh page starts with the sample.

The project recipe preserves the traced coordinates, source width/thickness, XY/thickness design scales, geometry-detail mode, color/material choices, printer settings, and split plan needed to regenerate the result. Design percentages remain separate from the source measurements. Color/material choices also appear in a split bundle's manifest; STEP, STL, DXF, and SCAD do not encode them. The recipe is not a substitute for the original physical measurement, nor a general-purpose CAD exchange format.

When **Apply reference scale** has been used, the browser-saved recipe also preserves optional `reference_calibration` data: `known_length_mm`, two `reference_points`, and `image_size` with its working-image width and height. Coordinates refer to the orientation-adjusted working image, whose longest side is at most 1400 pixels; they are not display-pixel coordinates or necessarily original camera-file coordinates. The full outside `width_mm` remains the scale input for geometry generation. Directly editing that width clears the endpoint-calibration record so it no longer appears to explain a manually chosen size.

The optional `measured_height_mm` preserves the independent outside-height input. Optional `height_check` stores `allowance_mm` (above 0, up to 2000 mm) and `measurement_bound_mm` (0–2000 mm), and requires that height measurement. These are user-entered decision inputs; no assessment status is saved. Import validates them and recomputes the result against the restored source. See [engineering model and verification](engineering-model.md) for the conditional interval rule. Its comparison is against the source profile before XY design scaling and does not change the generated shape. Recipes without these optional fields remain importable. They are workbench measurement notes, not an uncertainty budget, physical inspection certificate, or additional measurement metadata in STEP, STL, DXF, or the parts manifest.

If these optional notes are incomplete or invalid, **Save project** returns from
Export to the measurement controls, opens the height check, and focuses the field
that needs correction. Correct the notes or clear both decision inputs before
saving again. This does not change an otherwise current CAD model.

Keep a separately named copy of the original photo when provenance matters. The recipe **does not include the photograph**. A restored project therefore displays an outline-only source view; saved reference endpoints retain their working-image frame and can be adjusted numerically. Upload a photograph if you want to trace again; it starts a new source rather than attaching the old reference to a different image.

## Keep revisions consistent

Changing a photo, outline, reference width, thickness, or other geometry setting makes the previous result outdated. Rebuild the model before exporting it. If a rebuild fails, an earlier preview may remain visible to help recovery, but it must not be presented as the result of the new settings.

The preview and download links returned by a successful build belong to that build. The interface releases superseded builds, and its current build when its page is closed or reloaded. Remaining temporary server artifacts expire after one hour. Download files and recipes you want to keep; old links are not an archive. If the result has expired or been cleared, rebuild the current settings to obtain fresh links.

## A practical import checklist

1. Confirm the expected units.
2. Compare the complete width and thickness with the source dimensions multiplied by the explicit design percentages; inspect any outline change from geometry-detail approximation. If a known feature set the scale, check that its saved endpoints and measured length describe the intended physical reference.
3. Review the independent source-height comparison, if entered, and check further reserved dimensions against the physical part. Account for intentional design scaling when measuring the export.
4. Verify that every intended through-hole is open.
5. Check for unexpected disconnected bodies or closed-over openings.
6. Save the original recipe alongside any downstream CAD edits.

Automated tests exercise known fixtures and export re-imports. See [validation results](validation.md) for the checks actually run; they do not replace checks on your own photograph.
