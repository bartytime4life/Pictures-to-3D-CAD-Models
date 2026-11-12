# Conditional PSF fitting: numerical evidence and counterexamples

This candidate builds on published [PR #75](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/75),
head `0c35777b021f16968e06f9848df330b53b04855d`, tree
`8b051c5f1417c6a6ac098ceee715bec2e8309451`. Its Python APIs fit a declared raw
straight-edge model and investigate common Gaussian covariance. The
[guide](../psf-calibration.md) describes units, search limits, readiness pooling,
source-context guards and physical limitations.

## What is implemented

`fit_edge_spread` jointly searches offset and log Gaussian width using fixed
source pixels and `PixelNoise` projection. It profiles two bounded intensity
levels, uses analytic mean derivatives and actual-cost backtracking, and retains
the complete grid, represented basins, numerical unknowns and local rank.
Unprojected derivative scale guards prevent brightness-confounding roundoff from
masquerading as two informative geometric directions.

`covariance_from_edge_fits` retains all declared edges and their statuses. Any
missing candidate, unresolved search, boundary/tie/flat finding, deficient or
unavailable local rank, or unfinished represented basin withholds pooling.
Numerical readiness is not a Gaussian-model acceptance decision.

The covariance solve uses the orthonormal Frobenius coordinates
`(Sigma_xx,sqrt(2)*Sigma_xy,Sigma_yy)`. Weighted/unweighted rank, condition,
nullspace, candidate eigenvalues and row residuals remain separate. A minimum-norm
rank-two matrix can be SPD without identifying a covariance. Indefinite results
are not repaired by clipping eigenvalues. Representable parameters can survive
unrepresentable standardized residual diagnostics, which become `None` rather
than false zero. The finite orientation planner maximizes rank then retained
information volume under supplied variance-summary weights.

The explicit source-context edge-fit bridge reuses immutable pixel-value,
profile/request and supported-model guards. Its anchor/normal/width use the
working-photo frame. It does not convert display geometry into known target
geometry or change any calibration flag.

## Focused and whole-workbench regression

All **1,844 Python tests pass** in **279.27 seconds**, with zero failures, errors
or skips. All **337 frozen product files** remain unchanged through the terminal
run. The **85 new tests** comprise 47 raw edge-fit and 38 covariance/context
tests; the existing source-context tests also pass after sharing validation.

Checks include exact off-grid recovery; bounded brightness active faces;
projection and omitted information; work/unknown retention; extreme numerical
units and strict JSON; local brightness confounding; rotationally invariant
conditioning; constructive rank-two aliases; full-rank indefinite results;
variance-unit invariance; finite planning and all-row pooling. An actual generated
sheet photo also exercises source-context dispatch without changing the profile
or calibration flags. It is a digital integration check, not exact optical
recovery or a measured-camera test.

Local product-freeze SHA-256:
`a9613346e7b085f19c32b4710e3e03a128499c494c86a1553c220a1eaba7583d`.
JUnit SHA-256:
`b5d9111f495a06bcaeb3df7ce010baef15ae4ccefd934e643ad7974eca2520e0`.

The frontend build, Python lint/format and the guide's executable arithmetic
example pass. All 45 CLI help paths pass, and both API maps match the 11 actual
OpenAPI operations. The complete Markdown navigation audit passes; it retains
source hashes rather than relabeling historical software results. Browser, native-export, installed-machine and physical acceptance
receipts retain their original source bindings; these checks do not relabel them.

## Independent fixed study

The [13-case plan](../../studies/psf-calibration-v1.json) was fixed before fitting.
The [runner](../../studies/verification/psf-calibration-v1.py) independently renders
Gaussian/alternative means with `erfc` and uses rational controls for weighted
linear reconstruction. Its finite-D holdout uses an independent area-integral
oracle, not the production boundary formula. The
[complete canonical v2 result](../../studies/results/psf-calibration-v2.json)
retains **13/13 cases, 225 checks, zero failed cases and zero execution errors**.
Before/after source hashes match. Runtime is 2.865 seconds.

| Control | Recorded finding |
| --- | --- |
| Balanced correlated SPD and rotated directions | All edge fits are pooling-ready; supplied Gaussian covariance recovered within preset targets. |
| Declared correlated observations and noise-unit changes | Fixed retained source modes and scale changes preserve the conditional fit. Noise is supplied. |
| Rectangle | Distinct SPD cross terms produce identical axis spreads; numerical rank two, identified covariance withheld. |
| Rational nearly parallel directions | A `1e-4` variance perturbation leaves every observed variance positive but shifts the inferred perpendicular variance by about `-0.99995`; the rank-three candidate becomes indefinite and is retained without clipping. |
| Weighted rational oracle and unit changes | Independent exact weighted coefficients agree with the numerical reconstruction. |
| Direction planner | Balanced `0/60/120` degrees gives ideal condition `sqrt(2)`; one additional edge for fixed `0/90` directions is `45` degrees. These are variance-model design statements. |
| Positive Gaussian mixture | Pooling-ready fits and SPD covariance still predict the finite-D holdout incorrectly; Gaussian adequacy is not established. |
| Exact common-response alias | Nearly perfect edge fits recover the response-scaled covariance, not the supplied physical source covariance. |
| Pixel-aperture and gamma mismatch | Pooling-ready fits can retain biased Gaussian-equivalent covariance; their alternate mean models remain explicit. |
| Constant source and exhausted no-refinement search | Pooling is withheld; no planned row disappears. |

Matched targets were fixed at `1e-5` pixel offset/width error, `1e-4` pixel-squared
covariance Frobenius error, `1e-3` intensity levels on a fourth-direction holdout
and `2e-3` levels on the finite-D holdout. Actual maxima are `1.989e-9` pixel
offset, `2.635e-9` pixel width, `9.520e-9` pixel-squared covariance error,
`1.657e-8` fourth-direction levels and `9.490e-8` finite-D levels. These are
matched mathematical-source checks with supplied target normals/noise and
generated radiometry, with brightness levels fitted inside bounds;
they are not physical accuracy specifications.

The mixture counterexample differs from its supplied true second-moment tensor
by `5.32455` pixel-squared Frobenius units and has `2.74389` levels maximum
finite-D discrepancy. Its separately labelled independent quartile-summary
countercontrol also gives a perfectly quadratic SPD tensor while missing that
target by `2.70697` levels. A Gaussian-equivalent spread is not necessarily the
true second moment or sufficient optical model.

For the common-response example,
`h(u)=Phi(a*Phi_inverse(u)+b)` transforms width `s` into `s/a` and shifts offset
by `-b*s/a`. A shared unknown response can therefore yield essentially exact
Gaussian edge profiles but covariance `Sigma/a^2`. Here maximum edge residual
is below `9e-11` levels while the physical-source covariance discrepancy is
`1.21489` pixel-squared Frobenius units. Rank, SPD and low residual cannot
resolve that response/PSF ambiguity.

All four alternate-source groups are numerically pooling-ready. Their retained
mismatch is deliberate evidence that readiness must not set
`gaussian_model_validated` or `physically_calibrated` true.

## Failure retention and development history

Seventeen CLI/flow controls pass. An injected first-case `ValueError` keeps all
13 rows; all **12 later actual numerical cases execute** and match canonical
serialized results apart from runtime. The report and printed JSON agree byte
for byte. Output validation precedes analysis and refuses existing destinations.

Initial development caught and repaired an extra half-pixel shift when using a
helper that already returns centres; boolean geometry coercion; and a false
local rank caused by projecting out brightness nuisance roundoff. The final
tests preserve those regression cases. No recovery tolerance was relaxed.

The first successful study used an incorrect label/reference for the mixture
covariance error: it compared against the base component instead of the supplied
mixture's true second moment `3.4*Sigma0`. That initial report remains locally
byte-preserved under `.local/verification/psf-calibration-initial-base-label-v1.json`.
Canonical v2 corrects the reported reference and value. Source means, fit
candidates, independent predictions, fixed plan and numerical targets are
unchanged. A first contract harness also compared in-memory tuples with JSON
lists; its corrected version exercises the actual CLI and reads serialized JSON.
Both development histories are retained locally, not relabelled final passes.

## Separate main-line behavior

During this work, `main` advanced independently to
`f1679bb50ca39e1764897e00124eccdf41b21f59`, including directional tracing from
[PR #77](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/77).
That main line does not contain the PR #75 research stack. Its rectified-rise
covariance estimator is not this raw source fitter, and these controls do not
qualify that separate implementation. The targeted rank-defect reproduction and repair are in
[draft PR #78](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/78),
head `185d682197437581083a8ecd46de6357d7adb846`. Its separate main-based suite
passes 633 tests; those checks are not part of this 1,844-test lane. This draft
does not imply the repair is merged or physically qualifies directional blur.

The final canonical run binds these SHA-256 values:

| Source or artifact | SHA-256 |
| --- | --- |
| `backend/edge_spread.py` | `44944261616d5bb01132daf6de7e1d3de81d8a679fa9e68ce2b8024093d1e8ff` |
| `backend/psf_calibration.py` | `06d5348fa54119c7307b3d0a626b78c5af05f6e05dc90f4d814631ccfe2cc282` |
| `backend/source_context.py` | `edf8f056793444f6577ee692833edb2ad6f40ba1c462524abaffc4e9322c8b41` |
| `studies/psf-calibration-v1.json` | `9737ca7b9c5079c5142bba23ea00f07db2ab16763f87a3e28e204a17cc52ff59` |
| `studies/verification/psf-calibration-v1.py` | `f444bb3ffdbdfa8125a8978746afcb3b63c851909dc12aed3a14d101f5f9c637` |
| `studies/results/psf-calibration-v2.json` | `378f09f06003967d56da8ef2340b3243357663a310e4788c211a95796e96a551` |

## Remaining engineering requirements

The caller must bind independently declared target geometry, fixed ROIs, source
identity, channel mix, noise/operator, search settings and physical capture
conditions. Geometric uncertainty, target-edge sharpness, camera response,
pixel integration, spatial variation and correlated summary errors still need
justified models or independent evidence. Supplying a fitted covariance to a
finite-shape experiment remains an explicit hypothesis. Automatic target
selection, camera qualification, accepted geometry replacement and print/fit
verification remain open.
