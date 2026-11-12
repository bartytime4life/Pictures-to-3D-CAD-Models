# Research and design decisions

The [known warp-chain study](warp-observations.md) extends the fixed observation
operator to `S G R`, including nonidentity projective/radial maps, explicit border
order and rounding-stage accounting. An independent raw-edge study separates
digital agreement from optical assumptions: affine straight edges permit a
direction-specific Gaussian spread, homographies need spatial variation, and
radially curved boundaries can shift a Gaussian half-level. The
[complete record](validation/warp-observations.md) retains these controls;
none calibrates a real camera or changes production tracing.

The [fixed-observation/covariance investigation](profile-observations.md) now
composes the known finite smoothing filter and final Keys sampler, rather than
assuming one effective continuous Gaussian. A compact SVD accounts for shared
input-pixel noise, retaining support violations and numerical rank decisions.
Its [complete controls](validation/profile-observations.md) show false precision
from independence assumptions and preserve global wall aliases. The known earlier
warp is included by the extension above; calibration of image-derived warp
parameters, camera response and real noise remains separate work.

Related [known-PSF interpolation research](https://scispace.com/papers/optimal-linear-interpolation-of-images-with-known-point-xuwgxkheoe)
considers autocorrelation and aliasing when choosing a linear interpolant.
That literature lead was reviewed at abstract level; this implementation uses
the existing fixed Keys weights and the explicit linear covariance identities,
rather than claiming to implement its optimal interpolant.

The [conditional corner-radius developer tool](corner-feasibility.md) adds a
bounded-error investigation alongside the production methods below. Rectangular
Gaussian probability covers and monotone radius boxes give inner/outer sets
under fixed geometry, blur and supplied level bounds. Its
[development record](validation/corner-feasibility.md) retains unknown cases,
wrong-model rejection and numerical-refinement results. This is a restricted
set-inversion application, not automatic physical uncertainty or a new tracer
correction.

The [shared-blur extension](validation/corner-blur-domains.md) adds one bounded
nuisance domain to that investigation. It distinguishes a radius projection of
joint feasible boxes from independently optimized per-point fits. Intersected
Gaussian density/CDF mass bounds reduce repeated-CDF dependency loss. Wider
domains can still remain unknown; pose, model discrepancy and real-capture
adequacy require separate evidence.

The [pixel-aperture extension](pixel-apertures.md) distinguishes a point sample
from a known normalized uniform rectangle average. A bounded Gaussian-CDF
antiderivative supplies averaged marginal masses to the same nested-cutout
cover and joint-box rules. This follows the physical distinction between
continuous images and pixel integrals studied by
[Chao et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC4523554/), without adopting
their localization-accuracy claims for CAD. Its [development record](validation/pixel-apertures.md)
retains false radius exclusions under center sampling, compatible finite-area
controls and shared-blur unknowns. Uniform product apertures do not model the
workbench's signed Keys resampling or general warped sensor footprints.

The [signed-stencil extension](signed-stencils.md) encloses a declared fixed
linear resampling operator. Actual Keys counterexamples show a signed response
outside the convex hull of its radius-endpoint values, so each aperture term
is bounded over the whole radius box before signed summation. Exact DC/L1
summaries also expose affine normalization and worst-case error gain. The
[development record](validation/signed-stencils.md) retains disconnected outer
sets, unknowns and the calibration boundary; it does not qualify the full image
processor or supply an automatic tracing correction.

[Documentation index](README.md) · [Guided workbench review](validation/guided-workbench.md)

This product starts with a deliberately constrained geometry problem: a photograph can provide a planar boundary, and a user can supply measured scale and thickness. The resulting extrusion is useful for flat parts without pretending that a single image identifies hidden surfaces.

The research below informed the implementation and its acceptance criteria. It is a review of technical and accessibility sources, not a claim that user interviews, a physical metrology study, or a production security assessment have been completed.

The [original selected design reference](images/design-reference.png) is a generated concept. The [recorded workbench screenshot](images/workbench.png) is browser-rendered implementation evidence; the [guided-workbench review](validation/guided-workbench.md) records the reviewed interaction, screenshots and evidence date. The sample photograph is generated demonstration input and is traced by the real conversion pipeline; it is not a measured reference specimen.

## Image to outline

[OpenCV's contour introduction](https://github.com/opencv/opencv/blob/4.x/doc/py_tutorials/py_imgproc/py_contours/py_contours_begin/py_contours_begin.markdown) describes contour extraction from binary images. This supports a visible threshold-and-review stage before geometry construction.

[Contour hierarchy](https://github.com/opencv/opencv/blob/4.x/doc/py_tutorials/py_imgproc/py_contours/py_contours_hierarchy/py_contours_hierarchy.markdown) records nested boundaries. That matters because a part's through-holes must remain distinguishable from its outer boundary. Pixel hierarchy cannot determine whether a photographed dark region is physically a hole; user review remains necessary.

[Contour approximation](https://github.com/opencv/opencv/blob/4.x/doc/py_tutorials/py_imgproc/py_contours/py_contour_features/py_contour_features.markdown) uses a distance parameter to simplify an outline. That parameter controls approximation of the traced pixels. It does not establish the accuracy of the camera, source photograph, or physical measurement.

### Local wall geometry and observation operators

The [wall-localization candidate](wall-localization.md) keeps one fixed local
observation window while expanding geometric hypotheses and updating predicted
width with each candidate. Its failed expanded-window development version exposed
an illumination-model mismatch that reversed the pooled-tone branch and damaged
camera-height inference. The [complete comparison](validation/wall-localization.md)
retains both versions and adverse cases.

A separate developer prototype models the final signed Keys operator as
`y ≈ S D(e) theta`: `D(e)` predicts source basis values at input-array pixel
centres and the fixed matrix `S` applies the actual sampling weights. Linearity
preserves exact source-field aliases. Known pixel means require aperture
integration too. The controls support that supplied final-operator model;
earlier rectification, smoothing, sensor response, curvature and independently
justified observation/model-error bounds remain separate research.

## Known-feature scale and dimensional checks

The workbench accepts either the full outside width or a measured distance between two image points. For the latter, the Euclidean pixel distance defines one millimeter-per-pixel factor, applied to both axes. Endpoints use the orientation-adjusted working-image coordinate frame, not the resized browser preview. The measured reference, endpoints, and frame are retained separately from the resulting outside width and intentional design percentages.

[OpenCV's homography tutorial](https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html) describes the projective relation between planes and its use for perspective correction. [Its camera-calibration tutorial](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html) treats camera parameters and radial/tangential distortion separately. A single known length supplies uniform scale; it does not supply either correction. This motivates the front-facing capture guidance, same-plane reference requirement, and explicit warning about short references.

An optional measured outside height is compared with the source-profile estimate before design scaling. It does not enter the scale calculation or adjust geometry. A measurement used to set scale cannot also provide an independent test of that scale. If a reserved check is used to correct the model, it becomes development evidence for the revised model; retain the earlier result and seek a fresh check. The [independent-check worksheet](../reference-library/templates/INDEPENDENT-CHECKS.md) records that distinction.

[JCGM 100:2008 (GUM), sections 3.1–3.3](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf) explains why a measurement result needs an uncertainty statement and why several effects can contribute. Here those effects can include physical reference measurement, endpoint placement, trace approximation, perspective, and lens distortion. The height comparison reports a signed difference and, when the user supplies an allowance and an absolute measurement error bound, a conditional interval decision for that one source dimension. This is not a numerical uncertainty budget or a manufacturing pass; [engineering model and verification](engineering-model.md#bounded-source-height-decision) gives the decision rule and its limits. Synthetic coordinate/export checks test the calculation and preservation of inputs; a measured-photo benchmark remains necessary to quantify physical performance.

## Reference sheet, sub-pixel edges and fitting

The reference-sheet stages are documented with their derivations and checks in [reference-sheet tracing](reference-sheet.md). The main sources and results they rely on:

- Plane homography and camera pose from a plane: [OpenCV's homography tutorial](https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html); the two orthonormality constraints on the rotation columns are those of [Zhang's plane-based calibration](https://www.microsoft.com/en-us/research/publication/a-flexible-new-technique-for-camera-calibration/) (2000), here used with one image and a known principal point to solve only the focal length.
- Radial distortion from straight lines (the plumb-line method): D. C. Brown, "Close-range camera calibration", *Photogrammetric Engineering* 37 (1971). The model inverse uses safeguarded Newton/bisection on its central branch; [domain and numerical checks](validation/radial-inverse.md) are separate from this historical method reference.
- Tone curve: the sRGB transfer function of IEC 61966-2-1:1999, in the form given by the [CSS Color Module Level 4 conversion code](https://www.w3.org/TR/css-color-4/#color-conversion-code). Display P3 uses the same curve. Edges are measured after undoing it, because blur and partial pixel coverage mix light linearly.
- Cubic convolution interpolation: [Keys (1981)](https://doi.org/10.1109/TASSP.1981.1163711), whose a = −½ kernel reproduces quadratics.
- Circle fitting: the Kåsa algebraic fit refined by Gauss–Newton on geometric distance; see N. Chernov, *Circular and Linear Regression: Fitting Circles and Lines by Least Squares* (CRC Press, 2010) for bias and precision.
- The normal CDF is evaluated with [Abramowitz & Stegun 7.1.26](https://personal.math.ubc.ca/~cbm/aands/page_299.htm) (|erf error| < 1.5 × 10⁻⁷).
- Algebraic identities are checked in exact rational arithmetic at seeded, sampled rational points. These checks avoid floating-point cancellation and can expose counterexamples; they are not formal proofs that an identity holds for every input. The [Schwartz–Zippel lemma](https://en.wikipedia.org/wiki/Schwartz%E2%80%93Zippel_lemma) provides related background, but a numerical failure-probability claim would require explicit polynomial-degree and sampling-set bounds that this report does not establish.

The blur–curvature series, its third-order coefficient (5/24), the two-step wall model and its degeneracy, the sheet-proportions check, the size of the tone-curve bias and the shift a sloped shadow causes were derived for this workbench and checked numerically; they are not taken from a cited source.

### New findings and research candidates

The [November 11 scientific model review](validation/scientific-model-review.md)
records reproducible limitations at `5588a52`, their evidence level and acceptance
checks for future changes. At that baseline a thin circular segment became a whole circle;
directional blur can bias accepted geometry; and greedy benchmark matching can
hide valid comparisons. These findings were unresolved at that baseline; the documentation update
did not deliver new algorithms. The subsequent [initial-fit support repair](validation/fit-support.md)
adds separate center/coverage evidence and a complete assembled-boundary check.
It keeps coverage points separate from precision measurements, and runs before
physical reconstruction; final forward-model adequacy remains further work. The
[benchmark repair](validation/benchmark-correspondence.md), merged in PR #43,
adds global correspondence and complete dimension accounting; physical feature
identity and independent measured-photo evaluation remain separate limits.

The merged [fillet-sector repair](validation/fillet-sweep.md) preserves an arc's
angular witness when its constrained center moves. Its independent anisotropic
sharp-corner example still fits nonzero fillets after the representation defect
is repaired. Topological validity, consistent arc sectors and forward-model
adequacy are separate checks; the scalar Gaussian interpretation remains a
research limit.

[Al-Sharadqah and Chernov's circle-fit analysis](https://arxiv.org/abs/0907.0421)
compares geometric and algebraic fits with coordinate errors. It motivates
examining estimator assumptions; it does not establish that a low-residual
circle covers the photographed boundary. A source-support guard needs its own
geometric counterexamples and regression tests.

The synthetic lens renderer previously called the production inverse. The
[radial-domain repair and independent simulation](validation/radial-inverse.md)
remove that code dependency, check both implementations against high-precision
brackets and add a test-only higher-order lens term. The six mismatch cases
show that low sheet residuals need not bound reserved part dimensions.
Independent physical cameras remain necessary: [Wirgin's discussion of inverse
crimes](https://arxiv.org/abs/math-ph/0401050) concerns reuse of the model as well
as code when generating and inverting test data.

Automatic tone recovery is a research candidate, not a reliable default for an
arbitrary part photo. [Lin, Gu, Yamazaki and Shum's single-image method](https://www.gujinwei.org/research/radiocalib/index.html)
uses selected RGB-edge distributions and a response prior; its project record
requires enough edges spanning the intensity range. A scene dominated by one
part color and one paper color need not supply that evidence. The current
pipeline continues to decode sRGB under its stated assumption.

### Directional-blur experiment status — November 12, 2026

The following 13-case experiment is historical development evidence. A later
[frozen 30-case qualification attempt](validation/directional-spread-qualification.md)
at `2d76aea` found orientation-imbalanced false negatives and additional unknown
outcomes. No production blur warning or anisotropic correction was added.

A local exploratory diagnostic was rerun against committed `eec45d0`, excluding
the initial-fit support candidate. It estimates an empirical image-plane blur
covariance from normal-profile variances and the local rectification Jacobian:
`s_i² − 0.7² = (J_iᵀ n_i)ᵀ Σ (J_iᵀ n_i)`. The subtracted term is the known
rectified smoothing variance. At least three independent orientation equations
are needed for the symmetric covariance's three unknowns; two perpendicular
straight-edge directions cannot determine its cross term. Fit rank, conditioning,
profile rejection and residual thresholds are exploratory eligibility checks,
not confidence levels or calibrated optical-PSF measurements.

For a locally curved boundary with centered Gaussian covariance Σ in its
normal/tangent frame, the leading half-level displacement derived for this
experiment is `κ/2 × (Σ_tt − Σ_tn²/Σ_nn)`. Substituting normal variance alone
loses the conditional-tangent term. This specializes the tangent-plane expansion
in [Elsey and Esedoğlu's anisotropic threshold-dynamics paper, appendix](https://websites.umich.edu/~esedoglu/Papers_Preprints/elsey_esedoglu_anisotropy.pdf).
An independent Gaussian-circle integral, using standard-library `erf` and
quadrature rather than backend rendering/fitting routines, was checked on 24
cases. Doubling quadrature order from 320 to 640 changed the computed shift by
at most `2.85 × 10⁻¹³` in its pixel coordinates. Quadrature convergence does
not establish end-to-end photo accuracy or bound the leading-order expansion.

Across 13 frozen synthetic cases, both Keys and bilinear diagnostic sampling
flagged six directional-blur cases and left seven other cases unflagged. These
previously examined cases are not a new independent evaluation set. The proposed
circle-radius correction still worsened the earlier held-out rotated-blur case:

| Absolute error (mm) | Unmodified `eec45d0` trace | Experimental Keys-based correction |
| --- | ---: | ---: |
| Small-hole diameter | 0.035454 | 0.042050 |
| Bore diameter | 0.035211 | 0.036602 |

Bilinear-based correction also worsened both errors. A gamma-1.8 tone-mismatch
control remained unflagged despite 0.086840 mm small-hole and 0.118973 mm outer
errors. An absent directional flag therefore cannot mean accurate geometry.
The candidate remains research only: no diagnostic or covariance correction
has been added to the product. It needs fresh nuisance/PSF cases, explicit
unknown outcomes and independent captures before any production reporting.

Ignored local scripts and hash-bound JSON receipts are retained under
`.local/verification/directional-blur-current-eec45d0*`; they are not bundled
reproducibility artifacts. At that pinned revision the synthetic renderer shared
the production radial inverse, and feature measurement shared arc reconstruction.
The independent integral checks one mathematical subproblem. The separate lens
repair above does not retrospectively change these experiment inputs or results.

### Directional-spread qualification decision

The frozen 30-case follow-up produced 27 traces: 6 flagged, 16 eligible-unflagged
and 5 ineligible; 3 failed tracing. A long rectangle contributed 90 accepted
profiles near one direction and only 11 near the perpendicular direction. A
pooled median residual of 0.00839 hid a minority-direction median of 5.87425.
Removing that median gate would also flag an isotropic rectangle. Numerical
rank and conditioning therefore did not establish adequate orientation support.
Two perpendicular straight-edge normals cannot identify a covariance cross
term; sampled corner directions do not automatically supply valid independent
straight-step equations. The [complete research record](validation/directional-spread-qualification.md)
preserves all outcomes, the algebraic counterexample, artifacts and next steps.

Keep the diagnostic in research. A successor needs orientation-balanced
summaries, valid local support and explicit unknown states, specified before a
fresh cohort. The 30 examined cases are now development evidence. An unflagged
diagnostic cannot establish accurate geometry or a Gaussian optical cause.

### Corner resolution, adequacy and feasible radii

The [corner-resolution review](validation/sharp-corner-resolution.md) separates
two questions: whether a numerical search brackets its threshold, and whether
the assumed blur model explains the observations. The search now checks its
final upper endpoint and reports exhaustion as unresolved. Its estimate is
explicitly conditional on the blur model; this does not implement an absolute
adequacy test. An independent rounded-corner example retains a resolution
estimate smaller than its known radius when that model is mismatched.

[Jaulin and Walter (1993)](https://webperso.ensta.fr/jaulin/paper_automatica93.pdf)
infer parameter sets whose discrepancies from observations fall within prior
error bounds, using interval enclosures over complete parameter boxes.
[Brynjarsdóttir and O'Hagan (2014)](https://www.tonyohagan.co.uk/academic/abs/simmach.html)
show why calibration parameters can be confounded with model discrepancy.
These primary sources motivate the implemented [conditional radius sets](corner-feasibility.md)
under their fixed-model assumptions, including supplied shared blur domains,
known pixel apertures and declared signed stencils. Broader sets with separately
justified model-discrepancy, pose and other nuisance domains remain future work.
They do not validate this workbench's optical assumptions or turn its current
standard deviations into maximum-error bounds. A sampled radius grid cannot
certify that no compatible radii exist between samples.

### Material gradients in actual edge profiles

The [repeatable material-gradient study](material-gradients.md) uses an independent
bounded piecewise-affine Gaussian convolution and uniform pixel means, followed
by actual tone decoding, Keys rectification, smoothing, blur estimation and
crossing functions. It separates spatial lighting slopes from a common gain and
offset, which cancel in fixed accepted profile crossings. It retains both slope
treatments and every low-contrast rejection; the two-affine branch is an ablation,
not a qualified correction. The [development record](validation/material-gradients.md)
keeps the stage boundaries and wall/edge confounding explicit.

[Debevec and Malik (1997)](https://people.eecs.berkeley.edu/~malik/papers/debevec-malik97.pdf)
recover radiometric response using differently exposed photographs and known
exposure ratios. [Grossberg and Nayar (2002)](https://www.cs.columbia.edu/CAVE/publications/pdfs/Grossberg_ECCV02.pdf)
analyze ambiguities in recovering that response from image brightness transfers.
These primary sources support treating a camera response as a separate model;
they do not establish that this workbench's sRGB decoding calibrates a particular
phone, or that single-profile affine normalization undoes spatial illumination.

### Nearest local crossing and numerical predicates

The [nearest-crossing rule](edge-crossings.md) compares actual piecewise-linear
root distances. Strict brackets and confirmed isolated zeros are distinguished
from unresolved target-level contacts; equal minima do not justify averaging.
[Shewchuk (1997)](https://www.cs.cmu.edu/~quake/robust.html) explains how roundoff
near a predicate boundary can alter geometric decisions. That motivates exact
binary-data rational comparison for competing candidates here, not adoption of
the paper's orientation/incircle implementation or performance claims.
The [verification record](validation/edge-crossings.md) includes an independent
3,888-case contact/mask enumeration, direct image counterexamples and the prior
cohort's preservation check. Represented-sample correctness remains distinct
from physical edge identification and photometric/model discrepancy.

### Joint wall and lighting identifiability

The [bounded wall/lighting study](wall-gradients.md) uses five physical source
node levels and Gaussian convolution. Nonnegative source bases sum to one, so
box constraints keep the entire source bounded. At each supplied geometry,
SVD-based face enumeration fits these linear nuisance parameters; a finite
grid supplies constructive geometric alternatives. The independent source
quadrature and convex-optimality checks are retained in the
[verification record](validation/wall-gradients.md).

This follows the variable-projection principle reviewed by
[O'Leary and Rust](https://www.cs.umd.edu/users/oleary/software/varpro.pdf): solve
linear coefficients conditionally on nonlinear parameters. It does not implement
their full nonlinear optimizer, infer an error distribution or turn a design
matrix condition number into geometric confidence. The five-node derivation
and exact wall-label ambiguity are local model results developed here.

With flat top/paper levels `C,A`, wall width `w`, the interpretations `(e,B=C)`
and `(e+w,B=A)` define identical source fields. A fixed known width alone does
not remove that discrete ambiguity. A constructed midpoint between nearby
predictions also demonstrates finite-error ambiguity; it is a different
observation from the original truth samples. Neither result supplies a physical
camera-noise prior, complete camera-scene construction or automatic correction.

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
is limited to 2000 vertices before split intersections. Fitted curves first use
a four-corner enclosing rectangle, then the conservative curve enclosure below.
Negative results for either bound remain inconclusive about the curve itself.
The search checks one piece at a time and leaves all geometry and measurements
unchanged. It does not evaluate slicer placement, physical fit, or printing.

## Conservative fitted-curve placement

The following is an engineering derivation using supporting half-planes.
[CGAL's halfspace-intersection documentation](https://doc.cgal.org/latest/Convex_hull_3/)
provides related computational-geometry background. SciSpace located
[Richardson's support-probe approximation paper](https://scispace.com/papers/approximation-of-planar-convex-sets-from-hyperplane-probes-3os7ldt596)
as further reading; this implementation uses fixed directions and does not claim
that paper's adaptive algorithm or approximation rate.

For a unit normal `u = (cos φ, sin φ)`, define support
`h(u) = max { dot(p,u) : p on the fitted outer boundary }`.
A line contributes the maximum of its endpoints. A circle with centre `c`
and radius `r` contributes `dot(c,u) + r`. A circular arc contributes that same
value when `φ` lies in its signed radial sweep; otherwise its maximum occurs
at an endpoint. This handles clockwise and counterclockwise sweeps, including
major arcs and sweeps crossing zero. Holes cannot increase any extent.

Every point of the actual solid satisfies `dot(p,u) <= h(u)`. Intersect those
supporting half-planes for 256 equally spaced normals. Unlike an inscribed
polygon made from sampled curve points, this intersection contains the whole
curved boundary between normals. Adjacent supporting lines give its vertices.
With step `δ = 2π/256` and tangent `t_i = (-sin φ_i, cos φ_i)`, their intersection is
`h_i u_i + ((h_(i+1) - h_i cos δ) / sin δ) t_i`.
The discretized support inequality
`h_(i-1) + h_(i+1) >= 2 cos δ h_i` keeps these intersections in convex cyclic
order. Computation uses a local origin and adds 1e-6 mm to each support for
outward numerical padding. This is not a manufacturing allowance.

The existing continuous-angle solver searches rotations of the resulting
outer polygon and verifies the returned witness against all its vertices.
Containing this polygon contains the exact curved solid. Failure remains
unknown because a finite outer enclosure may exclude a valid tight placement.
Before reporting a new curved placement, the worker also rotates a temporary
copy of the exact CAD solid and checks its kernel bounding box against both
the bed limits and the reported conservative footprint. An unconfirmed witness
is withheld as unknown; the original solid and exports retain their orientation.
Measurements, normalization offsets and this final witness check use
`BRepBndLib.AddOptimal` with triangulation disabled. The
[OCCT 7.8.1 API declaration](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_8_1/src/BRepBndLib/BRepBndLib.hxx)
was checked against the OCP wrapper during the recorded curved-placement work
(see [that validation record](validation/curved-placement.md)). This prevents cached STL/viewport
triangulation and its deflection allowance from inflating geometric dimensions.
The fixed directions bound geometry approximation; they are not fixed trial
placement angles. No universal enclosure-error or physical accuracy is claimed.

For `s` fitted segments, support evaluation costs `O(256s)` with `O(256)`
temporary storage. The resulting hull has at most 256 vertices, bounding the
subsequent `O(h²)` placement search. Polygon outlines and the 2000-segment input
limit retain their existing behavior. Numerical enclosure failures leave CAD
intact and report unknown. Curved splitting remains a separate explicit choice.

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

The [guided next-step flow](validation/guided-workbench.md) derives its action from the
available outline, valid source measurements, design settings and current build
revision. It distinguishes entering measurements from rebuilding stale geometry;
it does not convert CAD readiness into a physical verification result. The export
dialog groups CAD and mesh files first and leaves drawings/source files in a
separate disclosure. If optional height notes prevent saving, the interface opens
the measurement check and focuses the input needing attention while retaining
the current CAD model.

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

## Conditional source-space edge fitting

The [raw-source tool](raw-source-fit.md) separates one nonlinear plane-edge offset
from two bounded linear brightness levels. A known lens-free homography transforms
the candidate line into raw coordinates; a supplied raw Gaussian covariance
sets its optical probability. Both the available source samples and predicted
means use `V^T D^-1` from the same retained sampling/noise factor. This avoids
inverting weak processed modes while preserving the declared information choice.
The [complete controls](validation/raw-source-fit.md) keep rounding, encoding,
wrong-PSF/nonlinear response, flat/tied searches and invisible raw-source mismatch.
This remains conditional developer inference, not production correction or
physical uncertainty. Unknown optics, radial/curved edges, data-derived geometry
and global wall identity need further evidence.

## Conditional common-response consistency

The [response tool](response-calibration.md) uses exact chain reachability for
one scalar nondecreasing function with supplied exact abscissae and closed
output/slope bounds. Forward/backward interval propagation gives tight marginals;
a common piecewise-linear witness proves existence. Duplicate inputs share one
value. General exact difference-constraint closure supplies an independent oracle.

For an affine Gaussian edge, changing position/spread can be absorbed into a
reparameterized monotone response. The [finite controls](validation/response-calibration.md)
retain this ambiguity and show how independently supplied patch/slope assumptions
restrict represented alternatives. Wrong calibration, quantization and channel/
spatial/stage violations remain adverse results. No response is learned from
one unknown edge, and exact finite inputs do not certify a continuous Gaussian
integral or physical camera calibration.

The [bounded-input response extension](response-rectangles.md) distinguishes
existential and every-input rectangle constraints and supplies outward
mathematical CDF covers. The [continuous domain extension](gaussian-response-domains.md)
uses those tests plus Gaussian order invariants to enclose a shared offset/sigma
feasible set. It preserves full closed-box coverage and unresolved regions;
separate interval projections do not retain joint correlation. Its
[complete development record](validation/gaussian-response-domains.md) includes
order-only gauges, refinement and a thin feasible line. This is set inversion
under supplied models, with no general convergence or physical-accuracy claim.


## Stable tangent-circle geometry

A rounded end between distinct nonparallel lines does not have constant width.
The [tapered-cap repair](validation/tapered-caps.md) preserves its two signed
distance constraints. For unit line normals collected in rows of `N`, signs
`s`, observed circle `(C*,r*)` and signed distances `d` from `C*` to the lines,
solve

```text
shift = solve(N, r* s - d)
v = solve(N, s)
anchor = C* + shift
C(r) = anchor + (r-r*) v
```

Changing a line anchor along its direction leaves its geometric constraint
unchanged. Subtract coordinates before taking the normal dot product, and keep
the reference radius instead of subtracting a distant virtual apex from `r v`.
Near parallelism, a small radius increment can still move the centre by
`abs(delta_r) norm(v)`. The stopping rule includes that movement; a radius-ulp
movement larger than the fit tolerance leaves the constraint unresolved.
Those are arithmetic/representation checks, not physical uncertainty bounds.
Roundoff-level parallel directions retain their separate constant-width cap model.

## Finite-shape source prediction

Local half-plane or isolated-circle corrections omit light contributed by a
nearby chord, corner, opposite boundary or hole. A circle-consistent export can
therefore remain inconsistent with the source image. The
[finite-shape developer model](finite-shape-source.md) integrates the entire
projected region under a supplied Gaussian PSF before point sampling. Its
boundary-flux quadrature preserves far-boundary winding contributions and
resolves near-boundary travel before accepting embedded-order agreement.

The conditional circular-segment fitter jointly searches radius and chord
fraction with fixed pose, raw covariance and source/noise support. Bounded
brightness is profiled at every geometry; local domain-scaled Gauss–Newton steps
use actual profiled-cost backtracking. Error estimates and local ranks remain
numerical diagnostics. Pixel apertures, unknown radiometry, joint camera/PSF
inference and production source-context capture remain separate work.

## Circle-consistent joins and minimum-edit cycles

The [canonical-arc candidate](validation/canonical-arcs.md) repairs the separate
free-arc representation defect retained in the [tapered-cap record](validation/tapered-caps.md#regression-scope-and-remaining-work).
For fixed centre `C`, radius `R`, unit line direction `d` and perpendicular
distance `h`, intersections are absent for `h > R`, tangent for `h = R`, and
`F ± s d` for `h < R`, where `F` is the perpendicular foot and
`s = sqrt((R-h)(R+h))`. The product form avoids cancellation in `R²-h²`.
Near contact, `ds/dR = R/s`: tiny distance errors can produce square-root-scale
endpoint changes. A linear radial guard is not an endpoint-accuracy guarantee.

Ordered source endpoints are frozen after fitting/trimming; signed source sweep
and an interior angular witness preserve traversal and major arcs. For one
source endpoint `P`, the squared endpoint-displacement objective has reduced
costs `±2s d·(F-P)` after removing the candidate-independent terms. Both adjacent
primitives contribute a witness at each join. A cyclic dynamic program enforces
line progress and arc winding while minimizing additive score bounds. A winner
must have an upper score below every distinct competitor's lower score.
Numerically unresolved compatibility remains a competitor; it cannot be
silently discarded to manufacture uniqueness. Work limits retain unknowns.

These are engineering arithmetic guards, not certified exact constructions or
physical uncertainty bounds. A narrow observed-tangent normalization exists
only for prescribed tangent constraints and an explicit design-intent attempt
whose original circle already reaches both lines to roundoff precision. Free
near-contact cases remain unresolved unless represented tangency is exact.
The selected three-point circle is checked in local coordinates against stored
`C,R`; the complete boundary still needs its separate validity check.

Source partition endpoints include blurred transitions. Their unique minimum
is only an algorithmic choice. Hard containment of all old arc angles is also
incorrect: changing a radius at a fixed chord legitimately trims angular
support. Finite Gaussian D-shape controls retain both polyline outcomes and
nonzero shape error; consistent exports do not qualify a blur model or camera.

The distinction between predicates and constructions follows established
computational geometry practice. [Shewchuk's robust-predicate work](https://www.cs.cmu.edu/~quake/robust.html)
explains why near-zero geometric tests require care; the
[CGAL circular-kernel design](https://doc.cgal.org/latest/Circular_kernel_2/index.html)
separates circle/arc objects and intersection constructions and provides an
exact circular kernel. This implementation uses neither CGAL nor that exact
construction guarantee. No dependency or physical calibration follows from
these references.
