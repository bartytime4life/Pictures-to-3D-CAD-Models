# Covariance-aware corner fitting: independent evidence

This change uses the full empirical rectified Gaussian covariance for nonparallel
fillets instead of its geometric-mean scalar. It builds on the main-based rank
repair [PR #78](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/78),
source `185d682197437581083a8ecd46de6357d7adb846`. The final review is stacked on
the documentation-only [PR #81](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/81),
head `60732a71b52b8d48241d6f2aa7780d5a7f790107`; its executable files are identical
to that rank-repair source before this change. The primary checkout remains at
`d747e30697a99a8f90d747d23d6ab7c1fa8b95ed`.

Read the [model guide](../anisotropic-corners.md) for the coordinate frame,
whitening construction, finite numerical budgets and unresolved-result policy.
These results concern supplied mathematical Gaussian inputs, not a physical
camera calibration or manufacturing tolerance.

## Independent reproduction before the repair

The independent oracle describes a canonical infinite corner by `x <= g(y)`.
For half sweep `h`, `g(y) = sqrt(r²-y²)` when `abs(y) <= r*sin(h)`, and
`g(y) = (r-abs(y)*sin(h))/cos(h)` elsewhere. It integrates a conditional X-normal
CDF over standardized Y, using standard-library `erfc` and positive
Gauss–Legendre area weights. This differs from production's star-centred angular
radial integral. GL16/GL32 agreement is a numerical check, not a certified
quadrature enclosure; the uncomputed Y tails are bounded separately by
`erfc(12/sqrt(2))`, about `3.553e-33`.

The [16-case plan](../../studies/corner-anisotropy-v1.json) was frozen before
fitting. The original scalar implementation was retained separately by source
hash. With true `r = 4 px`, `S = diag(0.36, 4) px²`, exact tangent lines and the
production scalar `sigma = det(S)**0.25`, it returned `4.54123948098 px`.
The centre error was `0.76542821 px`, residual RMS `0.03743480 px` and inherited
radius spread `0.10453797 px`. A small conditional spread did not account for
that model mismatch. This reproduces the constrained fitting stage; it does not
claim a full-photograph or measured-phone failure.

The initial fixed-160-panel covariance prototype also missed a small-radius forward control by
`1.9853e-6` intensity probability units before the bounded quadrature comparison
was added. Its failed development probe remains in a separately labelled local
receipt rather than being promoted into the canonical result.

## Complete fixed experiment

The [runner](../../studies/verification/corner-anisotropy-v1.py) and
[canonical result](../../studies/results/corner-anisotropy-v1.json) retain all
**16 cases and 48 checks**, with zero failed checks or execution failures.
Runtime was **19.0511 seconds**. Before/after imported source hashes match;
stdout and the saved strict JSON are byte-identical. Every scalar fit field and
independently generated point array exactly matches the pinned baseline.

Among the **12 predeclared radius-recovery controls**, maximum covariance-model
radius error is `1.03053e-7 px`. The R4 counterexample becomes
`4.000000024571 px`. Across all cases, GL16/32 oracle disagreement is at most
`1.4433e-15`, independent half-level residual at most `2.3204e-14`, and covariance
forward-model discrepancy at true geometry at most `1.7123e-8` probability units.
These are observed finite matched-model results, not error bounds for other
inputs or physical accuracy specifications. The fits use supplied exact tangent
lines, covariance and a true-radius seed for nonzero controls.

Four adverse cases remain separate from those 12 controls:

| Case | Retained covariance outcome | Interpretation |
| --- | --- | --- |
| True sharp corner, radius 0 | No resolved fit (`None`) | Numerical non-resolution; no fabricated positive fillet or finite bound |
| Radius 0.6 px | Candidate about 0.600000605 px; conditional sharpness estimate about 1.18178 px | The assumed positional floor cannot distinguish this fillet from sharp; not a physical upper bound |
| Radius 1.5 px | Candidate about 1.500000037 px, without a sharpness estimate | Retained transition case under supplied model |
| Radius 4 px, 30-degree sweep | Candidate about 4.000000981 px; conditional sharpness estimate about 7.05967 px | Weak radius evidence despite matched numerical recovery |

The finite outcomes do not establish global optimization, geometric uniqueness,
Gaussian adequacy or calibrated confidence coverage. General free curves and
slot-cap approximations retain their separate limits.

## Integration, refusal and regression

All **54 new tests pass**. They include independent controls for separable sharp
CDFs, correlated sharp-vertex orthant probabilities, isotropic equivalence,
rotation/reflection/scale changes, positive-area rounded corners, covariance
refusals and explicit work exhaustion. Higher-order positive-area comparisons
also cover principal standard-deviation ratios 10 and 20; an unresolved ratio
400 control is refused rather than accepted from incomplete quadrature.

The source-frame tests exercise actual thickness homotheties and a complete
finite rounded-plate fitting chain with a rotated covariance, then line/arc
assembly. A uniform top-face scale of 0.8 carries covariance by 0.8² and recovers
the declared 6.4 px radius within the preset 0.015 px tolerance. Mixed support
scales pass through the real fit refusal and per-ring traced-outline recovery;
unaffected analytic rings remain available. The final recovery-focused run also
passes all **16 reference integration tests** and the original five-photo
directional-blur regression (**17 tests**, 31.56 seconds). These are digital geometry checks,
not native CAD/slicer or physical-camera acceptance.

### Retained integration failure and bounded recovery

The first whole-workbench run terminated with **680 passes and one failure**,
not an incomplete or running test. The existing heavily blurred, thick, tilted
synthetic photograph returned HTTP 422. Its corrected measured outer boundary
already crossed itself; the unresolved-corner policy exposed that invalid
source ring rather than accepting the former analytic reconstruction. The
profile validator correctly refused it.

The failed candidate's reference integration SHA-256 was
`9639d6faa6c1c3084f3e1ca53188b65d115524609631530f0687ac0fc217dfc1`.
Its terminal JUnit SHA-256 is
`00850bd94109960a4ce15da28f8b71a7f65ddf13d400de1caffdf43a445c436a`.
Those source and failure receipts remain separate from the revised candidate.
An attempted polygon cleanup was rejected: it produced multiple components and
the largest component deviated about `0.5092 px`, beyond the existing
`0.2692 px` polyline-detail allowance. Components were not silently discarded.

For that invalid unresolved ring, the revised recovery freezes the already
eligible initial geometric fit before snapping or deblurring, samples it into
straight segments and checks the complete closed boundaries in both directions
against the existing geometric-fitting tolerance. This case's tolerance is
`0.4240 px`, distinct from the polyline-detail allowance; the observed boundary
distance is about `0.4116 px`. It does not enlarge either threshold or infer a
radius. No generic topology-repair operator or component deletion is used. An
invalid source has no accepted polygon topology, and proximity does not verify
the intended topology. A candidate that is invalid, exceeds the point budget or
falls outside either boundary tube is refused. The complete profile still passes
through the existing validator, including interactions with its holes.

The separate diagnostic feature scorer requires analytic outer arcs and cannot
score this line-only recovery. Its unavailable result is retained; a successful
trace is not claimed as feature-accuracy evidence. User-facing notes identify
the polygonal approximation and unresolved corner radius.

### Final source-bound verification

The revised whole-workbench run terminated successfully on November 12, 2026,
at **19:58:19 UTC**: **687 Python tests passed** in 176.82 seconds, with runtime
warnings treated as errors and zero failures, errors or skips. This includes all
54 new tests and the original thick directional-blur regression. The earlier
680-pass/one-failure result above remains a separate failed development state.

Both existing sheet-reference browser scenarios passed against this candidate's
actual local backend and built interface: sheet-scaled tracing with CAD/drawing
exports, and changing an existing photo to a sheet reference with error
recovery. The two-scenario run took 17.389 seconds, with zero failed, skipped or
flaky scenarios. It used a separate loopback port and temporary model directory;
the service was stopped afterwards. This is a focused browser run, not a rerun
of the complete historical 74-scenario suite or a native slicer check.

The frontend build, Ruff, frontend/browser-source formatting and whitespace
checks pass. The complete documentation audit covers **61 Markdown files, 591
local references, 48 heading targets, 87 tables and one local HTML link**, with
zero errors. **14 read-only command checks**, all **11 HTTP API operations**
compared across source, OpenAPI and documentation, and **19 companion-library
documentation tests** also pass. Help/schema checks do not execute the commands'
workloads or establish operational acceptance.

All **273 non-Markdown source/configuration/test/plan/runner files** and **22
built interface files** remained unchanged through the final Python and browser
runs. Saved study results are reported separately from that source freeze. Broader product qualification,
installed-machine state, physical capture and print acceptance remain distinct.

The replay/failure audit passes **14 contracts**. It verifies refusal before
analysis for invalid/existing destinations, strict JSON/stdout identity, and an
actual first-fit failure: the error remains in the report while the other
**31 actual fits** execute and match canonical results. It does not count a
fake analyzer as recovery or fit-accuracy evidence.

| Artifact | SHA-256 |
| --- | --- |
| Frozen plan | `339e3917c477294fbe634f21ca4d90f09e0f88140b92527ec56e2bc72f225ba5` |
| Independent runner | `a645fab11537d0f0f61f8caef5a3245f798eeac3fb209158c5788526f4cae2b3` |
| Canonical result | `4c4c8e8df23587def5787ff840b04764f9a6df245762e2ea02ae074f2a9aeb32` |
| Fitting implementation | `a9f10e2ccccb2d1ddb4b91e07331f7ed964c1cf5c79f0187062d50ec145697c0` |
| Revised reference integration | `20bdaa4035f4796c6309495fc26a819c558d1dd95cf477781aad3fa348a9100a` |
| Complete replay/failure receipt (local) | `9e51ecb71bb2f5a253e327300d17cd4197118882c16123033505e38520865a2c` |
| Final source/built freeze (local) | `c5cee34a5674b203e76a0bb4aaee0365a44e67768d9000181eb9d0f0ff655b72` |
| Final 687-test JUnit (local) | `c73313a546bc8b4984de5a0d54cd136c9cd24d2e23d445b7ac9e8b071c1ee765` |
| Focused browser JSON (local) | `01550e25b3659b46bfd91e6f77fe11796c1c01f84cf082ec69c9e6123a5c355b` |

Local development, baseline and terminal receipts remain under ignored
`.local/verification/`. They preserve source hashes and earlier observations;
they are not downloadable repository artifacts. To rerun the fixed experiment,
choose a fresh JSON destination in an existing directory:

```bash
mkdir -p .local
.venv/bin/python studies/verification/corner-anisotropy-v1.py --model both --output .local/corner-anisotropy-new.json
```

The command needs the prepared workbench environment and no server, photograph,
model download, native application or physical hardware. Keep the full report,
including the adverse outcomes and all supplied inputs.
