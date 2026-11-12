# Project status and evidence

Candidate snapshot: **November 12, 2026**. This fixed-observation branch is based on
`6d2672710e54e9117048613dec6ef3ea448062b7`, the published head of
[draft PR #59](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/59).
It adds [known sampling/filter composition and conditional covariance](profile-observations.md)
as developer tools. The [new controls](validation/profile-observations.md)
retain false precision, global aliases and earlier-processing limits.
Production behavior remains at PR #59, whose [wall-fit record](validation/wall-localization.md)
preserves the failed development window and final checks. Start with [setup](development.md), the
[task index](README.md), [developer tools](developer-tools.md) or [API examples](api-examples.md).

## Source and review state

At this check, `main` was `5c07d0f70d7df0200bc24227c8ac7e9b630f7f09`.
PRs #47–#59 were open and unmerged. This candidate branch includes their
changes; that checkout of `main` does not contain them. The conditional corner
analysis remains separate from production tracing; the grid and crossing repairs
affect the existing production edge-profile search.

| Source | Included changes | Review state at this snapshot |
| --- | --- | --- |
| `main` at `5c07d0f` | Initial-fit support, benchmark correspondence/coverage, weak-edge recovery and fillet-sector preservation | Integrated through PRs #43–#46 |
| `ba94ef8e55bbc39b8074840052244f92c72be661` | Central radial-inverse branch safeguards and an independently implemented synthetic lens inverse | [PR #47](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/47), open; base `main` |
| `a3a2397cde2b1afbeda133ac86218eaae5a22edc` | Verified corner-resolution crossing and conditional radius messages | [PR #48](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/48), open draft; base PR #47's branch |
| `77b7f6f74ea411e336ff3cf613b33e406ee98d72` | Current-state guides, API example, mathematical wording and library maintenance instructions | [PR #49](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/49), open draft; base PR #48's branch |
| `be2a58cedb7a69702a57c9953a0e0d1e965feae8` | Version-1 conditional corner-radius analysis with fixed blur and provenance-bound CLI reports | [PR #50](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/50), open draft; base PR #49's branch |
| `b366b3f2cda4ca33a34b2b2aa109a9b1718acb0c` | Version-2 joint radius/blur domains, common-blur consistency and conservative radius projections | [PR #51](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/51), open draft; base PR #50's branch |
| `b800edbcf0a20ac2d30b82a9a135cfc46aa76a55` | Documentation consolidation, complete review chain and source-bound validation navigation | [PR #52](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/52), open draft; base PR #51's branch |
| `e22ff3d6608896c945bd3bc6ad338ff6a780e889` | Version-3 known normalized uniform pixel-aperture means | [PR #53](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/53), open draft; base PR #52's branch |
| `620d5c717e21fd7d7a797b114972fd2b09e9ece9` | Version-4 known fixed signed sampling stencils with whole-radius bounds and exact gain accounting | [PR #54](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/54), open draft; base PR #53's branch |
| `a5f99e5a4180ec2437c08215faa12058b6b490a9` | Symmetric production profile sampling and an independent material-gradient study | [PR #55](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/55), open draft; base PR #54's branch |
| `37eb4d2086c61dda983fe4e39391d9693dc82331` | Actual-distance crossing ranking and explicit unresolved contacts | [PR #56](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/56), open draft; base PR #55's branch |
| `7dfe0fe698c8831e9c02ae960f03bcdc533701dc` | Bounded five-node wall/lighting study, complete CSVs and constructive local ambiguity | [PR #57](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/57), open draft; base PR #56's branch |
| `0f5f888708b623245854b53458431af495b387fe` | Complete documentation review, numerical-tool catalog and corrected mathematical limits | [PR #58](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/58), open draft; base PR #57's branch |
| `6d2672710e54e9117048613dec6ef3ea448062b7` | Expanded consistent wall geometry, local observations, explicit numerical withholding and complete positive/negative development evidence | [PR #59](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/59), open draft; base PR #58's branch |

The PR links show live review state. A documentation update does not install,
merge or deploy those changes. Record the checkout used to start a service:

```bash
git rev-parse HEAD
git status --short --branch
```

The health endpoint's `version: "0.1.0"` is shared by multiple revisions and
cannot identify which implementation a server is running.

The wall-localization and fixed-observation candidates remain separate from integrated `main` and the
primary `codex/slicer-integration` checkout at
`d747e30697a99a8f90d747d23d6ab7c1fa8b95ed`. Its broader search and conditional
numerical checks do not establish physical edge identity. The matched final-Keys
prototype and conditional covariance module are developer research and are not applied to tracing. New review
branches do not change an already running or installed application.

## Implemented capabilities and remaining limits

| Capability | Engineering basis | Remaining limit or required check |
| --- | --- | --- |
| Flat-part reconstruction | Reviewed 2D outer boundary and through-holes, uniform scale and entered thickness | No hidden geometry, varying thickness or original feature-history recovery |
| Reference-sheet correction | One radial coefficient, plane homography, subpixel edges and conditional wall/parallax correction | Assumed optics, tone response and wall geometry; no measured-phone accuracy result |
| Fitted circles, lines and arcs | Residual gates and complete initial-boundary support check | Later blur reconstruction and snapping can still disagree with observations |
| Corner-radius resolution | Checked numerical crossing under a scalar Gaussian model | A model-resolution estimate is not a physical upper-radius bound |
| Bed placement and split suggestions | Continuous-angle polygon placement or conservative curve enclosure; bounded straight-cut grid search | Individual geometric containment; native slicing, joints and physical fit need separate checks |
| Optional AI assistance | Text-only local inference, bounded proposals, explicit Apply and Undo | Fixture tests establish integration; no live-model quality winner is recorded |
| Export and project recovery | CAD/mesh/drawing exports, editable browser recipe and temporary server artifacts | Save photos separately; browser-only measurement notes require the browser's project save |
| Offline reference library | Revision 7 handbook, calculators, photo workspace and parametric examples | Separate storage, build and verification record; wider methods are not workbench features |

See [engineering equations and decisions](engineering-model.md),
[method assumptions](reference-sheet.md), [export contents](exports.md) and the
[roadmap](roadmap.md) for details. A [fixed-corner developer CLI](corner-feasibility.md)
now implements conditional radius sets with fixed or bounded independent
axis-aligned blur, using point observations, known uniform pixel-aperture means
or declared fixed signed combinations with whole-radius bounds.
General inference with uncertain geometry, pose, correlated
or spatially varying PSFs and model discrepancy remains research;
there is no product endpoint, automatic tracing correction or accuracy label.

## Evidence by scope

| Evidence | Recorded result | Interpretation |
| --- | --- | --- |
| Fixed-observation developer candidate | [Covariance and composition checks](validation/profile-observations.md): 1,225 Python tests passed, including 47 new cases; seven density/repeat configurations and 12 postblur cases | Supplied-noise local sensitivity and known operators; no production or physical confidence status |
| Local wall-localization candidate | [Complete comparison and regressions](validation/wall-localization.md): 1,178 Python tests and 74 browser scenarios passed; build and lint passed; 192 paired observation scenes and 24 separate matched-operator controls | Retains failed development camera checks and unresolved/model-mismatch cases; no physical calibration or universal improvement claim |
| Nearest-crossing candidate | [Rule and preservation checks](validation/edge-crossings.md): 1,111 Python tests passed, independent 3,888-case contact oracle | Actual-distance selection and explicit unresolved contacts; no physical edge or camera qualification |
| Joint wall/lighting candidate | [Bounded source and full CSV checks](validation/wall-gradients.md): 1,131 Python tests passed; 840 direct and 576 image fits | Developer study; no automatic correction or physical uncertainty/accuracy status |
| Material-gradient/sampling candidate | [Crossed study](validation/material-gradients.md): 1,075 Python tests passed; 9,216 rows in each before/after census | Production sampling symmetry repaired; material gradients, wall ambiguity and physical calibration remain open |
| Signed-stencil candidate | [Whole-radius record](validation/signed-stencils.md): 1,022 Python tests passed | Known fixed signed observations, exact gain/work accounting and retained unknowns; no production-pipeline or physical calibration |
| Pixel-aperture candidate | [Finite-area record](validation/pixel-apertures.md): 929 Python tests passed | Known normalized product-aperture means; center-sampling counterexamples and retained unknowns; no production-image or physical qualification |
| Joint blur-domain candidate | [Shared-blur record](validation/corner-blur-domains.md): 839 Python tests passed | Joint nuisance domains and safe projection; no new browser or physical qualification |
| Conditional corner-analysis candidate | [Numerical/CLI record](validation/corner-feasibility.md): 760 Python tests passed | New developer-only analysis; no fresh browser/build or physical qualification |
| Earlier local browser/build record | [Corner-resolution record](validation/sharp-corner-resolution.md): 630 Python tests and 74 browser scenarios; build and lint passed | That source and recorded inputs; the wall-localization row records the fresh run separately |
| Earlier radial candidate | [Radial record](validation/radial-inverse.md): 623 Python tests and 74 browser scenarios after integration with `5c07d0f` | Separate source binding; higher-order lens mismatch remains visible |
| Model-mismatch research | [Directional study](validation/directional-spread-qualification.md) and [corner counterexample](validation/sharp-corner-resolution.md) retain misses, unknowns and negative outcomes | No production anisotropic correction or physical radius enclosure |
| Companion library | [Revision 7 verification](../reference-library/VERIFICATION.md) | Its own dated release record, not a new library release |
| Earlier documentation follow-up | [PR #49 coverage and checks](validation/documentation-current-state.md) | Documentation parsing, links, commands and API example at its recorded source |
| PR #52 documentation consolidation | [Coverage and checks](validation/documentation-math-state.md) | Navigation, review chain, source/receipt consistency and complete Markdown checks at its recorded source; no new product regression or physical result |
| Documentation update through PR #57 | [Complete coverage and checks](validation/documentation-complete-2026-11-12.md) | Current guides, numerical-tool contracts and repository-wide Markdown checks; no new product or physical qualification |

Hosted results are bound to exact heads. Earlier rows retain their last recorded
results; `37eb4d2`, `7dfe0fe`, `0f5f888` and `6d26727` were checked again during this
documentation update on **November 12**:

| Head | Hosted workflow | Result at this observation |
| --- | --- | --- |
| `ba94ef8` | [Workbench run 110](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43173672079) | Cancelled |
| `a3a2397` | [Workbench run 111](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43176958836) | Completed successfully |
| `77b7f6f` | [Workbench run 112](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43179485257), [library run 39](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43179485496) | Both completed successfully |
| `be2a58c` | [Workbench run 113](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43181910268) | Completed successfully |
| `b366b3f` | [Workbench run 114](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43184279416) | Cancelled at the subsequent check |
| `b800edb` | [Workbench run 115](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43185322816) | Completed successfully |
| `e22ff3d` | [Workbench run 116](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43188961747) | Cancelled at the subsequent check |
| `620d5c7` | [Workbench run 117](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43192825464) | Completed successfully |
| `a5f99e5` | [Workbench run 118](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43196410807), [library run 40](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43196410880) | Both completed successfully |
| `37eb4d2` | [Workbench run 119](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43200015707) | Completed successfully |
| `7dfe0fe` | [Workbench run 120](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43203756110) | Cancelled at the final documentation observation |
| `7dfe0fe` | [Library run 41](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43203755932) | Completed successfully |
| `0f5f888` | [Workbench run 121](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43209391346) | Completed successfully |
| `0f5f888` | [Library run 42](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43209391383) | Completed successfully |
| `6d26727` | [Workbench run 122](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43214844810) | In progress at this observation |
| `6d26727` | [Library run 43](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43214844876) | Completed successfully |

Follow the exact run links for later results. The candidate's local 1,225-test result is
separate from hosted CI. Earlier observations remain in their dated validation
records; successful CI does not merge, install or qualify a physical part.

## Next engineering work

Prioritize absolute forward-model adequacy, then independently specified
model-mismatch evaluations and reserved real captures with measured dimensions.
The [material-gradient record](validation/material-gradients.md) makes the
paper-only slope limitation and competing wall explanation explicit; the sampling
symmetry fix does not resolve either model assumption.
The nearest-contact rule now keeps ties, plateaus and unconfirmed local contacts
unresolved. Correct feature identity from imperfect seeds and realistic image
error bounds remain separate engineering work.
The [joint wall/lighting record](validation/wall-gradients.md) now makes exact
local ambiguity and bounded finite-error alternatives explicit. Full-pipeline
initialization, common-tone assumptions and distinguishing capture/measurement
evidence remain priorities before promoting that solver to production.
The [localization record](validation/wall-localization.md) additionally isolates
an inappropriate observation-window extension and demonstrates why matching the
final signed sampler matters. Earlier image-processing operators, effective blur,
lighting and joint camera/shape evidence remain open work.
The [fixed-observation follow-up](validation/profile-observations.md) now models
declared finite smoothing and shared-pixel covariance. Earlier spatially varying
rectification, realistic noise/model discrepancy, correlated neighboring profiles
and globally ambiguous wall interpretations remain open.
Keep observation-error bounds separate from model discrepancy, local fit spread
and endpoint-placement sensitivity. Numerical or work-budget exhaustion must
remain unresolved rather than becoming a physical claim.

Native slicer acceptance, installed versions, actual printer/material profiles,
layer previews and physical coupons remain separate qualification tasks. No
real-photo accuracy study, physical-fit acceptance or live-AI quality comparison
is recorded by this documentation refresh.
