# Sampling, correlated noise and realistic edge evidence

Reading a blurred image at smaller intervals does not create independent camera
measurements. A developer module now represents the actual fixed signed sampling
operator, can compose a known finite smoothing filter, and accounts for shared
input-pixel noise. It supports the next wall-model investigation; it does not
change tracing, add a confidence badge or calibrate a real camera.
The [warp-chain extension](warp-observations.md) now also composes the known
earlier Keys rectification and retains raw optical-model countercontrols.
The [raw-source fitter](raw-source-fit.md) now uses the available source samples
for both target and model, preserving the declared row space and reporting raw
residual components omitted by it. Supplied geometry/optics/noise remain assumptions.
The [source-bound controls](validation/profile-observations.md) retain both
false-precision examples and remaining model mismatch.

Use the [source context](source-context.md) to obtain actual request-bound
prewarp values and an observation operator. The [edge-spread fitter](psf-calibration.md)
can then search a declared straight edge's offset and Gaussian width using
`PixelNoise`'s fixed retained source modes. This does not estimate the noise
factor: its input deviations remain supplied, and pooling directional variance
summaries does not infer their correlations or standard deviations.

## Separate observations from their source

Let `g` be the vector of unique input pixels and `S` the matrix of declared
sampling weights. Then `y = S g`. The Keys builder clips source indices before
coalescing repeated taps, including border replication. Repeated taps referring
to one pixel share its noise; they must not become independent noise sources.
The kernel intentionally reuses the actual Keys implementation. Tests also call
the actual sampler and OpenCV filtering with independently specified inputs.

For a declared finite filter `G` before final sampling, the operator is `S G`.
Filtering uses an explicitly chosen `reflect101` or `replicate` border. This
matches linear float64 filtering; float32 rounding remains a separate discrepancy.
[OpenCV's filter contract](https://docs.opencv.org/4.x/d4/d86/group__imgproc__filter.html)
documents output-depth and border behavior. The seven-tap Gaussian support used
in the study is verified against the recorded runtime's impulse response.

With independent input errors of supplied standard deviations `s`, define
`D = diag(s)`, `L = S D`, and `Cov(y) = L L^T`. This is conditional on the supplied
noise model. Resampled values are correlated because they reuse the same input
pixels; this general effect is also described in the
[STScI correlated-noise guide](https://hst-docs.stsci.edu/drizzpac/chapter-3-description-of-the-drizzle-algorithm/3-3-weight-maps-and-correlated-noise).
The workbench's processed image has earlier resampling and smoothing, so its
pixels cannot simply be assumed independent in a physical interpretation.
Neighboring profiles can also share pixels. Separate per-profile factors do not
justify treating pooled profiles as independent; that needs a joint operator
or an independently justified covariance approximation.

## Whiten the retained modes, and check what was omitted

Use the compact SVD `L = U diag(d) V^T` and `W = diag(1/d) U^T` for retained
nonzero modes. This gives `W L = V^T` and unit covariance. Uncorrelated components
need not be independent; a Gaussian likelihood additionally requires Gaussian
input errors. The implementation factors `L`, avoiding formation of `L L^T`
which squares its conditioning. See [NumPy's SVD contract](https://numpy.org/doc/stable/reference/generated/numpy.linalg.svd.html).

The least-squares score is `||W(y - prediction)||^2`. A singular-covariance
pseudoinverse alone is insufficient: also inspect the component outside the
retained range, `(I - U U^T)(y - prediction)`. For example, duplicating one pixel
gives identical rows; a residual `[1,-1]` has zero pseudoinverse score but cannot
come from that shared pixel. The module reports this component separately and
refuses unsupported observations in its source-design fit.

When input pixels are available, the more stable identity is
`W S g = V^T D^-1 g`. `whiten_source` uses it, avoiding division of already sampled
data by tiny singular values. All results remain conditional on the retained
numerical row space. The cutoff is `eps * max(rows, columns) * largest_singular_value`;
rank, cutoff and largest omitted singular value remain inspectable. Truncation
can change a row space and break an otherwise exact repetition identity.

Passing the range check does not control amplification within retained modes.
For a deterministic discrepancy `delta`, the Euclidean norms obey
`||W delta|| <= ||delta|| / d_min`, where `d_min` is the smallest retained
singular value. Tiny retained values can therefore amplify float32 rounding or an imperfect optical model. The stable
source identity improves evaluation of a declared source field; it does not
remove discrepancies in the actual observed chain. Inspect conditioning and
model adequacy before interpreting a whitened residual as a likelihood. A
numerical rank threshold is not a calibrated physical discrepancy threshold.

Duplicate measurements add no information when covariance and retained raw row
space are unchanged. Sampling a previously unseen input combination can add
information, so arbitrary density changes are not universally invariant.

## What the controls demonstrate

The fixed noise study uses one ideal straight step, known tones and optical
spread, and independent Gaussian input noise of one linear-light level. Across
25, 49, 97 and 193 profile samples, all operators span the same 16 input pixels.

| Samples | Diagonal-noise predicted local spread, px | Covariance-aware local spread, px |
| --- | --- | --- |
| 25 | 0.01709 | 0.02683 |
| 49 | 0.01200 | 0.02683 |
| 97 | 0.00848 | 0.02683 |
| 193 | 0.00600 | 0.02683 |

The diagonal estimator's actual local spread stays about 0.02684 pixels. Common
8,192 Gaussian input draws support the conditional variance calculation; these
are linearized known-tone estimators, not a nonlinear estimator's coverage study.
The repeat controls preserve this effect. Separate controls retain genuine
row-space gains and a numerical truncation counterexample.

A second example has identical mean fields at wall labels separated by 3.09524
pixels, although each branch has finite local sensitivity. Small local spread
therefore does not prove global identification of a silhouette.

The postblur controls expose another distinct limitation. The current pipeline
applies discrete Gaussian smoothing before final Keys sampling. Replacing that
combination by one continuous Gaussian of even an oracle moment-matched width
leaves discrepancies and misses six constructed one-step aliases. Explicit known
filter composition retains all six aliases in those development controls, while
float32 prediction discrepancies remain visible. This does not qualify earlier
rectification, nonlinear tone response, detector aperture, curved boundaries or
the actual camera's noise and optics.

## Developer API and limits

`backend/profile_observations.py` provides `keys_profile(image_shape,x,y)`,
`KeysProfile.after_filter(kernel,border=...)` and `PixelNoise.factor(matrix,input_std)`.
Coordinates are image index coordinates; geometric pixel centres are
`pixels_xy + 0.5`. Sampling is bound to the declared image shape.
`PixelNoise.fit_source(source_design, observed)` fits an unconstrained linear
input-pixel design to a **processed profile** `observed`, using `whiten(observed)`
and `whiten_source(source_design)`. It reports numerical design/noise rank and
residual degrees of freedom, with no physical-fit, bounded-tone or global-uniqueness
claim. This differs from the [raw-source fitter](raw-source-fit.md#developer-api),
which projects both available prewarp observations and the model with
`whiten_source`, avoiding the processed-profile division by weak retained modes.

Limits are checked before dense allocation or factorization: 512 profile samples,
2,048 source pixels, 500,000 matrix cells, 100 million factor work units
`rows * columns * min(rows,columns)`, 200,000 expanded filter terms and 50 million
composition work units. Filters are odd and at most 15 by 15. Unsupported requests
raise a descriptive error; work limits do not certify whole-photo latency.

```bash
make profile-noise-study OUTPUT=.local/profile-noise-new.json
make postblur-operator-study OUTPUT=.local/postblur-operator-new.json
.venv/bin/python studies/verification/profile-observations-oracle-v1.py --output .local/profile-oracle-new.json
```

All three commands require a fresh JSON path and retain complete controls, sources
and runtime versions. They use the workbench environment and require no server.
The finite-search prototype is pinned by source hash. The supplied optical/noise
parameters are experimental inputs, not values inferred from a user's photograph.
