# Analytic normal motion: complete residual-information experiment

The first frozen-source execution **exited 0**. All **578 normal-derivative
comparisons**, ten algebra controls and five normal-control batches pass.
All ten eligible records receive exactly one bounded joint `BGNS` trial, and
all ten pass the original actual-versus-linear criterion. Both upstream refusals
remain among the 12 records. The original residual protocol remains false;
its failed finite-difference control and old three target passes/ten completions
are unchanged. No new fit-pass count is assigned.

The [method](../finite-analytic-normal-information.md) explains the independent
translation-only chord reference, error propagation, matched projection cutoff
and single training-only step. The result supports this numerical diagnostic;
it does not establish physical optics or automatic correction.

## Frozen source and population

The [plan](../../studies/finite-analytic-normal-information-v1.json), SHA-256
`28efd2aa241b662bdd2f771be48b37d99283c67033980dafc4e2dae23ff68dfd`,
was committed locally at `dfe0b68` before any new derivative, reference, SVD,
algebra control or trial evaluation. Final scientific source was committed locally at
`5a63e766b5ed1be28bbcc4a717c1d775eabf43c7` before the single execution:

| Scientific source | SHA-256 |
| --- | --- |
| [Driver](../../studies/verification/finite-analytic-normal-information-v1.py) | `4585f4fd620b2e9053bdac7faa5d89a99782a481281cfd8977d68a2638e36432` |
| [Independent affine reference](../../studies/verification/finite-analytic-normal-oracle-v1.py) | `a62202aa6ce9288377fdbf06b087c991947ce53e890df7393e61aa3fb57b27f2` |

All 45 frozen inputs match. All 48 runtime source bindings and all 558 outer
tracked non-Markdown files remain unchanged during execution. Documentation
PR #101 was incorporated before the scientific freeze. Subsequent saved-data
auditor and archive additions are separate from that frozen execution.

The archive contains five paired synthetic datasets and ten supplied covariance
hypotheses, not ten independent photographs. The original 560 observations,
baseline means, brightness faces and `B/G/S` columns/errors are reused exactly.
Four new three-pixel diagonal controls cross normal and contrast signs. The
original six-pixel normal control is post-hoc, evaluated by a new method.
Its archived name is `normal`; the frozen plan's `independent_normal_angle`
label is a descriptive alias for the authoritative control at index 3.

## Derivative and work results

| Check or work lane | Recorded result |
| --- | --- |
| New normal calls | 15 batches, 578 queries; all resolved and qualified |
| Normal API work | 1,156 endpoint work units and 578 panels; all affine closed forms |
| Independent chord reference | 73,984 complete fixed panels, 8,306,880 attempted/completed density nodes, 48,025 omitted-tail panels, zero guard failures |
| Tail-envelope work | 147,968 exponential calls, recorded separately from density nodes |
| Largest API/reference discrepancy | `1.64313e-14` probability per source-plane radian |
| Largest scaled normal-column error estimate | `6.24169e-10` intensity levels per radian |
| New actual trial means | 10 calls/560 queries, 1,092,212 evaluations and 112,504 panels |
| Forbidden work | Zero baseline regeneration, geometry-Jacobian replay, covariance finite differences, optimizer, renderer or preparation calls |

Each comparison meets both the requested `1e-10` probability/radian criterion
and the reported API-error criterion, with the frozen independent-reference
allowances. Signed contrast is applied once; all retained error components enter
the matrix guards. Fixed orders 64/96 and Decimal precisions 80/120 agree under
the frozen checks. These are engineering estimates, not certified error bounds
or a repair of the general projective reference oracle.

## What allowing angle motion changes

All **20 matched comparisons** (all 56 samples and training 40 for each eligible
record) retain three covariance directions both before and after adding normal
motion. The ten training projected spectra are nonincreasing as expected under
nested nuisance projection. Their weakest directions remain at least 301,936
times the shared cutoff under this estimated guard. This local result does not
identify a camera PSF or establish statistical significance.

Conditional covariance residual energy decreases in eight training cases and
increases in two (indices 0 and 7). Changing both the residual and covariance
projection permits that increase; it is not an increase in projected singular
values. The [two-dimensional example](../finite-analytic-normal-information.md#compare-covariance-at-a-matched-numerical-scale)
explains the distinction.

All full training matrices have resolved rank 10. Their condition numbers,
1,535–4,375, depend on the declared column scaling. Eight trials are limited by
the covariance-Frobenius cap; two use `alpha=1`. Applied angle changes range
from `-7.26248e-4` to `4.01214e-4` radians. The maximum ratio of actual linearity
discrepancy to its allowance is 0.66105, with no retry or damping selection from
held-out responses.

The table shows computed RMS in intensity levels. Held-out values already
influenced preprocessing and moments, so these are conditional residual checks.
`BGS` is the saved fixed-normal comparator, not another new execution.

| Case / covariance hypothesis | Baseline held-out RMS | Saved BGS RMS | New BGNS RMS |
| --- | ---: | ---: | ---: |
| Small isotropic / legacy | 0.453758 | 0.386851 | 0.409365 |
| Small isotropic / moment | 1.471537 | 0.981051 | 0.980536 |
| Small directional / legacy | 7.541359 | 7.241277 | 7.243535 |
| Small directional / moment | 0.693269 | 0.509797 | 0.514933 |
| Medium directional / legacy | 7.919997 | 7.575939 | 7.581462 |
| Medium directional / moment | 0.395774 | 0.209621 | 0.209617 |
| Large directional / legacy | 10.601772 | 10.211225 | 10.195014 |
| Large directional / moment | 0.352150 | 0.196770 | 0.224882 |
| Rotated major / legacy | 7.962687 | 7.661497 | 7.663177 |
| Rotated major / moment | 1.039312 | 0.749462 | 0.755428 |

New held-out RMS and maximum errors improve over the saved baseline in all ten
records. Against saved BGS trials, BGNS improves held-out RMS in only three
records and maximum error in six. Joint coefficients and common damping both
change; differences cannot be attributed to angle alone. Small numerical
differences are not evidence of practical or statistical significance.

## Residual improvement does not guarantee better geometry

Synthetic truth is examined only after every trial and prediction is fixed.
Relative to the archived baseline fits, centre error improves in seven records,
radius error in six, and chord-fraction error in seven. **Indices 0, 1 and 7
worsen in all three geometry metrics despite lower residuals.** These post-hoc
descriptive scores are retained without new
target-pass labels. They support investigating acquisition/model adequacy before
automatic adoption of extra fitted parameters.

## Independent review and complete archive

The [archive index](../../studies/results/finite-analytic-normal-information-v1-summary.json)
binds 36 complete compressed/decoded artifacts. The
[canonical report](../../studies/results/finite-analytic-normal-information-v1.json.gz)
decodes to **270,836,922 bytes**, SHA-256
`11607377de1a98446c07e53be67c01cf669fd99dca6f1ea0abf8284a1a47d387`.
Gzip is lossless, with zero mtime and no embedded filename. No row, panel,
precision result, original failure or work count is dropped.

- The portable standard-library saved auditor passes **257,459 checks**.
- The separate census/work/arithmetic auditor passes **803,488 checks**, including
  independent pivoted two-pass QR checks of all ten coefficient vectors.
- The mathematical saved-array auditor passes **722,095 checks**. It uses the
  same NumPy SVD kernel, with independently implemented surrounding arithmetic;
  this is not independent qualification of that SVD implementation.
- Thirty independent scalar checks reconcile the post-hoc synthetic truth scores.
  None of these auditors evaluates new models, density nodes or references.
- Ten blocked-import CLI/source-refusal checks, eight protocol-gate stub checks
  and thirteen portable-auditor static/CLI checks pass. The first stub fixture's
  7/8 failure is retained: its row stub lacked required metadata. Correcting that
  fixture leaves the governing scientific driver unchanged.

Static review corrected protocol-failure qualification and partial-work retention
before the scientific source freeze. No scientific result was rerun or retuned.
The [portable workflow](../../studies/fixtures/finite-analytic-normal-information-v1/README.md)
separates hash verification/saved auditing from an explicit new numerical run.
Its saved-data block was executed verbatim from the repository root: all 36
artifact hashes and decoded sizes match, and all 257,459 audit checks pass.
Documentation verification covers 97 Markdown files, 1,072 local links, 95
fragment links and 125 tables, with zero errors; all 97 files also parse with
the pinned `marked` 17.0.5 renderer. These are documentation and saved-data
checks, with no new scientific evaluations.

All 555 inherited non-Markdown files match the published PR #101 base byte for
byte and mode for mode. Application source is unchanged; no full application/browser suite, installed
slicer or physical print is newly qualified. Automatic refinement still requires
a qualified inverse, supported acquisition/illumination/thickness models,
independent measurements and preservation of the accepted CAD boundary.
