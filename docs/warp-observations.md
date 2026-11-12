# Known warp composition and raw optical models

The observation module now follows a fixed raw-photo-to-profile path, including
Keys perspective/lens rectification, declared finite smoothing and final Keys
sampling. This makes the digital model more realistic. It also exposes an
independent question: whether the supplied source field and optical blur are
appropriate before those operations. The [complete controls](validation/warp-observations.md)
keep digital agreement, float32 rounding and optical-model assumptions distinct.
These developer tools do not change production tracing or add an accuracy label.

## Compose the actual order

Let `R` map source pixels onto the rectified grid, `G` be the declared smoothing
filter, and `S` read the final profiles. With fixed maps and ideal float64
arithmetic, the known operator is `A = S G R` and the predicted profile is `A g`.
The actual pipeline also stores `R g` as float32 and filters in float32. Those
rounding operations are not included in the ideal linear matrix.

```mermaid
flowchart LR
    A[Already linear source pixels] --> B[Keys rectification R]
    B --> C[Float32 storage]
    C --> D[Finite Gaussian smoothing G in float32]
    D --> E[Final Keys profile S]
```

The new `after_warp(source_shape,source_x,source_y)` accepts one source index
coordinate for each currently required intermediate pixel. It composes only the
needed local stencil; no full-image warp matrix is allocated. The convenience
`after_rectification(source_shape,H,k1,plane_size,ppm)` follows the existing
measurement path's geometry:

1. Rectified pixel `(i,j)` represents plane `((i+.5)/ppm,(j+.5)/ppm)`.
2. Apply homogeneous division using `H` to obtain undistorted photo coordinates.
3. Apply the normalized radial factor about the original photo centre, using
   its half-diagonal as the normalization radius.
4. Subtract `.5` to obtain source index coordinates for Keys sampling.

`source_shape` is `(height,width)`, while `plane_size` is `(width_mm,height_mm)`.
The declared current grid must match the rounded plane dimensions times `ppm`.
The original source and the current rectified grid can have different dimensions.

Final Keys sampling replicates rectified indices. Smoothing then reflects or
replicates indices on that rectified grid, according to its declared border.
Only then does `R` map each needed rectified pixel into the photo and replicate
its source Keys taps. Moving smoothing or reflection across the warp gives a
different operator. General reverse-coordinate mapping is described in the
[OpenCV transformation guide](https://docs.opencv.org/4.13.0/da/d54/group__imgproc__transform.html);
this module uses the project's own unquantized Keys measurement sampler.

Repeated source indices are coalesced before covariance accounting. A zero
functional remains zero after warping; it has no retained noise information.
Non-finite/horizon map coordinates are refused before integer conversion or
kernel evaluation. This is a low-level geometry safeguard, not evidence of a
reproduced valid-sheet photo failure.
Checks cover the used local stencils, not global validity of an entire plane map.

## Keep supplied noise separate from estimated geometry

`PixelNoise.factor(A,input_std)` can now propagate declared independent source
noise through the complete fixed digital operator. The [covariance guide](profile-observations.md)
explains whitening, support checks and rank limits. This does not make the
selected homography, lens term, edge normals or optical spread known quantities.

Statistical calculations assume the operator is fixed independently of the
noise. Freezing geometry or channel weights estimated from the same noisy image
does not establish a calibrated conditional noise distribution. Parameter
uncertainty, selection effects and shared pixels between neighboring profiles
need joint estimation or independently justified approximations.

## A Gaussian lives in a coordinate system

For affine photo mapping `q = B p + b`, plane material `n^T p >= c` with
unit plane normal `n`, and translation-invariant raw Gaussian optical covariance
`Sigma_raw`, define

```text
m = B^-T n
sigma_plane_normal^2 = n^T B^-1 Sigma_raw B^-T n
f_raw(q) = C + Delta * Phi((m^T(q-b)-c) / sqrt(m^T Sigma_raw m))
```

This direction-specific spread is exact for an ideal affine straight edge.
A geometric-mean scale generally is not. Gaussian covariance transforms with
the affine map; [Lindeberg's scale-space treatment](https://people.kth.se/~tony/papers/Lin10-TR-KTH-CSC-CV-2010-3.pdf)
describes that transformation property. Interpolation remains a separate digital
operation even when the continuous source model is exact.

A lens-free homography maps a straight boundary line by
`line_raw = H^-T line_plane`. In a consistent projective chart, the raw Gaussian
half-plane probability follows that raw line. Its pullback into the plane is
rational, so one frozen local Jacobian is an approximation away from its anchor.
The finite controls retain up to 0.147875 linear-light levels of discrepancy
from that approximation and up to 8.47010 levels from a geometric-mean scalar.

Radial distortion generally curves a line in the raw image. Applying a Gaussian
CDF to geometric signed distance is then a tangent approximation to a two-
dimensional convolution. A separate supplied-PSF quadrature control gives
0.4985125 response at a true curved boundary and about 0.01119 raw pixels of
half-level displacement. Agreement of two quadrature orders is convergence
evidence, not a certified integration bound or a real-camera error estimate.

## What the digital comparison establishes

The fixed experiment uses six already-linear synthetic arrays, three maps,
three radial coefficients, two output scales and three profile locations.
Its 108 processed chains produce 324 readouts. Every planned readout is kept.
This is six reused source arrays, not 324 independent scenes or real captures.

The declared matrix agrees with float64 staged operations within `1.99e-13`
linear-light levels. The actual float32 chain differs by up to `2.96e-5`.
Measured rectification-cast and blur-rounding errors explain that difference
within `1.79e-13`. Their triangle accounting includes a recorded arithmetic
allowance; it does not supply an unseen-input, vendor-certified or physical bound.
An independent raw-edge study separately checks the complete operator and the
source-PSF distinctions above.

The measured float32 discrepancies also matter for inference: small retained
covariance modes can amplify them even when a residual lies in the retained
range. See [conditioning and whitening](profile-observations.md#whiten-the-retained-modes-and-check-what-was-omitted).
The separate [source-space fitter](raw-source-fit.md) now supplies a bounded
finite offset search under a declared lens-free Gaussian source. It uses available
prewarp observations rather than inverting weak processed-profile modes; it does
not calibrate a likelihood for a real photograph.

## Repeat and interpret

```bash
make warp-observation-study OUTPUT=.local/warp-observations-new.json
.venv/bin/python studies/verification/raw-gaussian-warp-edge-v1.py --output .local/raw-edge-new.json
```

Use fresh JSON paths and the workbench environment. The main comparison requires
a Git checkout for its context field; exact source hashes bind the implementation.
The independent raw-edge runner pins the production/observation sources and
refuses changes until that pin is explicitly reviewed. Its Git field is optional.
Both retain complete controls and runtime versions and require no CAD server.

Warp composition checks at most 32,768 expanded taps and 50 million composition
work units before expansion. The existing 2,048-source-pixel and 500,000-cell
dense limits still apply; unsupported requests fail explicitly. These caps do
not establish whole-photo latency. Real-camera noise/PSF calibration, detector
aperture, nonlinear tone response, spatially varying blur and full reconstruction
remain separate work before this research can support production uncertainty.
