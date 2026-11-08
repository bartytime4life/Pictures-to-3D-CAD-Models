# Research and design decisions

This product starts with a deliberately constrained geometry problem: a photograph can provide a planar boundary, and a user can supply measured scale and thickness. The resulting extrusion is useful for flat parts without pretending that a single image identifies hidden surfaces.

The research below informed the implementation and its acceptance criteria. It is a review of technical and accessibility sources, not a claim that user interviews, a physical metrology study, or a production security assessment have been completed.

The [selected design reference](images/design-reference.png) is a generated concept. The [workbench screenshot](images/workbench.png) is browser-rendered implementation evidence. The sample photograph is generated demonstration input and is traced by the real conversion pipeline; it is not a measured reference specimen.

## Image to outline

[OpenCV's contour introduction](https://github.com/opencv/opencv/blob/4.x/doc/py_tutorials/py_imgproc/py_contours/py_contours_begin/py_contours_begin.markdown) describes contour extraction from binary images. This supports a visible threshold-and-review stage before geometry construction.

[Contour hierarchy](https://github.com/opencv/opencv/blob/4.x/doc/py_tutorials/py_imgproc/py_contours/py_contours_hierarchy/py_contours_hierarchy.markdown) records nested boundaries. That matters because a part's through-holes must remain distinguishable from its outer boundary. Pixel hierarchy cannot determine whether a photographed dark region is physically a hole; user review remains necessary.

[Contour approximation](https://github.com/opencv/opencv/blob/4.x/doc/py_tutorials/py_imgproc/py_contours/py_contour_features/py_contour_features.markdown) uses a distance parameter to simplify an outline. That parameter controls approximation of the traced pixels. It does not establish the accuracy of the camera, source photograph, or physical measurement.

## Outline to solid and exchange files

[CadQuery examples](https://github.com/CadQuery/cadquery/blob/master/doc/examples.rst) demonstrate profile extrusion and holes. This provides a direct, inspectable path from a valid planar boundary to a solid with a supplied thickness.

[CadQuery import and export documentation](https://github.com/CadQuery/cadquery/blob/master/doc/importexport.rst) describes STEP, STL, and DXF support and distinguishes interchange geometry from parametric history. The interface therefore calls STEP a CAD solid and keeps a reproducible project recipe separately.

The intended checks go beyond successful file creation: re-import STEP, verify bounds and positive volume, check mesh closure, and check that planar loops and units survive DXF export. The [validation report](validation.md) records the tests actually executed.

## Why multiview reconstruction is separate

[COLMAP's tutorial](https://github.com/colmap/colmap/blob/main/doc/tutorial.rst) describes overlapping images from different viewpoints and the importance of texture and capture conditions. Its [FAQ](https://github.com/colmap/colmap/blob/main/doc/faq.rst) discusses hardware and reconstruction constraints.

Those requirements differ substantially from a single-photo extrusion. A future multiview feature would need its own capture flow, resource budget, reconstruction validation, scale handling, and explanation of mesh versus editable CAD. It is not an invisible background feature of this release.

## Interaction and accessibility

The workbench keeps the photographed boundary and generated solid together so the user can compare them before export. Real measurements are entered explicitly. Geometry edits invalidate previous export state, and recoverable errors preserve the user's inputs.

These design choices are supported by the following W3C guidance:

- [Keyboard operation](https://github.com/w3c/wcag/blob/main/understanding/20/keyboard.html): provide keyboard operation for controls and non-freehand interactions.
- [Labels or instructions](https://github.com/w3c/wcag/blob/main/understanding/20/labels-or-instructions.html): explain input purpose and expected format, including units.
- [Error identification](https://github.com/w3c/wcag/blob/main/understanding/20/error-identification.html) and [error suggestion](https://github.com/w3c/wcag/blob/main/understanding/20/error-suggestion.html): identify the failed input and a useful correction.
- [Status messages](https://github.com/w3c/wcag/blob/main/understanding/21/status-messages.html): announce asynchronous state without unnecessarily moving focus.
- [Use of color](https://github.com/w3c/wcag/blob/main/understanding/20/use-of-color.html): do not communicate validity through color alone.
- [Target size](https://github.com/w3c/wcag/blob/main/understanding/22/target-size-minimum.html): make controls large enough or appropriately spaced.

Following these principles is not a certification of conformance. Keyboard, assistive-technology, contrast, responsive, and browser testing must evaluate the implemented interface.

## Evidence boundaries

The linked upstream documents are maintained sources and may change. The application's lockfiles pin the installed dependency versions; a documentation example on an upstream branch is not proof that every API or behavior matches the installed version.

Generated demonstration imagery is clearly an example. It is useful for checking the workflow, but neither it nor a synthetic shape establishes a physical error bound. A measured-photo benchmark would need known reference parts, capture protocols, independent dimensions, and reported uncertainty.
