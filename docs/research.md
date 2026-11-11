# Research and design decisions

This product starts with a deliberately constrained geometry problem: a photograph can provide a planar boundary, and a user can supply measured scale and thickness. The resulting extrusion is useful for flat parts without pretending that a single image identifies hidden surfaces.

The research below informed the implementation and its acceptance criteria. It is a review of technical and accessibility sources, not a claim that user interviews, a physical metrology study, or a production security assessment have been completed.

The [selected design reference](images/design-reference.png) is a generated concept. The [workbench screenshot](images/workbench.png) is browser-rendered implementation evidence. The sample photograph is generated demonstration input and is traced by the real conversion pipeline; it is not a measured reference specimen.

## Image to outline

[OpenCV's contour introduction](https://github.com/opencv/opencv/blob/4.x/doc/py_tutorials/py_imgproc/py_contours/py_contours_begin/py_contours_begin.markdown) describes contour extraction from binary images. This supports a visible threshold-and-review stage before geometry construction.

[Contour hierarchy](https://github.com/opencv/opencv/blob/4.x/doc/py_tutorials/py_imgproc/py_contours/py_contours_hierarchy/py_contours_hierarchy.markdown) records nested boundaries. That matters because a part's through-holes must remain distinguishable from its outer boundary. Pixel hierarchy cannot determine whether a photographed dark region is physically a hole; user review remains necessary.

[Contour approximation](https://github.com/opencv/opencv/blob/4.x/doc/py_tutorials/py_imgproc/py_contours/py_contour_features/py_contour_features.markdown) uses a distance parameter to simplify an outline. That parameter controls approximation of the traced pixels. It does not establish the accuracy of the camera, source photograph, or physical measurement.

## Known-feature scale and dimensional checks

The workbench accepts either the full outside width or a measured distance between two image points. For the latter, the Euclidean pixel distance defines one millimeter-per-pixel factor, applied to both axes. Endpoints use the orientation-adjusted working-image coordinate frame, not the resized browser preview. The measured reference, endpoints, and frame are retained separately from the resulting outside width and intentional design percentages.

[OpenCV's homography tutorial](https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html) describes the projective relation between planes and its use for perspective correction. [Its camera-calibration tutorial](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html) treats camera parameters and radial/tangential distortion separately. A single known length supplies uniform scale; it does not supply either correction. This motivates the front-facing capture guidance, same-plane reference requirement, and explicit warning about short references.

An optional measured outside height is compared with the source-profile estimate before design scaling. It does not enter the scale calculation or adjust geometry. A measurement used to set scale cannot also provide an independent test of that scale. If a reserved check is used to correct the model, it becomes development evidence for the revised model; retain the earlier result and seek a fresh check. The [independent-check worksheet](../reference-library/templates/INDEPENDENT-CHECKS.md) records that distinction.

[JCGM 100:2008 (GUM), sections 3.1–3.3](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf) explains why a measurement result needs an uncertainty statement and why several effects can contribute. Here those effects can include physical reference measurement, endpoint placement, trace approximation, perspective, and lens distortion. The height comparison reports a signed difference, not a numerical uncertainty budget or a manufacturing pass. Synthetic coordinate/export checks test the calculation and preservation of inputs; a measured-photo benchmark remains necessary to quantify physical performance.

## Reference sheet, sub-pixel edges and fitting

The reference-sheet stages are documented with their derivations and checks in [reference-sheet tracing](reference-sheet.md). The main sources and results they rely on:

- Plane homography and camera pose from a plane: [OpenCV's homography tutorial](https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html); the two orthonormality constraints on the rotation columns are those of [Zhang's plane-based calibration](https://www.microsoft.com/en-us/research/publication/a-flexible-new-technique-for-camera-calibration/) (2000), here used with one image and a known principal point to solve only the focal length.
- Radial distortion from straight lines (the plumb-line method): D. C. Brown, "Close-range camera calibration", *Photogrammetric Engineering* 37 (1971). The model inverse is solved by Newton's method.
- Tone curve: the sRGB transfer function of IEC 61966-2-1:1999, in the form given by the [CSS Color Module Level 4 conversion code](https://www.w3.org/TR/css-color-4/#color-conversion-code). Display P3 uses the same curve. Edges are measured after undoing it, because blur and partial pixel coverage mix light linearly.
- Cubic convolution interpolation: [Keys (1981)](https://doi.org/10.1109/TASSP.1981.1163711), whose a = −½ kernel reproduces quadratics.
- Circle fitting: the Kåsa algebraic fit refined by Gauss–Newton on geometric distance; see N. Chernov, *Circular and Linear Regression: Fitting Circles and Lines by Least Squares* (CRC Press, 2010) for bias and precision.
- The normal CDF is evaluated with [Abramowitz & Stegun 7.1.26](https://personal.math.ubc.ca/~cbm/aands/page_299.htm) (|erf error| < 1.5 × 10⁻⁷).
- Exact identities are checked in rational arithmetic at random rational points. A nonzero rational function vanishes at a random point with negligible probability (the [Schwartz–Zippel lemma](https://en.wikipedia.org/wiki/Schwartz%E2%80%93Zippel_lemma)), so agreement at independent random points is strong evidence the identity holds generally.

The blur–curvature series, its third-order coefficient (5/24), the two-step wall model and its degeneracy, the sheet-proportions check, the size of the tone-curve bias and the shift a sloped shadow causes were derived for this workbench and checked numerically; they are not taken from a cited source.

## Outline to solid and exchange files

[CadQuery examples](https://github.com/CadQuery/cadquery/blob/master/doc/examples.rst) demonstrate profile extrusion and holes. This provides a direct, inspectable path from a valid planar boundary to a solid with a supplied thickness.

[CadQuery import and export documentation](https://github.com/CadQuery/cadquery/blob/master/doc/importexport.rst) describes STEP, STL, and DXF support and distinguishes interchange geometry from parametric history. The interface therefore calls STEP a CAD solid and keeps a reproducible project recipe separately.

The intended checks go beyond successful file creation: re-import STEP, verify bounds and positive volume, check mesh closure, and check that planar loops and units survive DXF export. The [validation report](validation.md) records the tests actually executed.

## Continuous-angle rectangular placement

The placement implementation is engineering synthesis using convex support
geometry. [Toussaint's rotating-calipers paper](https://www-cgrl.cs.mcgill.ca/~godfried/publications/calipers.pdf)
describes rotating support lines for convex-polygon problems; the
[SciSpace record](https://scispace.com/papers/solving-geometric-problems-with-the-rotating-calipers-awbxr0c4b6)
was used to locate this primary source. [Shapely's convex-hull documentation](https://shapely.readthedocs.io/en/stable/reference/shapely.convex_hull.html)
defines the enclosing convex geometry used here. This implementation searches
fixed-bed containment rather than simply taking a minimum-area rectangle:
a minimum-area rectangle need not fit the specified bed even when some other
rotation of the outline does.

For model coordinates `(x, y)`, a counterclockwise rotation gives
`x' = x cos θ − y sin θ`, `y' = x sin θ + y cos θ`.
The projected width and depth are the maxima minus minima of these coordinates.
Taking the convex hull leaves those extrema unchanged. Supporting vertices
change only when a hull edge becomes parallel to one bed axis. Between adjacent
events each extent is `a cos θ + b sin θ`, with fixed coefficients.

Solve each bed-limit equality analytically using
`a cos θ + b sin θ = hypot(a,b) cos(θ − atan2(b,a))`.
The roots and support events partition `[0, π]` into intervals where the truth
of both containment inequalities is constant. Check boundaries and interval
interiors to retain isolated exact fits and narrow feasible intervals without
an arbitrary angular increment. Every returned angle is verified again against
all hull vertices. A 1e-6 mm numerical comparison tolerance is explicit.

The bounded implementation scans the hull at each support interval, taking
`O(h²)` time and `O(h)` storage for `h` hull vertices, rather than claiming the
linear complexity of a full rotating-calipers implementation. Polygon input
is limited to 2000 vertices before split intersections. Fitted curves use a
four-corner enclosing rectangle instead of inscribed samples. Negative results
for that conservative rectangle remain inconclusive about the curve itself.
The search checks one piece at a time and leaves all geometry and measurements
unchanged. It does not evaluate slicer placement, physical fit, or printing.

## Bounded split-plan search

Split planning is a finite geometric optimization over
`G = {(c,r) in {1,2,3,4}² : 1 < c*r <= 8}`, containing eleven grids.
Each grid partitions the prepared polygon's bounding rectangle into equal
cells. Intersect each cell with the actual polygon, retain every connected
polygon component, reject invalid results or more than eight pieces, and check
that their total area equals the source area within the existing split tolerance.
Holes and empty cells therefore affect actual piece count rather than being
counted as nominal rectangular tiles.

A grid is feasible only when each piece's thickness fits Z and its actual
polygon can be rotated and translated inside the usable bed rectangle. Rank
feasible grids lexicographically by `(actual_piece_count, c+r-2, r, c)`.
The second term counts straight cut lines. Exhaustively evaluating this small
set finds the minimum under that ranking among grids passing the build's
polygon checks. Numerical intersection failures qualify the search as partial.
The result is a proposal on the current model revision; it changes no geometry
until the user applies the settings and rebuilds.

Before searching angles, reject any convex hull whose area exceeds
`(usable_width + 1e-6) * (usable_depth + 1e-6)`. A convex rectangle containing a
piece also contains its convex hull, so this is a necessary condition for fit.
Including the existing numerical comparison tolerance avoids imposing a
stricter limit than the final directional checks. This prunes obviously
impossible candidates without weakening placement verification.

The search is bounded to eleven grids with at most eight pieces each. It does
not optimize arbitrary partitions or plate packing, nor evaluate strength,
kerf, assembly tolerances or printing. Fitted single-piece curves are excluded
because their split fallback changes exact arcs into polygons; that change
remains an explicit manual decision.

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
