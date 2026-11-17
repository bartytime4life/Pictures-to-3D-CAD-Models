# Workflow guide

Choose the workspace that matches the source and the result you need. The measured flat-part workflow builds a planar extrusion; the Relief workspace interprets an image as a height or transmission field. Neither is a universal reconstruction of hidden 3D shape.

## Scale and check a flat part

**Inputs:** one useful front-on photograph, a known physical length and a measured constant thickness.

1. Load the photo in **Flat part** and inspect the outer boundary and each through hole.
2. Select the scale method. A full-width measurement refers to the entire traced horizontal extent. A known-feature reference uses two chosen endpoints and the length between them. A paper reference needs its stated physical size and a suitable capture of the full sheet.
3. For a common-object reference, confirm the actual object's type and dimensions. Place endpoints across the selected feature; an assumed catalog size is not an independent measurement.
4. Enter thickness. If using a reference sheet, changing thickness can require another trace because side-wall correction depends on it.
5. Compare an independent height or another important dimension with the predicted source geometry. A conditional endpoint-shift scenario helps inspect sensitivity but does not account for every camera or measurement error.
6. Build, inspect and save the project. Use the [engineering model](engineering-model.md) for explicit fit requirements and acceptance records.

The source measurement and the requested design size are different controls. **Quick edit** derives XY scale from a target width and derives thickness scale from a target thickness. XY remains proportional. **Restore measured size** returns both scales to 100%; it does not replace your reference measurements.

## Edit and compare versions

Change target size, appearance, detail or print-planning settings. Undo and Redo restore design settings; editing the source or loading a new project starts a new relevant context. A new build is needed before exporting any restored version.

The model viewer's camera, grid, wireframe, dimensions and separated-piece inspection are visual aids. They do not modify the project geometry. To change a shape beyond the exposed size/detail/split controls, export STEP or generated OpenSCAD and edit it in the appropriate CAD tool. Imported downstream changes do not update this workbench's recipe automatically.

To inspect a source edge, use the source panel's plus/minus buttons and drag the image. With the source inspection region focused, arrow keys pan, `+` or `-` changes zoom, and `0` fits the image again. **Fit source image** resets zoom and pan without changing measurements. The source outline moves with the photograph. In CAD preview, **Grid**, **Mesh** and **Size** toggle display layers; **Reset CAD display** restores their defaults.

## Prepare a large part for a slicer

1. Select the actual printer and nozzle, or enter custom build bounds. Set a deliberate XY margin.
2. Build the model and read the per-piece fit results. Rectangular containment checks account for dimensions and a flat in-plane orientation, not supports or toolpaths.
3. If available, inspect a suggested split plan. Straight cuts introduce no alignment joints, clearance or kerf allowance. Review the assembly method before choosing the split.
4. Inspect each current piece in **Prepare for slicing**. The rotation slider changes only the display angle; the mesh-footprint message is separate from the saved geometric fit result. **Use suggested turn** returns to the solver's angle when one exists.
5. Select the process plan. Nozzle size bounds the allowed layer height; actual machine/material profiles can impose tighter limits.
6. Rebuild and download the selected slicer ZIP. Import individual `part-XX.3mf` files for separately arranged pieces. Combined geometry retains assembly positions.
7. Choose native printer/material/process settings, arrange and orient, slice and inspect layers. Save the reviewed native project in the slicer.

Read [print planning](print-planning.md), [printer data](printer-catalog.md) and [slicer integration](slicers.md) for details. Native launch, when explicitly enabled locally, only requests opening geometry; it does not prove import or slicing succeeded.

## Make a relief or lithophane

Open **Relief**, select the intended mode and source, then choose width and thickness range. The studio accepts image-derived heights and supported depth/elevation workflows. A brightness relief interprets brightness as height; a lithophane maps transmission into thickness. Optional AI depth is a separate local model with its own setup and limits.

Inspect the built surface, warnings, wall bounds and exported units. Supported spherical forms have additional opening/collar settings. Blender handoffs permit downstream sculpting or scene editing, but those edits do not flow back into the browser's build settings. Follow the [complete relief guide](relief.md), including its calibration and printing limitations.

## Choose source photos from a collection

Open **Photo library**, add photos or an authorized local folder, and run the indexing workflow. Sort by sharpness, inspect copies and open a selected image in Flat part or Relief. Optional local vision features add similarity and suggested groups; verify groups by eye.

Library originals, thumbnails and metadata have different retention rules from temporary flat-part uploads. A moved or changed original may need a rescan. See [photo library](photo-library.md) and [privacy](privacy-security.md).

## Learn without changing a model

Use **Knowledge** to search guides, follow step-by-step articles and retain local notes. Use **Science lab** to edit numerical scenarios for scale sensitivity, layer discretization or measured clearance. The scenarios are independent of the current CAD recipe: exporting a scenario records its inputs; it does not apply a correction to geometry.

**Search commands** opens a keyboard-accessible launcher. Use Ctrl/Cmd+K, type a workspace or action, choose with the arrow keys, and press Enter. Escape closes it. Follow [science](science.md) for formulas, assumptions and source references.

## Hand off a durable project

Keep the original photo, the browser-saved project JSON, the exact geometry you reviewed and the intended slicer package. If you need optional feature-reference or independent-height notes, retain the browser's **Save project** output: the server's build recipe in a slicer ZIP omits some browser-only measurement notes.

For fabrication, also record the native slicer project, machine/material profile, actual print settings and physical measurements. A ZIP hash identifies bytes; it does not establish dimensional accuracy or a successful print. Use the companion [independent-check](../reference-library/templates/INDEPENDENT-CHECKS.md) and [print-acceptance](../reference-library/templates/PRINT-ACCEPTANCE.md) templates.
