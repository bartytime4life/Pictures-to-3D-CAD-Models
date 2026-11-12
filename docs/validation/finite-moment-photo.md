# Finite-D moments on synthetic measured photo fields

This 2026-11-12 developer study preserves a local moment-inversion probe and makes its fixed inputs portable. It does **not** change tracing, blur estimation, CAD, an HTTP endpoint or a workbench control. Reproducing the probe is separate from qualifying its model or meeting its numerical targets.

The [original plan](../../studies/finite-moment-photo-v1.json), [portable runner](../../studies/verification/finite-moment-photo-v1.py), [fixture manifest](../../studies/fixtures/finite-moment-photo-v1/manifest.json) and [complete result](../../studies/results/finite-moment-photo-v1.json) retain all outcomes. The plan remains byte-identical to the plan frozen before the original probe. Neither targets nor the fraction domain were widened during packaging.

## What was measured and retained

The preceding synthetic capture baseline uses the existing PR #86 source at `dcb14e5c62ed6f4b3de4426e863aa48b007eb819`, snapping disabled and no thickness correction. Both complete six-case outcomes are archived:

| Capture baseline | Sheet | Returned traces | Refusals |
| --- | --- | --- | --- |
| [v1](../../studies/fixtures/finite-moment-photo-v1/baseline-v1-result.json) | A4 | 1 | 5, reference-sheet detection |
| [v2](../../studies/fixtures/finite-moment-photo-v1/baseline-v2-result.json) | Measured custom 60 × 60 mm | 5 | 1, minor-D outline contrast |

The custom sheet is an existing supported capture choice, not a detector-threshold change. The initial large-D fit contains two lines and two arcs, rather than one ideal arc/chord decomposition. All initial seed fits, measured scale and blur summaries remain available; the study selects the largest-radius observed arc and longest observed line. The line supplies the chord-normal direction, with its sign chosen from the observed arc. Synthetic truth does not supply the seed, normal, background or ROI.

Five compressed fixtures retain the exact 300 × 300 `float32` measurement fields `g`, with field-byte and container hashes. These are the production pipeline's linear-light channel mix **after** Keys rectification and 0.7 px Gaussian smoothing, not sensor RAW or an independently calibrated PSF. Original NPZ containers also contain object-valued covariance entries; the replay reads only numeric `g` and `points` with `allow_pickle=False`. The manifest includes observed seed fits, field bounds, pixels/mm, scalar blur, capture-source hashes and synthetic truth for later diagnostics. The original probe and capture scripts are archived as `.py.txt` provenance, not replay entry points.

For each eligible field, the original plan tries padding of 6, 8 and 12 times the observed scalar blur, with a 16 px minimum. It estimates background from the complete one-pixel ROI border. Each ROI is then evaluated at background offsets `0`, `−0.01`, `+0.01`, `−0.1` and `+0.1`. These offsets use the linear-light intensity scale where 0 and 255 retain their endpoints; they are deterministic sensitivity checks, not a noise distribution. Pixel coordinates are integer indices plus 0.5. Signed background-minus-field weights are never clipped.

## Conditional moment calculation

In the ideal continuous model, let constant background be `b`, constant material contrast be `a`, unit-mass PSF be `h`, and finite material be `K`. After subtracting the correct background,

```text
w(p) = b − I(p) = a (h * 1_K)(p),
M = integral w(p) dp,
rho(p) = w(p) / M.
```

Either contrast polarity cancels in this normalization when nonzero signed mass is retained consistently. The particular frozen probe is for dark material and refuses nonpositive mass. Finite-ROI signed pixel sums approximate these integrals; with background errors their normalized weights need not be a probability density.

The general relation between convolution and geometric moments is given in Shakibaei and Flusser's [*Image Deconvolution in the Moment Domain*, equation 5.3, pp. 113–114](https://library.utia.cas.cz/separaty/2014/ZOI/flusser-0429812.pdf). The following D-specific slice formulas and inversion are this study's derivation, independently checked during review; the chapter's image-reconstruction algorithm is not implemented here.

Let `X` be uniform on `K` and let independent blur displacement `Z` have zero mean and central symmetry. Then `rho` represents `X+Z`: its centroid equals that of `X`, its third central moments equal those of `X`, and its covariance is `Cov(X)+Cov(Z)`. This requires the whole convolution and finite relevant moments. Central symmetry is sufficient; invariance of third moments does **not** identify a Gaussian PSF.

For the unit D, `x²+y² ≤ 1` and `x ≤ f`, define

```text
s = sqrt(1−f²),  theta = asin(f)+pi/2,  A = theta+f*s,
mu = −2*s³/(3*A),
E[x²] = (theta−f*s*(1−2*f²))/(4*A),
E[y²] = (3*theta+f*s*(5−2*f²))/(12*A),
E[x³] = (−2*s³/3+2*s⁵/5)/A,
E[x*y²] = −2*s⁵/(15*A),
k30(f) = E[x³]−3*mu*E[x²]+2*mu³,
k12(f) = E[x*y²]−mu*E[y²].
```

In the observed chord-normal/transverse basis `B=[n,t]`, solve the supplied-domain equation `κxxx/κxyy = k30(f)/k12(f)`, then form

```text
R = (κxyy/k12(f))^(1/3),
C = observed_centroid−R*mu(f)*n,
S = observed_covariance−R²*B*diag(E[x²]−mu²,E[y²])*B.T.
```

The probe checks decreasing ratios at 257 sampled fraction values in the fixed interval `[-0.8,0.9]`, rejects ratios outside that range and performs 60 bisections. A separate 1,001-value numerical review supported the ordering on `[-0.999,0.999]`; neither sampling result is a monotonicity or uniqueness proof. Small third-moment signals near degenerate D shapes, uncertainty in the supplied normal and finite-image effects remain important conditioning limits. Returned `S` is in rectified squared pixels. It is a covariance difference under the declared model, not a calibrated raw-camera covariance.

## Complete outcomes

All **75 numerical attempts** and the **one upstream-ineligible case** remain in the 76-row result: 74 `moment_proposal`, one ratio-domain refusal and one upstream contrast refusal. Ten proposals have a nonpositive minimum covariance eigenvalue. Their values and original statuses are preserved; `moment_proposal` does not mean that a valid Gaussian covariance was recovered. No eigenvalue clipping or automatic geometry replacement is applied.

Nominal means 8-sigma padding and zero background offset. The fixed geometry targets are centre error ≤ 0.02 mm and absolute radius error ≤ 0.02 mm. **Four of five nominal cases pass; small-isotropic fails its centre target.** These are synthetic digital comparisons, not population rates or physical tolerances.

| Nominal case | Centre error, mm | Signed radius error, mm | Geometry targets |
| --- | --- | --- | --- |
| Small isotropic, R3 | 0.0242610 | +0.0037794 | Fail |
| Small directional, R3 | 0.0055417 | +0.0043385 | Pass |
| Medium directional, R6 | 0.0005391 | +0.0014019 | Pass |
| Large directional, R12 | 0.0022592 | −0.0003132 | Pass |
| Rotated major directional, R6 | 0.0036337 | −0.0062229 | Pass |

At zero offset, each nominal 8-to-12-sigma ROI comparison meets the original 0.01 mm change target: centre changes are zero at the stored precision, and the maximum radius change is below `7.2e−16 mm`. This agreement does not test a common background bias. In the small-directional case, offsets of `−0.01/+0.01` change centre errors to `0.03757/0.04530 mm`. For the rotated-major case, `+0.01` gives centre/radius errors of about `0.02296/−0.03669 mm`. Its 12-sigma, `−0.01` covariance estimate has minimum eigenvalue about `−3.75673 px²`. All larger-offset failures also remain in the complete result.

Background subtraction over a large finite ROI amplifies small errors through both signed mass and high-order moments. Thresholding the mass, clipping negative weights, substituting truth background or projecting `S` onto the positive-definite cone would change this experiment. The study does none of those. Nonconstant lighting, unknown response, resampling, truncation, finite pixel aperture and visible walls can break the assumed moment relation; a nonzero PSF centroid is also confounded with geometric translation. There is no Gaussian qualification, uncertainty interval, physical accuracy claim or moment-based auto-apply.

## Replay and contracts

From the repository root, using its installed dependencies and a fresh destination:

```bash
.venv/bin/python studies/verification/finite-moment-photo-v1.py --output /tmp/finite-moment-photo-review.json
.venv/bin/python studies/fixtures/finite-moment-photo-v1/replay-contracts.py
```

The runner requires a new `.json` output and an existing parent directory; stdout is the same complete JSON as the saved file. Missing/existing/symlink destinations are refused before NumPy imports or fixture analysis. The final exclusive create also refuses a file inserted after the initial check. It does not create parent directories, import the backend, rerun capture or query Git.

Exit 0 with `status: reproduced` means that all original parsed rows match exactly and bound inputs stayed unchanged; it does **not** mean all geometry targets pass. A changed numerical replay or mid-run source/input change is retained in a `replay_mismatch` report with exit 1. Invalid inputs or an output refusal exit 2. Existing files remain intact. Current capture-source hashes are reported separately from the archived capture revision; a later backend change does not regenerate these fixed fixtures.

The local portable replay on Python **3.12.3** and NumPy **2.5.4** retains every original numerical field exactly. Its **31 CLI/data checks** pass: early help/refusals with a numerical-import sentinel, existing and dangling symlink preservation, exclusive-write race, saved/stdout equality, exact-row and outcome conservation, repeated-run equality, before/after bindings and tampered-field refusal. Focused Ruff checks pass. No full application, browser or physical experiment was rerun for this packaging task. Exact floating replay on another numerical runtime is a checkable outcome, not a portability guarantee.

## Source and artifact binding

The report binds 23 files before and after replay: runner, original plan, manifest, contract helper, eight original provenance files, five measured fields, and six capture/generation sources. Each original baseline retains its own complete before/after hashes. The five production modules plus synthetic generator are unchanged from the archived capture:

| Capture/generation component | SHA-256 |
| --- | --- |
| `backend/reference.py` | `23a94e699d5499d8a4621902193e3a70214062108a5d0d10abb04df9efb8b69d` |
| `backend/fitting.py` | `99354fa9822a354bfabe6b9069e2872bc75afe88d627f8e431a5ef6bb6b72833` |
| `backend/edges.py` | `c02bcf6f15958ea5c82444de3ea3af37f20031e6df463846dc8082e37abae9ee` |
| `backend/sheet.py` | `e18cbe44c476894f1655d6ce66a5e1b11cefe9ca4f95e7e17eb7f52efc236531` |
| `backend/circular_joins.py` | `1647721fe8763c61ae3c3fe2eb51201fc1d3cf5866c27a49caa74e66e682bde7` |
| `tests/synthetic.py` | `58a19b94363e71a9889fd49eb4904989f0e3101221c5c13b2a54bd536c424c4c` |

| Artifact | SHA-256 |
| --- | --- |
| Unchanged original moment plan | `7aa2762c329bb42407addd2416ef7ddb90d552664c64051ac47845fe418a44ad` |
| Original moment result | `23e8eff8c84ec50adc2c4f82815399ed15f20694717fcd0d02a2a4af16fd8fc6` |
| Original A4 baseline plan / result | `5ddf980ba75623cc1294e1f5863e44567c4752dda51889ec9c78fbd24c7ba73b` / `3900c65b314057a110d02d9235b809afa24f5af1f017965717a45d089be5c6ac` |
| Custom-sheet baseline plan / result | `2db3148f3be75ea7f9750aeae7115dd23762a581c1f3f879b484c7e1b3c9d687` / `e8a07de6297f1c5f9b71d1cd13a3a70e14664242475ae34446e1fe9ffc7183da` |
| Portable runner | `5c6b82adf877d6b6b6517dea379d9d9dd0c60c6de8339a117e593d164344bf5e` |
| Fixture manifest | `dcb8803fdb99895a14ae86899536985604d134d02bd65117f8028d97fc050855` |
| Portable contract helper | `41c14c824355017486f3f65f4452ba266b4c70fc656c75a753d0d13ed6c7d291` |
| Complete portable result | `b0d4f56c0815a11c7c9a1b7a40f0b385b346ad16e11e604edcde7ef1c61f3c50` |

The [canonical-join and directional-free-arc record](directional-free-arcs.md) describes the preceding production behavior and its separate optical counterexamples. This moment study supplies a conditional, background-sensitive geometry proposal for further investigation; it supplies no new production acceptance rule.
