# Project status and evidence

Documentation snapshot: **November 12, 2026**. This page describes the reviewed
source at `a3a2397cde2b1afbeda133ac86218eaae5a22edc` and the documentation
follow-up based on it. Start with [setup](development.md), the [task index](README.md)
or the [API examples](api-examples.md).

The next [conditional radius-analysis candidate](validation/corner-feasibility.md)
is based on documentation head `77b7f6f`. It adds a developer tool; the source
and review table below retains the earlier integrated baseline and open reviews.

## Source and review state

At the repository check on November 12, `main` was
`5c07d0f70d7df0200bc24227c8ac7e9b630f7f09`. The latest two algorithm changes
were still open for review. This documentation branch includes both changes;
an older checkout of `main` does not contain them.

| Source | Included changes | Review state at this snapshot |
| --- | --- | --- |
| `main` at `5c07d0f` | Initial-fit support, benchmark correspondence/coverage, weak-edge recovery and fillet-sector preservation | Integrated through PRs #43–#46 |
| `ba94ef8e55bbc39b8074840052244f92c72be661` | Central radial-inverse branch safeguards and an independently implemented synthetic lens inverse | [PR #47](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/47), open; base `main` |
| `a3a2397cde2b1afbeda133ac86218eaae5a22edc` | Verified corner-resolution crossing and conditional radius messages | [PR #48](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/48), open draft; base PR #47's branch |

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
now implements conditional radius sets from supplied bounds. General inference
with uncertain geometry, pose, blur and model discrepancy remains research;
there is no product endpoint, automatic tracing correction or accuracy label.

## Evidence by scope

| Evidence | Recorded result | Interpretation |
| --- | --- | --- |
| Conditional corner-analysis candidate | [Numerical/CLI record](validation/corner-feasibility.md): 760 Python tests passed | New developer-only analysis; no fresh browser/build or physical qualification |
| Latest complete local workbench run | [Corner-resolution record](validation/sharp-corner-resolution.md): 630 Python tests and 74 browser scenarios; build and lint passed | Reviewed implementation behavior on the recorded inputs; not a new run by this documentation change |
| Earlier radial candidate | [Radial record](validation/radial-inverse.md): 623 Python tests and 74 browser scenarios after integration with `5c07d0f` | Separate source binding; higher-order lens mismatch remains visible |
| Model-mismatch research | [Directional study](validation/directional-spread-qualification.md) and [corner counterexample](validation/sharp-corner-resolution.md) retain misses, unknowns and negative outcomes | No production anisotropic correction or physical radius enclosure |
| Companion library | [Revision 7 verification](../reference-library/VERIFICATION.md) | Its own dated release record, not a new library release |
| This documentation follow-up | [Coverage and checks](validation/documentation-current-state.md) | Documentation parsing, links, commands and API example; separate from full product regression suites |

Hosted CI was checked at **07:50 UTC on November 12**:
[workbench run 110](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43173672079)
for `ba94ef8` was cancelled;
[run 111](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43176958836)
for `a3a2397` was in progress. Neither was a successful hosted validation at that
observation. Follow those exact run links for later results; local passes remain
separate. The documentation branch has its own checks when published.

Follow-up at **08:17 UTC on November 12**: run 111 completed successfully.
For documentation head `77b7f6f`,
[library run 39](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43179485496)
completed successfully and
[workbench run 112](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43179485257)
was still in progress. These are separate from the conditional-analysis
candidate's new local Python checks.

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
