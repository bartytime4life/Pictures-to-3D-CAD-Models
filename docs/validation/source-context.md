# Real-trace source context: digital integration evidence

This candidate builds on draft [PR #74](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/74),
commit `c9daa2af289929efc15c3719677b9b0ae6b2ccfd`, tree
`7735c3488c40ad34fcd972c3d1101401b8da9dd2`. It adds opt-in Python capture through
the actual decode/reference trace, fixed observations and an explicit guarded
conditional fitting bridge. It does not add automatic refinement, an HTTP
source session, persistent photos, saved-project fields or a candidate acceptance
flow. Read the [API and lifecycle guide](../source-context.md).

## Source and observation binding

The captured bytes are exactly the float32 linear channel mix passed into
`sheet.rectify_gray`, before precision resampling, float32 storage and the added
Gaussian smoothing. Original encoded bytes, upright decoded RGB, working RGB and
the scalar field have separate identities. Metadata retains executed reduction,
including a reduction whose rounded dimensions happen to remain unchanged.

The display inverse is derived from the actual crop/rotation/scale, rather than
the scalar `mm_per_px` alone. Geometry is mapped back to sheet millimetres without
an extra half-pixel shift. Source indices are integer `[x,y]`; their geometric
centres are `[x+.5,y+.5]`. The actual homography, normalized radial map, chosen
channel weights, sheet orientation and rounded rectified dimensions remain bound
to the request and canonical profile.

The bridge checks its per-request observation label and independently verifies
the ordered source indices and values against the immutable field. A public
dataclass replacement cannot silently substitute another intensity vector. The
operator remains a declared fixed matrix, checked by the existing noise
factorization; a matching source label alone does not certify a replaced matrix.
Passing the profile-equality check does not select the application's latest
request. That ownership stays with the caller's result/context pair.

## Focused regression checks

All **45 focused tests pass** against unchanged source hashes. They cover:

- The exact real prewarp input, including non-luminance channel selection;
  distinct original-container/working identities; EXIF orientation and alpha;
  actual reduction and the unchanged-rounded-size case.
- Independent inverse geometry and explicitly enumerated signed Keys/filter/
  warp taps, including border handling and both smoothing modes.
- Immutable bytes-backed arrays and detached metadata; source order and bounds;
  stale-profile rejection; equal-profile but different-request rejection;
  altered observation indices/values and unsupported model preflight.
- Late trace failure, ordinary trace and explicit fallback lifecycle; unchanged
  HTTP response content and no source-context retention or source-file writes.
- Exact fitter dispatch using captured geometry, source values and the declared
  noise operator. This dispatch check alone is not a geometry-recovery test.

Test source SHA-256:
`df4b81ed369969ef9cedefc6216f0298be223c93e993ecacdb0a2978cf9f8f73`.

## Whole digital pipeline replay

The committed [plan](../../studies/source-context-v1.json),
[runner](../../studies/verification/source-context-v1.py) and
[complete result](../../studies/results/source-context-v1.json) retain all six
cases and before/after source hashes. The canonical run passes with unchanged
sources in 18.18 seconds. The expected digital values are computed by the full
image pipeline, separately from the composed sampling matrix. This is a digital
integration comparison, not an independent physical optics oracle.

| Case | Exact prewarp match | Maximum float64 operator versus rounded pipeline difference, level units | Point-Gaussian model guard |
| --- | --- | --- | --- |
| Pinhole | Yes | `5.1221e-6` | Conditional geometry available |
| Radial | Yes | `9.8500e-6` | Refuses nonzero lens term |
| Thick | Yes | `7.6767e-6` | Refuses lens and thickness/wall correction |
| Reduced | Yes | `8.1377e-6` | Refuses prior reduction and re-encoding |
| Colour | Yes | `2.8370e-6` | Conditional geometry available |
| Finite circular segment | Yes | `8.1509e-6` | Conditional geometry available |

The preset maximum replay discrepancy is `1e-4` level units. The small observed
differences remain present: the matrix uses float64 arithmetic, while the actual
rectified image and smoothing use float32. Agreement does not turn that rounding
discrepancy into noise or make image-derived pose/channel weights independent of
the observations. These are four fixed display queries per case, not an
exhaustive full-image equality check.

## Explicit end-to-end finite-shape fit

The final case independently polygon-rasterizes a circular segment, including
pixel-area coverage, applies a finite digital Gaussian blur and quantizes through
sRGB to a PNG. The real tracer detects its reference and supplies the working
field and estimated homography. The explicit context bridge fits radius/chord
using 36 fixed source pixels, a supplied `1.5² I` working-pixel covariance and
unit working-field noise. Ten separately selected source pixels are held out.
The render and point-detector forward model differ in aperture, digital blur,
quantization and estimated pose; this is an engineering tolerance check.

Preset bounds are `0.1 mm` radius error, `0.005` chord-fraction error and two
held-out level units. The known radius is `20.13 mm` and fraction is `0.267`.
The fit returns radius `20.12932994 mm`, fraction `0.2669328954`, radius error
`0.000670061 mm`, fraction error `0.000067105` and maximum held-out discrepancy
`0.54781` level units. It uses 28 geometry evaluations and 2,093,496 forward
evaluations. The returned profile remains unchanged.

Local geometry rank is two, no represented basin remains unrefined and no work
or numerical limit is flagged in this case. `global_search_certified=False`,
`pose_fitted=False` and `psf_fitted=False` remain explicit. This one generated
part does not establish general recovery, calibrated uncertainty, physical
dimensions or a printable fit.

## Failure retention and development history

An injected first-row failure keeps all six planned rows. All five later cases
execute the actual renderer/trace/operator or fit and match canonical numerical
rows apart from runtime. Six failure-retention/source checks pass. CLI checks
cover help, required output, existing-path refusal and missing-parent refusal;
destinations are checked before image analysis and final output uses exclusive
creation. No source image or pixel array is saved in reports.

The first development replay remains locally retained as
`.local/verification/source-context-initial-v1.json`: four ordinary replays
passed, the colour fixture failed sheet detection, and the finite fit failed its
preset target. The latter exposed a generator coordinate mismatch: the coverage
helper centres scene index `i` at `x0+i/ppm`, whereas working-photo models use
geometric centre `i+.5`. Correcting that independently rendered input and using
an existing qualified colour fixture fixed the study; no production fitting
tolerance was relaxed. The corrected candidate and final runs are separate
records. The initial focused test run also retained two test-setup failures
(a full-frame table cannot be an ordinary silhouette, and HTTP JSON uses lists).
Neither was a product numerical failure or a reason to remove an assertion.

## Local regression and delivery scope

The full local suite passes **1,759 Python tests** in **335.20 seconds**, with
zero failures, errors or skips. All **333 frozen product files** remain unchanged
through the terminal run. Of the 331 pre-existing product files, only
`backend/tracing.py` and `backend/reference.py` change; the source-context module
and focused test file are new. The frontend build and Python lint/format checks
pass. The guide example executes, all **44 CLI help paths** pass and both API
maps match the **11 actual OpenAPI operations**. The full Markdown audit checks
**101 documents**, **1,793 local links**, **120 fragment links**, **167 tables**
and one HTML reference without errors; document bytes stay unchanged during it.

Local freeze SHA-256:
`92fc4451545678445a7e8859ccc315e765bd078f3207ed5be41d7755add625b7`.
JUnit SHA-256:
`56a29b83c2bb110d3c34294d9b2c942232895dd8e651c8c57de79303d74b7b01`.

Existing browser and native-export evidence stays
bound to its original revisions. This component adds no new frontend control,
automatic profile replacement, native launch, merge, installation or deployment.

The canonical run binds these source/artifact SHA-256 values:

| Artifact | SHA-256 |
| --- | --- |
| `backend/source_context.py` | `a377dd0b5710d513de0594292eee50c55b0c98667babd30b4e36658a3e1cabba` |
| `backend/tracing.py` | `7f78c7ce7f709ff1169fa3842eb50fbd0bfa72551cde9054b90843c8b352c222` |
| `backend/reference.py` | `08f83e7a568aecf2b718c51269ac31afc1a95634e25a42dabb84682f68245648` |
| `studies/source-context-v1.json` | `0c2b46e97239f8373a60f7b324b067991973fb33aa51d1abe23ec026e5351f35` |
| `studies/verification/source-context-v1.py` | `4db6410c7c1981f3c0f283398747f101c3c80721373db31a51e503824ced0227` |
| `studies/results/source-context-v1.json` | `e21c722ee7ec03dd8696deafae6ced37bf92b4c0e23e315b5e9a6820814f12c9` |

## Remaining science and engineering

The captured field is decoded/processed working RGB mixed under assumed sRGB,
not sensor RAW. Scalar rectified edge blur does not identify raw SPD covariance.
Known coordinate-warp composition also does not supply a forward optical model
for nonzero radial distortion. Prior reduction, detector apertures, tone mapping,
spatial response/PSF, illumination, shadows, walls and uncertain pose require
their own models and calibration/error evidence. Fixed independent working-pixel
noise is supplied, not inferred from a camera.

Next steps are calibrated or bounded source optics/response/noise, broader
supported forward geometry, candidate generation tied to the current request,
and a review flow that retains the current boundary when evidence is inadequate.
Reserved measured captures and physical fit/print acceptance remain separate
requirements.
