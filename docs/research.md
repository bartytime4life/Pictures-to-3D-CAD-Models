# Research and design decisions

[Documentation index](README.md) · [Guided workbench review](validation/guided-workbench.md)

This product starts with a deliberately constrained geometry problem: a photograph can provide a planar boundary, and a user can supply measured scale and thickness. The resulting extrusion is useful for flat parts without pretending that a single image identifies hidden surfaces.

The research below informed the implementation and its acceptance criteria. It is a review of technical and accessibility sources, not a claim that user interviews, a physical metrology study, or a production security assessment have been completed.

The [source-scope guide](project-status.md) identifies which algorithms are in
this main-based checkout. Source-space PSF research on a separate lineage
does not replace the production rectified-width estimator or add new HTTP modes.

The [residual-information study](finite-residual-information.md) tests local
blur/geometry confounding at saved fits. Its [complete failed protocol](validation/finite-residual-information.md)
retains stable covariance sensitivities and unknown normal columns. A separate
post-hoc rotation identity is consistent with the observed finite-difference step
scaling; it does not replace the original failed normal control or identify a
physical PSF. A further [finite-chord derivation](finite-residual-information.md#finite-chord-shape-derivative-a-derived-proposal)
covers affine and projective maps under a fixed, supplied Gaussian observation
model and a valid whole-shape projective chart. The
[experimental operator](finite-normal-derivative.md) now has a
[complete failed qualification](validation/finite-normal-derivative.md): one
panel-budget unknown and a compressed-map error-estimation limitation remain.
It adds no automatic correction.

Later [analytic-normal results](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/blob/0f1adbd391f7fa015f458cca60dcfe2a0e2dad9e/docs/validation/finite-analytic-normal-information.md)
belong to their pinned research branch. They do not replace this checkout's
failed qualification or establish that smaller residuals improve geometry.

The [known acquisition-operator audit](finite-acquisition-operator.md) now
packages completed evidence from source `0714aad`: 16 new synthetic scenes,
32 output-scale records and 128 stage/Gaussian comparison cells. At supplied
true geometry and levels, moment matching leaves 9/32 unquantized comparisons
incompatible; the PNG lane has 15 compatible, 16 incompatible and one
inconclusive comparison. The nominal PNG comparator has 27 incompatible and
five compatible comparisons. The [full record](validation/finite-acquisition-operator.md)
preserves both the pre-capture bootstrap failure and the raw report's 320
scalar-serialization failures; a saved-only native conversion changes no category.
The [archive](../studies/fixtures/finite-acquisition-operator-v1/README.md)
includes the 87-file recorded source, separately from current main's newer
shadow-lighting model. These forward-only findings support an acquisition-aware
mean before fitting more parameters. They neither recover geometry, explain
historical fit errors nor qualify current-main automatic tracing.

The subsequent [source-cell acquisition mean](finite-acquisition-mean.md) is
now an experimental developer API. It integrates analytic finite-D cell coverage
and applies supplied kernels, levels, a known affine map and explicit encoding.
The [complete qualification](validation/finite-acquisition-mean.md) passes all
128 comparisons over the same 32 saved output records, with no changed encoding
codes. Analytic-D query discrepancies are at most 0.0000763 unquantized and
0.0000306 sRGB8 intensity levels. The
[portable archive](../studies/fixtures/finite-acquisition-mean-v1/README.md)
retains the first failed controls, initial audit arithmetic mismatches and a
separate workspace-accounting repair. These are supplied-stage forward checks,
not new captures, geometry recovery or physical camera qualification.
The subsequent [cell-sensitivity and fixed-linear qualification](validation/finite-cell-sensitivity.md)
now checks all five area columns and their signed intensity propagation in a
separate unrounded model. These operators are available in main; the new
[acquisition-aware recovery prototype](finite-acquisition-recovery.md) remains
on separately frozen local source, outside this checkout's runtime.
Its first 24-row protocol at `7ec6803` passes 4/12 matched cases; the continuation
at `e6e2c2` passes 9/12, comprising four smooth, four float32-staged and one PNG
case. Both protocols retain all 12 adverse rows and exit **1**. Three PNG cases
still miss the unchanged targets despite local stopping, and every matched PNG
case retains tied represented candidates. The **459 focused tests** qualify
separate software controls, not general recovery or camera accuracy.
The [complete record](validation/finite-acquisition-recovery.md) also preserves
the original study's first saved-audit failure: 14 pre-cast float64 area-order
differences cannot be reconstructed from the saved rounded float32 coverage.
No independent audit success, automatic tracing or GUI/HTTP integration follows.
The [API contract](finite-acquisition-mean.md#refusals-provenance-and-work)
now states the input ranges, exact hash inputs, failure behavior and corrected
workspace formula. Its unquantized path still stores float32 values. Any
smooth derivative or separable brightness model must distinguish its unrounded
operator from this executable chain, preserving the computed constant response.

The later [coupled search](finite-acquisition-coupled.md) reaches **11/12**
matched target passes; the [source-event continuation](finite-acquisition-events.md)
stays at **11/12**. Both complete 24-case protocols still exit 1. Their first
focused suites pass 548 tests/nine subtests and 653 tests/21 subtests, respectively.
The [completed results](validation/finite-acquisition-continuations.md) and
[saved-only audits](finite-acquisition-saved-audit.md) retain the remaining PNG
miss, first failures and 28 historical precision unknowns. Candidate code and
complete local ZIPs remain separate from this main runtime and workbench UI.

The [protected-source-bin design](finite-acquisition-protected.md) retains its
eight failed first controls. The later
[exact active-face implementation](finite-acquisition-protected-active.md) records
**820 passes, one failed test expectation and 33 passing subtests**, exit 1.
Its fixture supplies 16 constraint rows, while the assertion expects 15.
The [first outcome and evidence](validation/finite-acquisition-protected-active.md)
remain unchanged; a separate control-only correction is pending. Neither
protected full recovery study has run. This adds no application integration.

The [original selected design reference](images/design-reference.png) is a generated concept. The [recorded workbench screenshot](images/workbench.png) is browser-rendered implementation evidence; the [guided-workbench review](validation/guided-workbench.md) records the reviewed interaction, screenshots and evidence date. The sample photograph is generated demonstration input and is traced by the real conversion pipeline; it is not a measured reference specimen.

## Image to outline

[OpenCV's contour introduction](https://github.com/opencv/opencv/blob/4.x/doc/py_tutorials/py_imgproc/py_contours/py_contours_begin/py_contours_begin.markdown) describes contour extraction from binary images. This supports a visible threshold-and-review stage before geometry construction.

[Contour hierarchy](https://github.com/opencv/opencv/blob/4.x/doc/py_tutorials/py_imgproc/py_contours/py_contours_hierarchy/py_contours_hierarchy.markdown) records nested boundaries. That matters because a part's through-holes must remain distinguishable from its outer boundary. Pixel hierarchy cannot determine whether a photographed dark region is physically a hole; user review remains necessary.

[Contour approximation](https://github.com/opencv/opencv/blob/4.x/doc/py_tutorials/py_imgproc/py_contours/py_contour_features/py_contour_features.markdown) uses a distance parameter to simplify an outline. That parameter controls approximation of the traced pixels. It does not establish the accuracy of the camera, source photograph, or physical measurement.

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
adequacy are separate checks. That scalar-model counterexample is historical;
the covariance-aware replacement below addresses its nonparallel-corner model
without establishing general physical-camera adequacy.

The main-line directional path now supplies normal-specific edge/wall widths and
directional slot-end shrink, with [numerical rank rejection](validation/directional-blur-rank.md)
in the preceding rank-repair candidate. The [new nonparallel-corner model](anisotropic-corners.md)
now uses the full covariance and transports the corner geometry into a whitened
Gaussian frame. Its [independent fixed experiment](validation/anisotropic-corners.md)
reproduces scalar-model bias and retains numerical refusals, weak-radius controls
and the remaining physical-model limits. General free curves and slot caps retain
their separate approximations; this does not import the source-space research stack.

Merged PR #107 also uses measured widths per supported direction when the
covariance fit is unavailable. Two-direction parts can therefore improve their
edge searches without identifying a full covariance. A matching covariance
used for paper-shadow blurring is not supplied to corner/curve correction;
those paths retain their scalar model. The
[current method and recorded synthetic comparisons](reference-sheet.md#3-segmentation-and-sub-pixel-edges)
supersede the historical one-width fallback described below.

The [blur-frame follow-up](blur-frames.md) distinguishes a coordinate error from
those model errors. A known uniform map transports `sigma` by `k` and covariance
by `k²`; the radius series is homogeneous only when both radius and spread move
to the same frame. A predeclared independent finite-disk/capsule experiment
tests stored-geometry transport, while reporting the remaining short directional
free-arc bias separately. Its [complete record](validation/curve-blur-frames.md)
also retains a rejected topology-cleanup probe: close source coverage alone did
not satisfy the original independent size limit. Mixed scalar corners retain
an explicit geometry hypothesis with unresolved radius uncertainty, rather than
claiming one stationary PSF across both maps.

The [partial-arc follow-up](validation/directional-free-arcs.md) tests both the
represented final circle and alternative directional forward fits. A complete
closed-outline witness shows that the historical line-foot/midpoint assembly can
serialize a different circle from the stored fit, even with valid topology. The
canonical join repair is a prerequisite for interpreting a fitted radius as the
radius in CAD; it does not remove the optical model's bias. Separate prospective
finite-Gaussian comparisons retain threshold/material mismatch and short-support
conditioning. A derived angular `R^-3` shrink term is exploratory, and the exact
whole-disk level-set model is conditional research rather than an automatically
selected model for an arbitrary circular boundary span.

The later [finite-material intensity inverse](finite-shape-inverse.md), introduced
in PR #88, models the complete circular segment, including its closing
chord, and fits centre, radius and chord fraction from fixed pixel intensities.
Supplied optics and a bounded two-level variable-projection solve keep model
assumptions explicit. Its [independent positive-area experiment](validation/finite-free-centre.md)
retains 12 matched recovery passes and a failed planned aperture-order comparison.
Captured-field initialization and mismatch failures remain separate. The
[moment study](validation/finite-moment-photo.md) explores blur-invariant third
central moments under centered symmetric convolution, with strong observed
background sensitivity. Neither result supplies automatic optical calibration
or replaces the workbench's current tracing path.

PR #91 adds an [immutable measured-ring preparation contract](finite-shape-inverse.md#prepare-a-measured-ring-observation-set)
and a [paired replay of saved measurement fields](validation/finite-photo-intensity-v2.md).
It completes all ten available fits; three of twelve declared case/lane records
meet every original target and two retain their upstream refusal. Both the crop
and the shared-width preparation policy differ from version 1, so this is not a
crop-only ablation. Held-out samples are excluded from fitting cost but influence
initialization and moments. The remaining intensity mismatches and 8–19 second
fit times belong to that original source. The subsequent
[affine batch experiment](validation/finite-affine-batch.md) uses the same
archived observations, targets and full-fit settings: mean evaluation improves
10.13× and complete fits 3.84× across the declared timing workloads. All 36
original/paired rows and completion flags remain present; acceleration does
not resolve the retained optical mismatches or qualify interactive use.
The [derivation](finite-affine-evaluation.md) explains shared transformed
panels, exact perspective fallback, numerical guards and charged work.

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

### Directional blur in the tracer — November 12, 2026

This subsection records the earlier covariance path. PR #107's later
[two-direction repair](reference-sheet.md#3-segmentation-and-sub-pixel-edges)
also supplies measured edge widths when that covariance is unavailable;
the historical fallback statements below do not describe every current edge search.

The tracer measures a blur that differs by direction as a covariance S from its edges' widths (σₙ² = nᵀSn in the rectified image) and, above a principal-spread ratio of 1.15, traces each edge with its own σₙ; [reference-sheet tracing](reference-sheet.md), §3, has the method and results. It is not the research diagnostic above, and it answers that qualification's findings with rules of its own:

- **Orientation support.** The qualification's long rectangle gave 90 profiles one way and 11 the other. The fit counts a direction only with 15 clean profiles in a 30° bin and needs three such bins, so a sharp-cornered rectangle is never fitted; its isotropic rendering, which the diagnostic's tensor read 2.1 times wider one way, keeps one width. Counted bins weigh the same.
- **Minority disagreement.** Each bin's median residual is judged alone, against 10 % and three of its own standard errors, so a dominant direction cannot hide a minority one; an inadequate fit keeps one width.
- **Unclean profiles.** Corners and thin holes whose profiles reach another edge are left out, which the qualification noted sampled corner directions need.
- **Non-Gaussian and spatial blur.** Motion streaks of 6 and 10 px passed and traced better; defocus disks are isotropic. Spatially varying blur and sharpening were not tested.

Its curvature term is the experiment's leading displacement: Σ_tt − Σ_tn²/Σ_nn = det S / nᵀSn, which averages √det S round a circle, so circles are corrected with (det S)^¼. Correcting curvature alone did not help (a curvature-only σ made a 1 × 3 px render's outline worse, 0.106 against 0.038 mm); the level search across each edge is what needs σₙ, which is consistent with the experiment's radius-only correction worsening its rotated case. The cases come from this repository's renderer, including ones built for this check, so they are not the independent evaluation the qualification asked for; real shaken captures are needed next.

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
