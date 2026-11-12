# Keep a trace bound to its source observations

The opt-in [source-context module](../backend/source_context.py) runs the real
reference-sheet trace and retains its exact prewarp working intensity field in
memory. It connects the tracing path to the developer [fixed-observation
operators](profile-observations.md) without reading values from the display
image or reconstructing them from a saved outline.

This is a Python developer API. It adds no HTTP endpoint, workbench control,
`Profile` field, saved-project format, global source cache or disk persistence.
Capturing a context does not automatically run the
[finite-shape fitter](finite-shape-source.md), replace geometry or infer a
camera's PSF, noise, response or pose uncertainty. A separate explicit fitting
method is described below.

## Capture only after a successful sheet trace

```python
from backend.source_context import trace_with_source

result, context = trace_with_source(
    encoded_image_bytes,
    reference="a4",
    thickness_mm=0,
    snap=False,
    fallback=False,
)
```

`data` is the encoded image's bytes. Trace options are the normal
`trace_image` options: `threshold`, `inverted`, `detail`, `reference`,
`sheet_mm`, `thickness_mm`, `snap` and `fallback`. Their existing defaults,
image limits, validation, warnings and tracing failures still apply. In
particular, omitting `reference` selects ordinary tracing and returns no source
context. `_source_capture` is reserved for the wrapper.

The return value is `(result, context_or_None)`. A context is published only
after a complete successful reference-sheet trace. Ordinary silhouette tracing
and an explicitly permitted ordinary-trace fallback return `None`. A failed
trace raises its normal error and returns no context. Check this outcome before
using source-observation methods; selecting a sheet is not proof it was used.
The caller owns the returned result/context pair; there is no global “latest
trace” or source-session registry.

## What the context retains

`context.working_field` is a read-only, bytes-backed two-dimensional view of the
exact little-endian float32 field supplied to precision rectification. Its
values are the trace's chosen nonnegative mixture of sRGB-decoded working RGB
channels, on a `0..255` linear-light scale. It precedes Keys rectification and
the added `0.7`-rectified-grid-pixel Gaussian smoothing.

“Raw” in the observation and fitting APIs means this available **prewarp working
field**, not sensor RAW or recovered radiance. Decoding, orientation, alpha
handling, camera processing and source quantization have already happened.
Large reference images are reduced and re-encoded before this field is made;
the context records that processing rather than undoing it. sRGB decoding does
not establish the camera's actual response.

`context.metadata()` returns a detached JSON-compatible record, including:

- The `trace-source-context-v1` schema, unique per-request `request_id`, encoded
  input SHA-256 and byte count, decoder name, and upright/working RGB shapes and
  byte hashes.
- The working-field SHA-256, shape, `<f4` dtype and stated level units; the
  chosen channel weights; and the reduction flag, method and actual XY scales.
- The plane-mm-to-undistorted-working-photo homography, normalized `lens_k1`,
  radial centre/scale, sheet-plane size, rectified dimensions and pixels per
  millimetre, and the rectification/smoothing contracts.
- The display-to-plane inverse, display dimensions, trace options, reference
  notes, thickness record and canonical profile SHA-256.
- NumPy, OpenCV and Pillow versions, plus explicit false flags for calibrated
  PSF, noise, pose and response, sensor RAW and modelled pixel aperture.

The record contains no image samples or encoded original. The context retains
the working field, not copies of the original encoded file or RGB arrays.
Metadata can still reveal dimensions, trace settings and notes; a metadata
record is not a replacement for the private source field.

The context owns the complete working field even when only a few observations
are requested. Normal image-size limits still apply. Keep contexts only as long
as the local investigation needs them; there is no server session to retrieve
after the caller releases the object.

## Bind observations to the current profile and request

All geometry/observation methods require `profile=`. `context.assert_profile`
validates and canonically serializes that profile, then compares it with the
captured profile. A difference raises `ValueError` and asks for a fresh trace;
old observations must not explain newly edited geometry.
An equal canonical profile passes this check even if it came from a later
request; this is a geometric-equality check, not a global revision check.

`context.sha256` hashes the canonical metadata record, which binds the source
hashes, frame, processing and request identity. Each `SourceObservation` carries
that digest as `context_sha256`. Two equivalent traces can have equal field
hashes but different context digests because their request IDs differ.

The profile check compares profile data; it does not identify a photograph by
itself or validate separately supplied width, design, PSF, noise or fitting
settings. Retain the context digest and bind those additional inputs to any
candidate/report revision. Editing the detached metadata dictionary does not
change the context or its checks.

## Choose the observation frame explicitly

| Method | Coordinates and result |
| --- | --- |
| `display_to_plane(points, *, profile)` | Maps 1–2,048 finite continuous display-coordinate pairs to sheet millimetres. It inverts geometry only and adds no pixel-centre offset. |
| `source_pixels(pixels_xy, *, profile)` | Reads 1–512 unique in-frame integer working-image `[x, y]` indices in the supplied order, with an identity sampling matrix. |
| `observe_display(points, *, profile, smoothing=True)` | Composes final Keys sampling, optional known smoothing and actual rectification into one fixed source-pixel operator. |
| `point_gaussian_geometry(*, profile)` | Returns the working `sensor_shape` and homography only when the guarded point-Gaussian model covers the recorded processing/geometry. |
| `fit_edge_spread(observation, *, profile, input_std, **fit_options)` | Explicitly fits a declared straight working-photo edge's offset/Gaussian width; anchor and normal use the working-photo frame. See [conditional calibration](psf-calibration.md). |
| `fit_circular_segment(observation, *, profile, input_std, psf_covariance, **fit_options)` | Explicitly runs the conditional fitter with this request's source observation and guarded geometry. It returns a candidate result without changing the profile. |

For direct source pixels, geometric forward models evaluate at
`pixels_xy + 0.5`. These are working-image indices, not original camera-file,
screen or display-crop indices. Direct reads do not interpolate, clip or smooth;
duplicate, noninteger and out-of-frame indices are refused.

Display points are already continuous geometric coordinates in the returned
profile/display frame. Do not add `0.5` to them. The context maps them back to
sheet mm, then to rectified index coordinates using
`plane_mm * rectified_ppm - 0.5` before composing the sampling operator. This
inverts the recorded crop, rotation and display scaling; it does not use the
display bitmap as an intensity measurement.

`observe_display` follows the [known warp chain](warp-observations.md):

```text
working source g -> Keys rectification R -> known smoothing G -> Keys samples S
A = S G R
```

With `smoothing=True`, `G` is the seven-tap-per-axis Gaussian for sigma `0.7`
rectified-grid pixels, with `reflect101` borders. With `False`, the operator is `S R`; earlier optical
blur, decoding and reduction are still present. Rectification uses the recorded
homography and radial term, with replicated source borders. Final Keys sampling
also replicates its grid border. Finite display points are not automatically
checked for membership in the visible part or a physically useful observation
region; callers must choose and preserve that region deliberately.

This explicitly constructs final Keys observations, as used by the blur/wall
profile branch. The primary outline crossing uses a different bilinear sampler;
`observe_display` does not silently reproduce that crossing operator. See the
[warp-chain scope](warp-observations.md) before treating a selected sample set as
the observations of a particular estimator.

The existing operator caps apply: at most 512 output samples, 2,048 distinct
source pixels and 500,000 matrix cells, plus filter/warp work limits. A request
can be valid for `display_to_plane` yet exceed sampling or factorization limits.
These are resource refusals, not evidence about the part.

## Read and whiten the same fixed samples

A `SourceObservation` contains immutable `pixels_xy`, `raw_values` and
`matrix`. Source indices are coalesced by the composed operator, and its column
order is the order of `pixels_xy` and `raw_values`. `observation.samples` is
`matrix @ raw_values` in float64 arithmetic.

`observation.noise(input_std)` creates a `PixelNoise` factor for supplied
independent working-pixel standard deviations. Supply one positive finite
scalar or one value for every source column, in the working field's level units.
It does not estimate noise from the image. Interpolation/filter taps that share
a source pixel share its noise; they must not become independent observations.
Factorization has its own allocation/work limits.

Use the same fixed pixel set, matrix, noise scaling and retained numerical row
space for observations and predictions. `noise.whiten_source(raw_values)` uses
that source projection directly. A retained-mode residual is conditional on
these choices, not a calibrated physical likelihood. Changing observation
support with candidate geometry changes the objective.

The composed matrix represents ideal **float64** `S G R`. Real tracing stores
the rectification and smoothing in **float32**. Capturing the exact input field
does not eliminate those later rounding discrepancies or make matrix samples
bit-identical to the rounded production measurement image. Small retained noise
modes can amplify the difference; keep that discrepancy separate from supplied
camera-noise assumptions.

## A synthetic, in-memory walkthrough

Run this from the repository root in its prepared Python environment. It uses a
generated sheet photograph and writes no image or report file. The declared
one-level noise scale illustrates the API; it is not estimated from the fixture
or justified for a real camera.

```python
from backend.source_context import trace_with_source
from tests.synthetic import render

data, truth = render(
    size=(1200, 900), tilt=(0.0, 0.0, 0.0), k1=0.0, thickness=0.0,
    shadow=0.0, gradient=0.0, noise=0.0, quality=100,
)
result, context = trace_with_source(
    data, reference="a4", thickness_mm=0.0, snap=False, fallback=False,
)
if context is None:
    raise RuntimeError("This request did not produce a reference-sheet context")
profile = result["profile"]
context.assert_profile(profile)

direct = context.source_pixels([[0, 0], [1, 0]], profile=profile)
display_points = profile["outer"][:3]
observation = context.observe_display(display_points, profile=profile)
noise = observation.noise(input_std=1.0)  # Supplied illustrative hypothesis.
target = noise.whiten_source(observation.raw_values)
print(context.sha256, direct.raw_values, target, noise.rank)

try:
    geometry = context.point_gaussian_geometry(profile=profile)
except ValueError as error:
    print("Point-Gaussian model unavailable:", error)
else:
    print("Conditional working frame:", geometry["sensor_shape"])
```

The first direct reads are merely an ordered-index example. The display reads
show how to form observations near the returned outline; they do not establish
that those outline points identify the physical edge. `truth` belongs to the
synthetic generator and is not injected into tracing. Even a fixture rendered
with zero distortion does not authorize overwriting an estimated lens term to
make the point-Gaussian guard pass.

## Guard the forward model before fitting

`point_gaussian_geometry` refuses a context with any of:

- Nonzero recorded `lens_k1`: a lens-free homography alone does not describe the
  source geometry.
- Prior area reduction and re-encoding: the field no longer has the primitive's
  declared point-detector Gaussian observation model.
- Nonzero entered thickness: top-face/wall/parallax corrections are outside the
  flat finite-material model.

Source reads and known digital sampling remain available for these contexts;
the restriction is on this particular forward model. Passing the guard supplies
only the frame and homography. A caller must still supply and justify the raw
PSF covariance, noise, constant-level/response and point-aperture assumptions,
analytic topology and candidate geometry. The guard does not detect undeclared
wall appearance, establish physical calibration or prove model adequacy.

### Explicit conditional fitting bridge

`context.fit_circular_segment` first applies that profile/model guard, then
requires a `SourceObservation` carrying this context's `context_sha256`. An
observation from another request is refused even when both requests produced
equal profile geometry. It also validates the ordered unique in-frame integer
indices and checks their supplied values against the immutable working field;
values are re-read from that field for fitting. The caller still owns and selects
the current result/context pair.

The matrix remains a declared fixed sampling operator and is validated by the
noise factorization. A context label does not certify that a separately constructed
or replaced matrix is the operator for a selected display-sampling path. Use the
context-issued observation to preserve that path.

The method supplies the captured working-frame dimensions, homography, source
indices and values to the actual finite-shape fitter. It factors the
observation's matrix with the caller's `input_std`, and passes through the
supplied `psf_covariance` and `fit_options`. Those options must include
`radius_bounds` and `chord_fraction_bounds`; fixed centre/normal, brightness
bounds and search/work limits follow the
[finite-shape API](finite-shape-source.md#conditional-radius-and-chord-fitting).
Centre, radius and chord offset use the captured sheet plane's millimetres;
the PSF covariance remains in working-image pixels squared.

This is an explicit conditional candidate fit, not an automatic refinement or
accepted replacement. Keep its work limits, unresolved/rank diagnostics,
competing candidates and residual decomposition with the supplied hypotheses.
It does not mutate the captured or returned profile, apply `correct_blur`,
qualify the camera or establish that the one-segment model describes the part.

The explicit [edge-spread bridge](psf-calibration.md#use-the-source-context-bridge-explicitly)
reuses the same model, request and source-value guards. Its normal, anchor, offset
and width use the working-photo frame, while circular-segment geometry uses sheet
mm. Fitting a target does not change any context calibration flag.

This context supplies a missing in-memory data binding for future source-fit
experiments. It does not implement automatic refinement, a saved capture
session, candidate acceptance or a review flow. General finite-shape recovery
and real-camera qualification remain separate evidence questions.
