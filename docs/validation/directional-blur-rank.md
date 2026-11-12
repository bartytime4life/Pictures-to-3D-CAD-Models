# Directional-blur covariance design rank

This repair is based exactly on `main` at
`f1679bb50ca39e1764897e00124eccdf41b21f59` (PR #77), tree
`81fbb8fd2392e0f8c24795707aa81647d68f47c4`. It changes the numerical
identifiability check inside `edges.edge_covariance`; it does not qualify a
camera or establish the adequacy of a Gaussian source model.

## Reproduced failure

The covariance design has rows `[nx², 2 nx ny, ny²]`. Opposite normals give
identical rows. Counting occupied angular bins therefore cannot establish three
independent covariance equations.

The independent regression specifies three separated straight-edge image patches
directly by the Gaussian half-plane `erfc` formula. The common supplied covariance
is `diag(4, 9)` pixel²; the normals are `(cos(π/6), sin(π/6))`, its exact
negative, and `(0, 1)`. Each patch supplies 20 actual sampled edge profiles.
No production blur renderer or width stub generates these inputs.

Floating angle reduction produces `29.999999999999996°` and `30.0°` for the
opposite copies, and `90.0°` for the third patch. The bin counts are
`[20, 20, 0, 20, 0, 0]`. All 60 profiles pass the clean-step measurement, but the
design has numerical rank two; its singular values are approximately
`7.5083, 4.3157, 2.60e-16`.

On the pinned baseline, the measured covariance is approximately
`[[1.72074, 1.98694], [1.98694, 9.01018]]` pixel². It is positive definite and
passes the directional-ratio switch, although its determinant is `11.5563`
instead of the supplied `36`. The missing direction is filled by the
least-squares minimum-norm solution. Positive definiteness does not identify the
missing parameter. Reversing the image contrast reproduces the same failure.

This is a measurement-function regression using actual sampled images. A complete
reference-sheet trace with this exact constructed input was not reproduced, and
the determinant difference is not a measured physical or whole-photo error.

## Repair and controls

Every weighted least-squares solve now checks the numerical rank returned by
`numpy.linalg.lstsq(..., rcond=None)` and returns `None` below rank three. This
also applies after robust trimming. The existing scalar-blur path handles that
unavailable covariance. Angular-bin counts, trimming, adequacy thresholds,
directional-ratio switching and curvature formulas are unchanged.

The six new controls retain both contrast polarities of the reproduced failure,
two rotated/sign-reversed two-direction controls, and two genuine three-direction
controls. The latter still recover the supplied covariance within `0.06` pixel²
per entry. That numerical regression tolerance is not a camera accuracy bound.

Before the repair, the new file reports **2 failed, 4 passed** in 0.24 seconds.
The repaired six cases plus the existing fidelity tests report **76 passed** in
41.21 seconds. The build-first full Python suite reports **633 passed** in
179.82 seconds, with runtime warnings treated as errors and no failures or skips.
All 269 frozen non-Markdown files and 22 built frontend files are unchanged
through that full run. The frontend build and changed-file Ruff checks pass.
No new browser run is claimed.

The candidate `backend/edges.py` SHA-256 is
`c02bcf6f15958ea5c82444de3ea3af37f20031e6df463846dc8082e37abae9ee`;
the new `tests/test_directional_blur_rank.py` SHA-256 is
`f3d3318be316a19599f20180218cdab9c0b74fbdb35471403cbbde1b1e6cfc7b`.
With the [development dependencies](../development.md) available, replay using:

```bash
npm run build
.venv/bin/python -m pytest -q -W error::RuntimeWarning tests/test_directional_blur_rank.py tests/test_fidelity_math.py
.venv/bin/python -m pytest -q -W error::RuntimeWarning
```

## Limits

Numerical full rank is necessary, not sufficient, for a well-conditioned or
physically correct covariance. No new condition-number acceptance threshold,
noise-independence claim, spatially varying PSF model, or physical confidence
statement is introduced. The fitted widths are measured in the rectified image;
they are not a separately calibrated sensor-space PSF. Historical PR #77 results
remain in the [validation overview](../validation.md) and
[reference-sheet guide](../reference-sheet.md).
