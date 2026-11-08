# Export formats and dimensional checks

Choose the output according to the receiving tool. All generated geometry uses **millimeters internally**. Confirm the receiving program's import settings rather than relying on a file extension to establish units.

## STEP: a CAD solid

Use STEP when continuing in a solid-modeling CAD application. The file contains the generated boundary representation of the extruded part and its through-holes.

STEP does not carry this application's original editable feature history. The receiving tool may support direct edits, but that is different from recovering a named sketch, constraints, or an extrusion feature. Keep the project recipe if you want to change width or thickness in this workbench later.

The traced boundary is a polygonal approximation. A hole that looks circular in the photograph is not automatically fitted to an exact analytic circle, and STEP export does not change that approximation into an exact measured feature.

After import, check the bounding-box width, height, thickness, number of solids, and hole topology. The expected result is one valid solid with positive volume.

## STL: a triangle mesh

Use STL for a mesh or slicing workflow. Its triangles approximate the solid's surface. Mesh resolution affects the representation of curved boundaries, not the fidelity of the original photograph.

STL commonly has no reliable unit metadata. Import its coordinates as **millimeters**. A model that appears 25.4 times too large or too small usually indicates an inch/millimeter mismatch.

Check that the receiving tool reports a closed mesh and that holes remain open. A printable mesh is not a declaration that the part is strong enough, dimensionally suitable, or ready for a particular printer and material.

## DXF: a planar profile

Use DXF for the 2D boundary and interior cutouts. It describes a flat profile, not the extruded thickness, toolpaths, cutting order, kerf compensation, or machine settings.

Confirm millimeter units, closed contours, and the separation between the outer boundary and holes in the receiving CAD/CAM software. Decide how to compensate for the manufacturing process there.

## Project JSON: the workbench recipe

Use **Save project** to download a version 1 JSON recipe. Restore it through **Photo → Browse files**, using the same chooser as an image. The app rebuilds the solid from the saved outline and dimensions; restoration does not require re-tracing a photograph.

Save before refreshing or leaving the page. The workbench does not provide automatic project persistence; a fresh page starts with the sample.

The project recipe preserves the traced coordinates and dimensional settings needed to regenerate the extrusion. It is not a substitute for the original physical measurement, nor a general-purpose CAD exchange format.

Keep a separately named copy of the original photo when provenance matters. The recipe **does not include the photograph**. A restored project therefore displays an outline-only source view; upload a photograph if you want to trace again.

## Keep revisions consistent

Changing a photo, outline, reference width, thickness, or other geometry setting makes the previous result outdated. Rebuild the model before exporting it. If a rebuild fails, an earlier preview may remain visible to help recovery, but it must not be presented as the result of the new settings.

The preview and download links returned by a successful build belong to that build. The interface releases superseded builds, and remaining temporary server artifacts expire after one hour. Download files and recipes you want to keep; old links are not an archive. If the result has expired or been cleared, rebuild the current settings to obtain fresh links.

## A practical import checklist

1. Confirm the expected units.
2. Compare the complete width and thickness with the entered values.
3. Check a second measured dimension against the physical part.
4. Verify that every intended through-hole is open.
5. Check for unexpected disconnected bodies or closed-over openings.
6. Save the original recipe alongside any downstream CAD edits.

Automated tests exercise known fixtures and export re-imports. See [validation results](validation.md) for the checks actually run; they do not replace checks on your own photograph.
