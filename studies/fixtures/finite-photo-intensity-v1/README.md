# Preserved actual-measurement intensity diagnostic

This archive preserves the prospective v1 diagnostic without rerunning or changing its plan, inputs, targets or fitting results. It uses five generated-photo measurement fields captured from the actual PR86 sheet-tracing path; the sixth source trace was already refused. It does not use private photographs, calibrate optics or qualify physical dimensions.

The copied plan and full result are byte-identical to the original ignored artifacts. `provenance.py.txt` preserves the original runner as text: it still names its original local inputs and output directory. **This is not a standalone replay command.** `input-aliases.json` maps the original inputs to existing portable moment fixtures by verified SHA-256. Replaying would require a future caller that resolves those aliases explicitly; no such caller or rerun is claimed here.

All 12 declared lanes remain: ten fits returned, seven satisfy the frozen completion flags, one meets every target, and two retain the upstream refusal. All 21 frozen source/helper/input files remain unchanged. There are no execution-failure rows. The terminal exit code is 1 because the predeclared all-lane target is not satisfied; it is not an interrupted run.

Targets are centre error <=0.02 mm, absolute radius error <=0.02 mm and maximum held-out intensity error <=1 linear-light level, with a best candidate, rank four and no work, refinement, unrefined-basin, numerical, flat, tied, endpoint or rank-deficiency flags. Forty training and sixteen disjoint held-out pixels come from the same fixed observed-field helper. The only between-lane configuration change is covariance; its blur-dependent ROI/padding can also change sample selection, so this is not a controlled same-pixel comparison of covariance alone.

| Case | Covariance lane | Target | Completion | C error mm | R error mm | Held-out max | Truth in box | Unfinished |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| small-isotropic | scalar | pass | yes | 0.000942141 | 0.00182286 | 0.872638 | true | 0 |
| small-isotropic | moment | fail | yes | 0.00408641 | 0.000747372 | 2.0113 | true | 0 |
| small-directional | scalar | fail | no | 21.5639 | 20.5497 | 61.6262 | false | 3 |
| small-directional | moment | fail | no | 20.0785 | 19.3409 | 59.2398 | false | 3 |
| medium-directional | scalar | fail | yes | 0.0624634 | 0.101495 | 19.044 | true | 0 |
| medium-directional | moment | fail | yes | 0.00960349 | 0.00894277 | 1.63436 | true | 0 |
| large-directional | scalar | fail | yes | 0.0417275 | 0.0323292 | 13.5916 | true | 0 |
| large-directional | moment | fail | no | 0.216187 | 0.0426812 | 54.1148 | true | 1 |
| minor-directional | scalar | fail | upstream refusal | — | — | — | — | — |
| minor-directional | moment | fail | upstream refusal | — | — | — | — | — |
| rotated-major-directional | scalar | fail | yes | 0.0384373 | 0.0487387 | 8.31927 | true | 0 |
| rotated-major-directional | moment | fail | yes | 0.00126921 | 0.0111344 | 2.9931 | true | 0 |

The two small-directional lanes expose an observation-policy failure: the whole-sheet border gives a background estimate of 131.1277 instead of the central paper level near 201.781. Threshold crossings span the entire 300-by-300 field, include border pixels in training, and generate a seed/search box excluding the true part. Their large errors and unfinished basins are not labeled converged intrinsic Gaussian-model bias. The large-directional moment lane also remains unfinished (`no_descent`, one unrefined basin). None of the ten fits exhausts the forward-work budget.

The small isotropic scalar lane improves centre error from the archived geometric fit's 0.07545 mm to 0.000942 mm and passes all frozen targets. The nominal moment lane on that same case completes and has small geometry errors, but fails the held-out intensity target. Medium and rotated-major moment lanes likewise have small centre/radius errors but held-out discrepancies above one level. Numerical completion and SPD covariance therefore do not establish model adequacy.

Moment matrices are retained raw and canonicalized only for antisymmetry within 64*eps*maxabs(S). Every representation change is recorded before fitting; no indefinite matrix is repaired or eigenvalue-clipped. The matrices remain data-derived effective hypotheses, not calibrated optical PSFs.

The next engineering step is a separately declared observation-domain bridge using the existing measured-ring bounding box with fixed blur padding, and an explicit crop-to-global homography. That step is not implemented, run or substituted into these v1 outcomes. No automatic trace/CAD promotion follows from this archive.

Raw result size: 1,618,042 bytes. Runtime: 168.370119 seconds. Plan SHA-256 `083fb18d5b42479282fcae7214646a396bd8bba8936633ea02ec090235ec2e95`; result SHA-256 `27380cfa0db6e0f057527e398673cd7fa9c611677c395e73aa896734d7d5e6c9`.
