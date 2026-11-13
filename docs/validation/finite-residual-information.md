# Finite-material residual information — November 12, 2026

The fixed [plan](../../studies/finite-residual-information-v1.json) asks what
covariance directions remain locally distinguishable after brightness and
geometry projection at the archived best fits. It keeps all 12 case/lane records,
the same 40 training and 16 held-out observations, supplied optics, domains and
old pass flags. It performs no inverse optimization, rendering or re-preparation.
The [method and rotation derivation](../finite-residual-information.md) and
[complete archive/review instructions](../../studies/fixtures/finite-residual-information-v1/README.md)
separate the planned replay from the later post-hoc analysis.

## Governing outcome: failed protocol, retained unknowns

The original replay **exits 1**, with `protocol_passed: false`. It retains all
12 rows: ten diagnostic-unknown records and two upstream refusals. All original
three target passes and ten completion flags remain unchanged; there is no new
fit-pass count. Six algebra and ten safe contracts pass, as do three of the four
independent positive-area controls. The normal control misses its fixed absolute
step/half-step allowance: **0.0004222865848 > 0.00002** linear-light levels per
radian. Production and positive-area fine derivatives nevertheless agree within
**2.7712e-10**. Matching two implementations at the same finite-difference step
does not resolve that step's truncation error. The failed control and full report
are preserved, without retry or tolerance change.

All 30 covariance columns across the ten eligible records pass their declared
finite-difference stability checks. Every archived normal column fails that
check, so all ten brightness/geometry/normal/covariance (`BGNS`) steps are
withheld. Valid `BGS` calculations are retained under a **fixed supplied normal**;
they are not jointly normal-qualified results and do not establish a physical PSF.

## Fixed-normal conditional results

With brightness and geometry projected out, all ten training matrices retain
three covariance directions under the estimated guards. The projected covariance
energy represents **44.8–94.4%** of the remaining training residual energy in
these local linear spaces. This is unweighted conditional linear algebra, not a
statistical significance or confidence measure. With the normal block unresolved,
covariance uniqueness against an unknown normal remains unqualified.

Each `BGS` step uses only the first 40 observations and the same retained SVD
cutoff. One common damping factor enforces the original geometry/brightness
bounds and the fixed covariance/geometry caps. Exactly one actual forward
trial is evaluated per eligible row; all ten satisfy the frozen actual-versus-
linear check. The original held-out values never select damping or a retry.

| Case | Lane | Held-out max before | After one bounded BGS step | Common alpha |
| --- | --- | --- | --- | --- |
| small-isotropic | scalar | 0.856553 | 0.709816 | 1.000000 |
| small-isotropic | moment | 3.564800 | 2.503041 | 0.374469 |
| small-directional | scalar | 17.182066 | 16.641910 | 0.040772 |
| small-directional | moment | 1.442766 | 1.019119 | 0.304514 |
| medium-directional | scalar | 18.028818 | 17.172592 | 0.049817 |
| medium-directional | moment | 0.845169 | 0.464360 | 1.000000 |
| large-directional | scalar | 17.958465 | 17.110324 | 0.039895 |
| large-directional | moment | 0.865774 | 0.664436 | 0.572515 |
| minor-directional | scalar | upstream refusal | retained | — |
| minor-directional | moment | upstream refusal | retained | — |
| rotated-major-directional | scalar | 17.964488 | 17.330640 | 0.043670 |
| rotated-major-directional | moment | 2.451006 | 1.803439 | 0.285663 |

Intensity values use the archived linear-light level scale. Residuals decrease
in this fixed conditional check, but the small-isotropic moment,
small-directional moment and rotated-major moment rows still exceed the original
one-level held-out target. No original target is relabeled. Truth is accessed
only after predictions for descriptive geometry errors, all retained in the
[readable index](../../studies/results/finite-residual-information-v1-summary.json).
Held-out pixels already influenced preparation/moments; they are conditional
residual checks, not independent predictions.

## Independent saved-data review

The portable [standard-library auditor](../../studies/verification/finite-residual-report-audit-v1.py)
passes **42 invented algebra/parser controls** and **9,683/9,683** saved-data
checks. It independently computes small-matrix Jacobi SVD, pivoted QR away from
cutoffs, residual/stratum arithmetic, finite differences and propagated errors,
projection/cutoff qualification, training-only coefficients, common damping,
SPD covariance charts, source binding, work counts and old flags. Seven QR rank
crosschecks are explicitly withheld near numerical cutoffs; their independent
Jacobi spectra remain. The audit confirms `protocol_passed: false`; its own
exit 0 does not replace the replay's exit 1.

All ten new baseline held-out arrays reproduce the original saved best-fit
predictions within the combined estimated forward/roundoff guard; the maximum
difference is **1.012e-9 levels**. This is source/parameter identity evidence,
not a new fit target or optical-model validation.

The canonical work log retains **196 mean calls and ten geometry-Jacobian
calls**, including the 16 synthetic derivative-control means and ten actual
`BGS` trials. It reports 21,290,976 returned evaluations and 2,101,194 panels.
Optimizer attempts, renderers and preparation calls are zero. The one-shot
launcher records the terminal exit and all 38 unchanged source/input members.
Its roughly 9.55-second elapsed time is execution provenance, not a latency
benchmark or an interactive-performance claim.

## Separate post-hoc rotation identity

After observing the normal failure, a separately frozen
[saved-array script](../../studies/verification/finite-normal-rotation-saved-v1.py)
uses the Gaussian rotation identity in the [method guide](../finite-residual-information.md#analytic-rotation-sensitivity-a-post-hoc-next-hypothesis).
It combines the saved centre derivatives and stable covariance columns in the
correct crop/global frame, without another model call or trial. Across all ten
eligible rows, coarse/fine maximum discrepancies have ratios **3.9991–4.0020**,
consistent with second-order central-difference truncation. Saved Richardson
comparisons range from 3.514e-10 to 2.134e-6. These shared-source comparisons do
not independently validate the identity's numerical implementation or qualify
any formerly unknown `N` column.

An independent saved-only scalar calculation uses raw centre Jacobians and
closed-form covariance coefficients rather than the script's matrix products.
All **560 identity values** agree within **1.146e-13**, estimated error sums
within **1.695e-21**, and all frames, rows and 38 bindings match: **13/13** checks.
The first audit retained **12/13** because its closure reader incorrectly expected
bare SHA strings instead of `{sha256, bytes}` records. Both receipts and the
corrected audit source remain in the archive. Correcting the reader changes no
numeric criterion or model result. This remains saved-data consistency only.

The next independent normal-derivative experiment should compare a direct chord
shape derivative, its truncated-normal first-moment form and positive-density
quadrature over new synthetic conditions. That implementation and experiment
remain undone. An acquisition-matched model still needs actual source samples,
transforms, finite kernels and stage bytes absent from the portable archive.
No causal optical, physical-accuracy or automatic CAD-adoption claim follows.

## Source and artifact binding

| Artifact | SHA-256 or exact source |
| --- | --- |
| Frozen plan | `837c626d7add9ebc6927d60245b85c1ad9bd361adaf8205e4bf62a4efd322532` |
| Diagnostic runner | `c4da819d3bf34bc4183fe55529d87acedc2946bf0fcdcd878ae2fd20eb3e7d69` |
| Complete decoded report, 8,973,743 bytes | `b1d15d4e006d1f65823cb6bd20810cd127d6d6ac6912973d590f38bd8acc6c74` |
| Portable saved-data auditor | `10c87e05f330d110f56a0740580af644b6117981d2eaea02ee31f820995d1e02` |
| Saved rotation-analysis source | `35579c70afff504e7af3d9a56ab4177c513090b5561737caa144e0061c7484dc` |
| Saved rotation report, 217,943 bytes | `6e957b1da5df7ffe84ab949cea3e3c527311e9edeffbdbdcb8ffed6167a8bf71` |
| Plan / diagnostic source commits before replay | Local `370bd32` / `8663026`; source and terminal manifests retained |
| Publication base | Documentation PR #94, `2f9abf2a4d2e1b809d2f3115f04fc04470682c4f`; inherited backend and input bytes unchanged |

Compressed and decoded hashes for every complete artifact are in the
[index manifest](../../studies/results/finite-residual-information-v1-summary.json).
The old preflight runner is provenance only; the final frozen source fixes
ceiling promotion of uncertain rank and classifies malformed FD/step responses
as protocol failures. Sixteen internal and 11 external safe contracts pass before
the numerical replay. The original plan, runner and failed report remain unchanged.

The three new scripts pass Ruff, formatting and compilation checks. This study
changes no production backend, frontend, tests, old study or generated-library
bytes. The inherited 943-test software result belongs to PR #93's unchanged
software interval; this is not a newly repeated full software/browser suite.
All **82 Markdown files** parse with locked `marked` 17.0.5; **907 local
references**, **87 heading fragments** and **110 tables** pass. The documented
portable archive block verifies all 17 compressed/decoded artifacts, reproduces
all 9,683 saved-data checks and reproduces the complete rotation JSON exactly.
All three new help commands pass. On the publication copy, the 16 no-model
contracts and 42 independent auditor sentinels also pass. All **370 inherited
non-Markdown blobs** remain identical to the PR #94 base. Whitespace checks pass.
No extra archived forward, derivative or trial is run during these checks.
