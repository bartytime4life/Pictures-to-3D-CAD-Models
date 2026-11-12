# Project status and evidence

Documentation snapshot: **November 12, 2026, 08:39 UTC**. This page describes
source at `b366b3f2cda4ca33a34b2b2aa109a9b1718acb0c` and the documentation
follow-up based on it. It includes the pending review chain below, through the
shared-blur analysis in PR #51. Start with [setup](development.md), the
[task index](README.md) or the [API examples](api-examples.md).

## Source and review state

At this check, `main` was `5c07d0f70d7df0200bc24227c8ac7e9b630f7f09`.
PRs #47–#51 were open and unmerged. This documentation branch includes their
changes; that checkout of `main` does not contain them. The developer analysis
is separate from the workbench's production tracing and interface.

| Source | Included changes | Review state at this snapshot |
| --- | --- | --- |
| `main` at `5c07d0f` | Initial-fit support, benchmark correspondence/coverage, weak-edge recovery and fillet-sector preservation | Integrated through PRs #43–#46 |
| `ba94ef8e55bbc39b8074840052244f92c72be661` | Central radial-inverse branch safeguards and an independently implemented synthetic lens inverse | [PR #47](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/47), open; base `main` |
| `a3a2397cde2b1afbeda133ac86218eaae5a22edc` | Verified corner-resolution crossing and conditional radius messages | [PR #48](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/48), open draft; base PR #47's branch |
| `77b7f6f74ea411e336ff3cf613b33e406ee98d72` | Current-state guides, API example, mathematical wording and library maintenance instructions | [PR #49](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/49), open draft; base PR #48's branch |
| `be2a58cedb7a69702a57c9953a0e0d1e965feae8` | Version-1 conditional corner-radius analysis with fixed blur and provenance-bound CLI reports | [PR #50](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/50), open draft; base PR #49's branch |
| `b366b3f2cda4ca33a34b2b2aa109a9b1718acb0c` | Version-2 joint radius/blur domains, common-blur consistency and conservative radius projections | [PR #51](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/51), open draft; base PR #50's branch |

The PR links show live review state. A documentation update does not install,
merge or deploy those changes. Record the checkout used to start a service:

```bash
git rev-parse HEAD
git status --short --branch
```

The health endpoint's `version: "0.1.0"` is shared by multiple revisions and
cannot identify which implementation a server is running.

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
axis-aligned blur. General inference with uncertain geometry, pose, correlated
or spatially varying PSFs and model discrepancy remains research;
there is no product endpoint, automatic tracing correction or accuracy label.

## Evidence by scope

| Evidence | Recorded result | Interpretation |
| --- | --- | --- |
| Joint blur-domain candidate | [Shared-blur record](validation/corner-blur-domains.md): 839 Python tests passed | Joint nuisance domains and safe projection; no new browser or physical qualification |
| Conditional corner-analysis candidate | [Numerical/CLI record](validation/corner-feasibility.md): 760 Python tests passed | New developer-only analysis; no fresh browser/build or physical qualification |
| Latest recorded browser/build run | [Corner-resolution record](validation/sharp-corner-resolution.md): 630 Python tests and 74 browser scenarios; build and lint passed | That source and recorded inputs; later developer-tool Python results do not refresh browser/build evidence |
| Earlier radial candidate | [Radial record](validation/radial-inverse.md): 623 Python tests and 74 browser scenarios after integration with `5c07d0f` | Separate source binding; higher-order lens mismatch remains visible |
| Model-mismatch research | [Directional study](validation/directional-spread-qualification.md) and [corner counterexample](validation/sharp-corner-resolution.md) retain misses, unknowns and negative outcomes | No production anisotropic correction or physical radius enclosure |
| Companion library | [Revision 7 verification](../reference-library/VERIFICATION.md) | Its own dated release record, not a new library release |
| Earlier documentation follow-up | [PR #49 coverage and checks](validation/documentation-current-state.md) | Documentation parsing, links, commands and API example at its recorded source |
| Current documentation consolidation | [Coverage and checks](validation/documentation-math-state.md) | Current navigation, review chain, source/receipt consistency and complete Markdown checks; no new product regression or physical result |

Hosted CI status is bound to each exact head. At **08:39 UTC on November 12**:

| Head | Hosted workflow | Result at this observation |
| --- | --- | --- |
| `ba94ef8` | [Workbench run 110](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43173672079) | Cancelled |
| `a3a2397` | [Workbench run 111](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43176958836) | Completed successfully |
| `77b7f6f` | [Workbench run 112](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43179485257), [library run 39](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43179485496) | Both completed successfully |
| `be2a58c` | [Workbench run 113](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43181910268) | In progress; no conclusion |
| `b366b3f` | [Workbench run 114](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43184279416) | In progress; no conclusion |

Follow the exact run links for later results. The local 839-test result is
separate from hosted CI. Earlier observations remain in their dated validation
records; successful CI does not merge, install or qualify a physical part.

## Next engineering work

Prioritize absolute forward-model adequacy, then independently specified
model-mismatch evaluations and reserved real captures with measured dimensions.
Keep observation-error bounds separate from model discrepancy, local fit spread
and endpoint-placement sensitivity. Numerical or work-budget exhaustion must
remain unresolved rather than becoming a physical claim.

Native slicer acceptance, installed versions, actual printer/material profiles,
layer previews and physical coupons remain separate qualification tasks. No
real-photo accuracy study, physical-fit acceptance or live-AI quality comparison
is recorded by this documentation refresh.
