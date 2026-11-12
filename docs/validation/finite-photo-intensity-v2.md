# Measured-ring observation bridge and paired intensity replay

The [frozen version 2 plan](../../studies/finite-photo-intensity-v2.json) tests a
data-contract repair for the [captured-field diagnostic](finite-free-centre.md#captured-field-integration-diagnostic).
That earlier diagnostic let the whole reference-sheet border contaminate a
small part's background and seed. Its two large directional errors were
initialization failures with unfinished basins and truth outside the search
box, not evidence of converged intrinsic Gaussian-model bias.

The new source builds on documentation PR #89 at
`8cd6e93875ffbc02f81587e0d3aac908f9affab1`. Existing fit, finite-mean,
reference, rendering, fixture and version 1 result bytes are unchanged.
The bridge is a Python developer function; no trace/build HTTP route or
automatic CAD selection uses it.

During final publication, the preceding PRs were merged into dependency branches
that had already closed. Main at `82017b96337430b5ed90f8d88fee1d0feff6d7e5` still
lacked their join/finite-material contents. The separate
[integration draft PR #90](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/90)
computes exactly the published PR #89 tree, with current main and PR #89 as
parents. This candidate now builds on that integration. Bringing it into the
tested working branch changes no file bytes; all 282 software and 38 science
hashes still match their completed runs. Subsequent publication-state edits are
documentation only. No geometry or study retest is claimed for the history merge.

## Prospective contract

The plan was frozen before any version 2 inverse recovery at SHA-256
`6563b63d283ad984cba38d2275cb20163c28da4b270c6d2a5d419548a15024ae`.
It retains all six original synthetic rendered capture cases and both covariance lanes. The five
available saved fields and measured rings are replayed; the minor-directional
upstream refusal remains in both lanes. No image is replaced, rendered again
or retraced.

Each eligible case prepares one crop with fixed measured-ring bounds and
padding `ceil(max(16,8*common_sigma))`. `common_sigma` is the larger of the
captured scalar width and the largest principal spread of the valid nominal
observed moment proposal. The two covariance lanes then reuse identical crop
bytes, 40 training/16 held-out samples, global seed and bounds, fixed normal and
global-to-crop mapping. Only supplied covariance differs between those lanes.

Version 1 to version 2 changes both the observation region and the prospectively
declared shared-width preparation policy. It is not a crop-only ablation.
The normal comes from archived observed line/arc witnesses. Truth is read only
after fitting and held-out scoring. The unchanged targets require centre and
absolute radius errors at most 0.02 mm, held-out maximum intensity error at most
one level, rank four and no incomplete, numerical, flat, tied, endpoint or
rank-deficient fit flags. Grid and refinement remain local finite searches.

Held-out indices are disjoint from the nonlinear fitting objective. Their
intensities still influence the field-derived seed and moment proposal, so
these are conditional diagnostic residuals, not independent prediction or
physical accuracy evidence.

## Observation and failure controls

Before any recovery, actual-data controls test byte-preserving crop snapshots,
changes confined outside the crop, an integer field/ring translation, complete
padding refusal and both covariance lanes' observation frames. The independent
mean check uses the separately implemented positive-area conic-slice integral,
at the data-derived seed, rather than rendering through the production mean.
It compares 32/64 integration orders under unchanged numerical tolerances.

Code review found and corrected source-dtype conversion and mutable NumPy
descriptor gaps before fitting. The bridge now stores immutable bytes, dtype
and shape, and returns fresh read-only views; arithmetic uses separate finite
float64 buffers. Focused controls include endian/strided source bytes, caller
mutation, overflow refusals and observed-only sample/bounds binding.

Runner failures must remain strict-JSON data, with unsafe payload fields named
and withheld, failure stages recorded and pass flags reset. Separate controls
exercise nonfinite fit/control payloads and errors after scoring. Synthetic
routing sentinels establish routing/serialization only; they do not substitute
for an actual first-fit-failure continuation.

## Results and source binding

The [complete result](../../studies/results/finite-photo-intensity-v2.json)
retains **12 rows**, with **ten completed fits**, **two original upstream
refusals** and **zero execution failures**. Every available fit has rank four,
no incomplete/ambiguity flags and evaluation truth inside its observed bounds.
All five paired preparations are exactly identical between their covariance
lanes. All 30 actual observation controls pass; the 38-file source/input closure
is unchanged. Saved JSON and captured stdout are byte-identical.

**Three of twelve rows meet every unchanged target**, compared with one of
twelve in version 1. The complete run retains exit **1**; it is not an all-target
pass. The available fits below all completed. Error columns are absolute centre
distance/radius discrepancy in mm; held-out error uses linear intensity levels.

| Case | Supplied covariance lane | Centre error, mm | Radius error, mm | Held-out maximum | All targets |
| --- | --- | --- | --- | --- | --- |
| Small isotropic | Scalar identity | 0.003283 | 0.000535 | 0.8566 | Pass |
| Small isotropic | Nominal moment | 0.005282 | 0.000933 | 3.5648 | Miss |
| Small directional | Scalar identity | 0.110384 | 0.004646 | 17.1821 | Miss |
| Small directional | Nominal moment | 0.004003 | 0.000249 | 1.4428 | Miss |
| Medium directional | Scalar identity | 0.027188 | 0.030778 | 18.0288 | Miss |
| Medium directional | Nominal moment | 0.004435 | 0.001404 | 0.8452 | Pass |
| Large directional | Scalar identity | 0.018349 | 0.006271 | 17.9585 | Miss |
| Large directional | Nominal moment | 0.001291 | 0.001361 | 0.8658 | Pass |
| Rotated major | Scalar identity | 0.023336 | 0.022342 | 17.9645 | Miss |
| Rotated major | Nominal moment | 0.010672 | 0.005236 | 2.4510 | Miss |

Both minor-directional lanes remain upstream-ineligible. All five nominal
moment lanes meet the centre and radius targets, but three miss the one-level
held-out criterion. The small-directional scalar fit now completes inside the
observed box, but its centre and intensity errors remain too large. These
outcomes remove the known whole-sheet initialization failure without proving
adequate optics or authorizing automatic geometric correction. Version 1 is
read and compared by all twelve parsed-row identities; it is never rerun or
rewritten.

The run takes **141.870 seconds**, with individual fits around 8–19 seconds on
the recorded machine. Neither this replay nor the developer API has a qualified
interactive latency. Targets, cases, source fields and the original failures
are not changed in response to results.

## Failure continuation and portable evidence

The [portable archive](../../studies/fixtures/finite-photo-intensity-v2/README.md)
contains complete source-bound receipts and its checksum manifest. The final
no-fit preflight passes **30 actual observation checks** and **18 parser,
routing and serialization contracts**, with zero inverse optimizers. It keeps
synthetic sentinels distinct from numerical recovery.

A separate actual run injects only the first fit-entry exception and executes
**nine later real optimizers**. It retains all twelve rows, including both
upstream refusals. All eleven later parsed rows match canonical exactly after
removing only `runtime_seconds` fields. Its **ten continuation assertions pass**;
the contract harness exits 0 while the embedded scientific study retains exit 1.
The first failed row has no fitted/held-out/truth payload and both pass flags
are false. Source/input hashes and the complete stdout/report bytes agree.
This required failure run takes **128.951 seconds**; it is not a second canonical
experiment or a retry of missed targets.

Independent read-only audits recompute completion, targets, truth containment,
paired observations, original version 1 hashes and later-row equality from the
saved reports. All ten promoted runner/receipt/progress/audit files are
byte-identical to their recorded local counterparts. Original version 1 and
earlier development preflight receipts remain preserved in their own scope.

## Software regression

The full local Python suite passes **899 tests**, with zero failures, errors or
skips and runtime warnings treated as errors. The JUnit interval is **195.798
seconds**; the wrapper records **196.624 seconds**. All **282 frozen software
inputs** and **22 built frontend files** remain unchanged during that interval.
Study plans, runners and results retain their separate source/input closures.
The production frontend build and complete `make lint` pass. The 37 focused
observation contracts are included in the full total. No automatic trace/UI
behavior changed, and no new browser result is claimed.

Final navigation checks pass **73 Markdown files**, **767 local references**,
including **68 fragments**, and **102 tables**, with no fence, table or local
navigation errors. All **329 pre-existing non-Markdown files** remain
byte-identical to the PR #89 base. Both promoted contract runners' read-only
help and all new Python source lint/format checks pass. Complete whitespace
checks pass. The local software logs and source receipts remain under
`.local/verification/`.

| Source or receipt | SHA-256 |
| --- | --- |
| `backend/finite_observations.py` | `09fa843f72b2fc265ba8d4a7111267bf10433eb4f3f2a0600a89cc7871cb3969` |
| `tests/test_finite_observations.py` | `fd0a2196b1a93e37128334088e5faa6989c0d2ad53d49cd5945db7b34d7680ca` |
| `studies/verification/finite-photo-intensity-v2.py` | `74c76c9961bb7e8488c99af2c4db0227022a5bde06d26f306962e5d265d694c5` |
| Full Python JUnit | `606e10069bb45435804552283fe021684ae222479fc11a0267e6b02f73929434` |
| Software interval binding | `66dd1a09b4985044cecba0764cd9cd76f49e98aca72a4448c38f92783beee588` |
| Complete version 2 replay | `967251c4458e7c06f88c6f5d4b01ab77654a0a744e1a181dd79c86df99d39127` |
| Final no-fit preflight receipt | `aca026591801562fa0730dc24d07210d9f2e4c3c9060afbf37c9334597ffc99b` |
| Actual first-fit failure result | `8bb6d605f2b03ceee83a54a32f02c0030d34aa809380c470ad179d1640295d18` |
| Actual continuation audit | `0a3f48d802b437aca42883e8f0be7b5811aea318e35ec3329cd425dbe0bc774c` |
| Portable evidence manifest | `c32b2ad520145c73c35f8b02108c1e1651315ecd1df368c1552477532bc744b9` |

Neither covariance lane is a calibrated camera PSF. A successful numerical
preparation does not establish constant illumination, supported thickness,
Gaussian acquisition, global uniqueness, final native CAD geometry, interactive
latency, real-camera accuracy or print fit. Those remain separate requirements
before automatic user adoption.
