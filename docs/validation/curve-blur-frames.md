# Blur-frame transport: engineering evidence

This candidate starts at [PR #83](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/83), source `48e4bb5b329a900b41c0f2baca3ec7e769a48682`, in an isolated worktree. The primary checkout remains at `d747e30697a99a8f90d747d23d6ab7c1fa8b95ed`. The [model guide](../blur-frames.md) explains which observations share a scale and which approximations remain unsupported as stationary Gaussian models.

## Reproduced coordinate error

For a known homothety `x_new = nadir + k*(x_old - nadir)`, covariance transforms to `k² Sigma` and every Gaussian standard deviation to `k sigma`. This follows by applying the same linear map to the centered random displacement. It does not infer missing optical information.

The existing free-radius series is `C(r,s) = r + s²/(2r) - s⁴/(24r³)`. Every term has length degree one, so `C(k*r,k*s) = k*C(r,s)`. Leaving the spread unchanged instead adds

```text
Delta = s²/(2r)*(1/k-k) - s⁴/(24r³)*(1/k³-k).
```

Exact rational arithmetic at `r=6`, `s=2`, `k=4/5` gives expected mapped output `5.064197530864197`, unchanged-spread output `5.210638503086420`, and extra frame error `0.146440972222222 px`. Transporting the spread gives exactly zero commutation error in rational arithmetic. This identity does not validate the radius series as a physical model.

A separate exploratory reproduction used independent finite Gaussian disk half-level observations, actual `fit_ring`, `correct_thickness` and `correct_blur`. For supplied radius 12 px and covariance `diag(1,9) px²`, the unscaled spread after a 0.6 top-face map adds `0.1338876772 px` frame error. The original finite scalar-model radius error, about `-0.0036430134 px`, is a different quantity and remains after correcting the frame. All six exploratory rows, including a disk with no half-level contour, remain in ignored source-bound development receipts.

## Prospective independent experiment

The [frozen plan](../../studies/curve-blur-frames-v1.json) was declared before evaluating the revised source. It contains 36 uniform rows (three shape/support classes, two Gaussian models, two rotations and three scale factors), eight separate mixed/support controls, and two disks whose center mass is below one half. Four independent oracle self-controls are also retained.

The [runner](../../studies/verification/curve-blur-frames-v1.py) uses positive conditional-normal area slices with standard-library `erfc`, targeted Gaussian/circle cuts and a cosine substitution at circle endpoints. A finite capsule is integrated as a rectangle and two disjoint half-disks. It does not reuse the production curvature correction as an observation generator. Rotated controls use an exact orthogonal change of coordinates on those independently generated sources.

The fixed criteria are `1e-6 px` for stored-geometry commutation, `1e-10 px` for the actual point map and `1e-8` for oracle order agreement and half-level residual. Finite-shape approximation errors are reported separately, with no recovery target imposed on this transport experiment. Free-arc controls concern stored radius/center transport, not a claim about canonical arc joins or exported geometry.

The [public canonical replay](../../studies/results/curve-blur-frames-v1.json) retains all **46 rows and 200 checks**, with zero failed checks or execution failures and identical before/after source hashes. Maximum uniform stored-geometry commutation error is `2.59348e-13 px`; maximum actual point-map error is `1.42109e-14 px`, GL32/64 disagreement about `4.44e-16` and half-level residual about `4.40e-13`. These numerical observations are not certified probability or floating-point enclosures. The preceding development run is preserved separately, rather than substituted for this canonical replay.

The runner's separate **14 contract checks** pass. They cover read-only help, fresh/existing/dangling/invalid destinations, strict JSON output and failure continuation. Injecting failure into the first actual production `fit_circle` call retains all 46 attempted rows and 105 actual fit calls; the remaining 45 rows match canonical numerical results after excluding runtimes. One failed row cannot silently truncate the matrix.

Remaining conditional finite-source approximation errors include approximately `-0.003643 px` for an anisotropic full circle, `+0.441934 px` radius and `0.592849 px` center error for a short anisotropic free-arc sector, and `0.006967 px` cap-center error for the anisotropic capsule. Coordinate consistency does not solve those directional/finite-shape approximations. No physical capture or manufacturing accuracy is established.

## Why a short free arc still has directional bias

The leading Gaussian displacement at direction `n` is `b(n)=det(Sigma)/(2R n.T@Sigma@n)`. This is the Gaussian specialization of the tangent-plane kernel-moment expansion in [Elsey and Esedoğlu, appendix, Proposition 13](https://websites.umich.edu/~esedoglu/Papers_Preprints/elsey_esedoglu_anisotropy.pdf). Applying it to this circle-fit problem is a separate inference, not a camera qualification from that paper.

For a partial arc, a free-circle least-squares fit can absorb `-b(n)` into both a radius shift and a center shift: `delta_R + delta_C dot n`. It does not merely take the full-circle angular average. At radius 12 px, `Sigma=diag(1,9)` and the 33 declared directions from -60 to +60 degrees, independent linear least squares predicts `delta_R` about `0.294244 px` and center-X shift about `-0.557863 px`. Adding the scalar mean correction of `0.125 px` leaves a predicted radius bias about `0.419244 px`, consistent in direction and scale with the separately retained finite-source error of `0.441934 px`. This is a leading-order explanatory calculation, not an error bound or a new acceptance threshold. Correct frame transport cannot remove that mechanism; an adequate directional partial-arc model remains required.

## Retained integration failures

The first 21-test core run had 20 passes and one exact-window-boundary failure: floating-point rounding admitted a different sample after scaling, moving the fitted centroid by 0.075 px. The adversarial test remains. A conservative arithmetic tie policy now requires a point to be numerically beyond a positive blur exclusion margin; its length-valued guard scales with the window arithmetic. It adds no physical allowance and is not a rigorous global floating-point bound. The final core run passes all 27 tests, including actual scalar legacy-geometry retention and injected zero, negative, nonfinite and sharp-bound controls.

The initial reference integration run had **26 passes and one failure**. New scalar mixed-corner withholding exposed an invalid corrected source ring in an existing thick rendered photograph. The initial geometric fit was valid but its complete source distance was `0.736182 px`, beyond the existing `0.258348 px` fitting tolerance, so recovery correctly refused it. A `buffer(0)` cleanup produced three nonzero polygon components. A single preselected closing at `epsilon = tolerance/16`, retaining the whole computed geometry, also failed reverse source coverage (`0.739671 px`). Those candidates were not accepted and the distance allowance was not enlarged.

A further development probe kept all seven `make_valid` faces, closed at the same fixed epsilon and retained two holes; the existing no-interiors rule refused it. Opening both holes to the exterior along predeclared shortest corridors at that same epsilon then produced one valid, hole-free, 956-line polygon. Its final outer boundary passed both source tubes (`0.0845133 px` against `0.258348 px`), and separated-component/distant-hole controls still refused. Nevertheless the actual scalar pipeline's independent outside-size error was **0.13948822 mm**, beyond the unchanged **0.05 mm** limit. The small-hole, bore, slot and position errors passed their own limits. Source proximity and validity did not establish correct dimensions. This topology-changing candidate was rejected; no cleanup, component selection, hole opening, tolerance increase or relaxed fixture was added to production.

## Final mixed-frame policy and focused integration

Uniform support now transports `sigma` and supplied covariance for the free curves, scalar/covariant corners, slot caps and line windows described in the [guide](../blur-frames.md). Exact point labels determine each support; different scales are not averaged into one PSF.

For mixed scalar nonparallel support, the existing geometry approximation remains available with `blur_frame_mixed` and infinite internal `r_sd`. It cannot emit a finite sharp-resolution bound or delete a corner as sharp. A zero, negative or nonfinite model radius retains a positive finite initial geometric arc with `blur_correction_withheld`, preventing another generic correction; otherwise the fit remains unresolved. Mixed supplied-covariance nonparallel support keeps PR #83's withholding and bounded outline-recovery/refusal behavior. Mixed free curves and slot caps keep their explicitly warned legacy approximation. The warning is emitted only when a marked analytic candidate survives final assembly.

The final reference-focused run passes **27 tests** with runtime warnings treated as errors, including the original scalar renderer's five independent feature limits, actual directional recovery, per-point scale propagation and emitted-warning gating. Its source hashes are unchanged before/after. The legacy geometry path is retained as an inspectable reconstruction hypothesis, not as evidence of an identified mixed-frame Gaussian or calibrated radius uncertainty.

## Final verification

The full run finishes with **725 passed, zero failed/errors/skips**, terminal exit zero, in 188.20 seconds as reported by pytest (188.995 seconds including wrapper overhead). Runtime warnings are errors. All **277 frozen non-Markdown source/configuration/test/plan/runner files** and **22 built frontend files** remain unchanged throughout the run. Markdown and canonical study-result JSON are excluded from that executable-source freeze and checked separately.

After this run, a fresh remote read showed main at `cad695f4a298a5530f92515d5a738decd1152721`, with PR #82's 45-minute CI budget. PR #83 had merged into its documentation base after that base's upstream PR closed; main did not yet contain its corner implementation. The isolated candidate preserves that implementation and integrates main. The merge changes exactly `.github/workflows/ci.yml` relative to the frozen regression inputs; its bytes exactly match that main commit. No application, test, dependency, study or built byte changes. The full Python suite is not represented as having run after that configuration-only merge; a separate hash comparison proves the runtime inputs remain identical.

After main integration, **both focused sheet-reference browser scenarios pass**, terminal exit zero, with zero skips, unexpected outcomes or flaky retries, in 16.586 seconds as reported by Playwright. They exercise actual tracing, thickness re-tracing, sheet switching, saved project state and STEP/DXF/SVG/PDF/OpenSCAD exports; one also scans the upload dialog with axe. All 277 integrated frozen files and 22 built files remain unchanged throughout. The backend uses an isolated temporary job directory on loopback port 18796. These two scenarios are not a rerun of the earlier complete 74-scenario browser suite or a full accessibility audit.

Build/type checking, Ruff and frontend/browser-source formatting pass. The documentation contract check passes **15 read-only commands** and **11 HTTP operation/source/OpenAPI/documentation mappings**. The companion library's **19 documentation tests** pass. The repository-wide navigation audit passes across **63 Markdown files, 625 local references, 50 fragments, 90 tables and one local HTML reference**, with document bytes unchanged during the check. It checks current and historical Markdown together; historical records retain their original revisions, counts, failures and meaning. Terminal source/documentation fingerprints are retained with the ignored verification receipts.

| Bound artifact | SHA-256 |
| --- | --- |
| `backend/fitting.py` | `5791fd421ffbfb1b88fe0b49f7c5fde452f678055dbf4e6a43ad8310bd0ba485` |
| `backend/reference.py` | `30ca880cddabbc027ab3758f1f6ee599e89b5ef553d69f90e08173e82b811004` |
| Prospective study plan | `268ccca265df67035fa872a414b3479c894bbc3a738728a9e09b4bacbea5ba49` |
| Independent study runner | `86b89e6f5b5ef09ee43f575c108923170ab7c97ea4fbd190246385ce91814625` |
| Public canonical result | `06dc8326097e4dcba29dd95a75ac6334d40cc5bd06ae87b26cde64605041a10d` |
| Python regression source/build freeze | `e568a2beabfe0ad7e4e5df6cd984f09636ae3bf4469e542af3bdb24828c6cc2f` |
| Python regression JUnit | `21f01602cd19be60067da7da0ff30dd41efc9252187bd9cfa26f4eb63ee548b6` |
| Integrated browser source/build freeze | `48b617951f8b8476b6db891c00a28d4bdecf6b6bc7c319aa18ceeb9800ebbd3b` |
| Browser JSON report | `3a154d7ec28a72e2dcab6a32a1b90597d4cb9a9698508aa53ee8489a19a3a804` |
| Fourteen study-contract checks | `00b4a8b3a9980bd32136c3fdfa6d07c895045105dfeea749ebb3cf915ec70e98` |

Focused receipts, earlier failures, rejected probes and the runner's injected-failure result remain separately preserved under the worktree's ignored `.local/verification/` directory. The runner emits strict JSON identical to its output file, refuses existing destinations and preserves adverse rows. None of these local, exact-input mathematical or generated-image checks establishes real-camera calibration, physical dimensions, native slicer acceptance or print fit. No private photographs were used by these experiments.
