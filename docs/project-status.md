# Project status and evidence

Documentation snapshot: **November 12, 2026**. The current developer candidate
adds [whole finite-shape source prediction and conditional radius/chord fitting](finite-shape-source.md).
Its [evidence record](validation/finite-shape-source.md) keeps supplied pose,
optics, numerical recovery and model mismatch distinct. It adds no production
trace endpoint or automatic CAD correction. Published
[PR #72](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/72) repairs
circle-consistent line/arc joins in production tracing, retaining an affected
source outline with an explicit notice when analytic construction is unavailable.
The [geometry and recovery record](validation/canonical-arcs.md) distinguishes
this digital repair from physical-camera accuracy. Interface controls, scale
inputs and API/file schemas remain unchanged. Start with [setup](development.md),
the [task index](README.md), [developer tools](developer-tools.md) or
[API examples](api-examples.md).

This candidate targets published PR #73 at
`fa853df69e6c279ab63404cf1c4b9d989bd13ed2`, tree
`023c6af1ecb39c9286784e7a3ad5ddfaa34ba5fc`.
PR #72 was merged into `codex/tapered-cap-geometry` at
`c3bd7bfd43c92904959a970825f61544c7c5a206`, preserving PR #72's published tree
`f99a1738ebf34268194bc75cb2c0a73a2b336054`.
PR #73 adds documentation on that merge. Its
[documentation audit](validation/documentation-pr72.md) retains its own checks
and historical review states.

## Source and review state

At the **18:07 UTC** readback, `main` remained
`485da7e01c6447177aae6e54e71ad2177544bdd6`, integrating PR #47.
The earlier **16:46 UTC** review found PRs **#47–#71 closed and merged into their listed base branches**.
PR #72 was merged into `codex/tapered-cap-geometry` at **17:34 UTC**. Those
individual merges do not propagate the whole stack into `main`: PRs #48–#72
were merged into successive review branches. The current candidate includes
those changes; the observed `main` does not. The conditional corner and response
analyses remain developer tools; production changes have their own records.

| Source | Included changes | Review state at this snapshot |
| --- | --- | --- |
| `main` at `485da7e` | Initial-fit support, correspondence/coverage, weak-edge recovery, fillet-sector preservation and radial-inverse safeguards | Integrated through PR #47 |
| `ba94ef8e55bbc39b8074840052244f92c72be661` | Central radial-inverse branch safeguards and an independently implemented synthetic lens inverse | [PR #47](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/47), merged into `main` |
| `a3a2397cde2b1afbeda133ac86218eaae5a22edc` | Verified corner-resolution crossing and conditional radius messages | [PR #48](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/48), merged into PR #47's branch |
| `77b7f6f74ea411e336ff3cf613b33e406ee98d72` | Current-state guides, API example, mathematical wording and library maintenance instructions | [PR #49](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/49), merged into PR #48's branch |
| `be2a58cedb7a69702a57c9953a0e0d1e965feae8` | Version-1 conditional corner-radius analysis with fixed blur and provenance-bound CLI reports | [PR #50](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/50), merged into PR #49's branch |
| `b366b3f2cda4ca33a34b2b2aa109a9b1718acb0c` | Version-2 joint radius/blur domains, common-blur consistency and conservative radius projections | [PR #51](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/51), merged into PR #50's branch |
| `b800edbcf0a20ac2d30b82a9a135cfc46aa76a55` | Documentation consolidation, complete review chain and source-bound validation navigation | [PR #52](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/52), merged into PR #51's branch |
| `e22ff3d6608896c945bd3bc6ad338ff6a780e889` | Version-3 known normalized uniform pixel-aperture means | [PR #53](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/53), merged into PR #52's branch |
| `620d5c717e21fd7d7a797b114972fd2b09e9ece9` | Version-4 known fixed signed sampling stencils with whole-radius bounds and exact gain accounting | [PR #54](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/54), merged into PR #53's branch |
| `a5f99e5a4180ec2437c08215faa12058b6b490a9` | Symmetric production profile sampling and an independent material-gradient study | [PR #55](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/55), merged into PR #54's branch |
| `37eb4d2086c61dda983fe4e39391d9693dc82331` | Actual-distance crossing ranking and explicit unresolved contacts | [PR #56](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/56), merged into PR #55's branch |
| `7dfe0fe698c8831e9c02ae960f03bcdc533701dc` | Bounded five-node wall/lighting study, complete CSVs and constructive local ambiguity | [PR #57](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/57), merged into PR #56's branch |
| `0f5f888708b623245854b53458431af495b387fe` | Complete documentation review, numerical-tool catalog and corrected mathematical limits | [PR #58](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/58), merged into PR #57's branch |
| `6d2672710e54e9117048613dec6ef3ea448062b7` | Expanded consistent wall geometry, local observations, explicit numerical withholding and complete positive/negative development evidence | [PR #59](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/59), merged into PR #58's branch |
| `778c3392c6dfe111d8f422959fbdbc09ad8ba75b` | Bounded fixed-observation and finite-filter operators, conditional correlated-noise accounting and false-precision controls | [PR #60](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/60), merged into PR #59's branch |
| `8523862145ef264d265d84b9443b779ea09db072` | Known raw-photo warp, smoothing and profile composition; digital rounding and independent optical-source controls | [PR #61](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/61), merged into PR #60's branch |
| `ca321442bd276c177c31f00bcd62fb0ea27b2e0e` | Hosted workbench job budget from 30 to 45 minutes; source, test set and individual limits retained | [PR #62](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/62), merged into PR #61's branch |
| `ad7cc00fed4b2e7006aae957758a12b2f9f15528` | Complete documentation alignment, current source/CI snapshot, engineering wording and source-preserving verification | [PR #63](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/63), merged into PR #62's branch |
| `701aa91af7a0b1c62e5527eed35e0227bdf0e9f3` | Raw-source edge fitting in fixed retained modes, bounded brightness, numerical ambiguity and standardized raw/complement diagnostics | [PR #64](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/64), merged into PR #63's branch |
| `8b9c6a803b89d05daee38b7f48c079f70c76de3a` | Documentation review, setup/navigation and raw-source API/diagnostic guidance; complete 86-document audit | [PR #65](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/65), merged into PR #64's branch |
| `81dd0871aab390b1613bedc0d2b7c7f0578cf280` | Exact common-response consistency, strict CLI, finite edge/calibration controls and independent certificate audits | [PR #66](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/66), merged into PR #65's branch |
| `b27e48e09079b497d85dea766233db266e13cc90` | Complete documentation review, executable calibration examples, recovery and report-handling guidance | [PR #67](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/67), merged into PR #66's branch |
| `0b359ecb38a4cbe8df5fd6e0a2cd9fd88fb42e4d` | Exact input/output-rectangle response constraints, outward Gaussian CDF covers and complete finite refinement controls | [PR #68](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/68), merged into PR #67's branch |
| `0d8bd37633900f4f88200be13bd5309d28ca58f2` | Continuous shared Gaussian offset/blur domains, strict CLI, independent proof replay and complete documentation review | [PR #69](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/69), merged into PR #68's branch |
| `df53bc495a83ebf72c38f0f14a778e153d35b8db` | Tangent geometry for tapered rounded ends, stable local radius/centre updates and independent native-export controls | [PR #70](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/70), merged into PR #69's branch |
| `861de04baa0e55775e7a90faba9288ea2205abf6` | Documentation review through PR #70, critical-arc checks and source-preserving command/API verification | [PR #71](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/71), merged into PR #70's branch |
| `25ff63a2452d6d47ac382f2cf15bfb403d6a6203` | Circle-consistent joins, explicit per-boundary recovery and independent circle/arc controls | [PR #72](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/72), merged into PR #71's branch at `c3bd7bf`; source-bound [local evidence](validation/canonical-arcs.md) |
| `fa853df69e6c279ab63404cf1c4b9d989bd13ed2` | Complete documentation audit, corrected engineering guidance and regenerated handbook HTML/PDF | [PR #73](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/73), open draft at the 18:07 UTC observation |
| Current developer candidate | Complete finite-material Gaussian source model and bounded joint circular-segment fitting | Proposed on PR #73's branch; [source-bound evidence](validation/finite-shape-source.md), with production integration and physical qualification still separate |

The PR links show live review state. A documentation update does not install,
merge or deploy those changes. Record the checkout used to start a service:

```bash
git rev-parse HEAD
git status --short --branch
```

The health endpoint's `version: "0.1.0"` is shared by multiple revisions and
cannot identify which implementation a server is running.

The later review-branch changes remain separate from the observed `main` and the
primary `codex/slicer-integration` checkout at
`d747e30697a99a8f90d747d23d6ab7c1fa8b95ed`. The wall candidate's broader search and conditional
numerical checks do not establish physical edge identity. The matched final-Keys
prototype and conditional covariance module are developer research and are not applied to tracing. New review
branches do not change an already running or installed application.

## Implemented capabilities and remaining limits

| Capability | Engineering basis | Remaining limit or required check |
| --- | --- | --- |
| Flat-part reconstruction | Reviewed 2D outer boundary and through-holes, uniform scale and entered thickness | No hidden geometry, varying thickness or original feature-history recovery |
| Reference-sheet correction | One radial coefficient, plane homography, subpixel edges and conditional wall/parallax correction | Assumed optics, tone response and wall geometry; no measured-phone accuracy result |
| Fitted circles, lines and arcs | Residual gates, initial-boundary support, tapered-cap constraints and circle-consistent final joins | Disjoint/ambiguous joins retain a notified source outline; consistency does not establish physical accuracy. [Check critical arcs](exports.md#verify-critical-arc-geometry) |
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
| Finite-shape source developer candidate | [Complete controls and regression](validation/finite-shape-source.md): 1,714 Python tests passed; 28 forward rows/182 checks and 29 inverse rows/256 checks | Supplied pose/optics/noise, retained ambiguity and work-limited cases; no production integration or physical qualification |
| Circle-consistent final-assembly candidate | [Construction and recovery](validation/canonical-arcs.md): 1,609 Python tests, 74 isolated browser scenarios, 132 independent rows/394 checks and all six actual-fit controls pass | Digital circle consistency and explicit source recovery; original 72/74 browser run retains two unattributed build-busy failures; no physical qualification |
| Tapered rounded-end geometry candidate | [Source-bound repair and native exports](validation/tapered-caps.md): 1,556 Python tests, 74 browser scenarios, 20 new focused cases and all 11 native-export rows pass | Exact synthetic geometry, line-anchor invariance and retained arithmetic limits; no physical camera or manufacturing qualification |
| Continuous Gaussian-response domain candidate | [Joint-domain controls](validation/gaussian-response-domains.md): 1,536 Python tests passed; all 27 analyses independently replayed, including 319 tree nodes and 396 CDF certificates | Supplied straight-edge/response model, complete retained unknowns and no general convergence or physical qualification |
| Bounded-input response developer candidate | [Rectangle/CDF experiment](validation/response-rectangles.md): 1,446 Python tests passed; all 288 finite cases retained, with 200 outer-box exclusions, 82 every-input certificates and six box-undetermined cases | Supplied mathematical Gaussian/response model; Cartesian compatibility alone is insufficient for correlated input feasibility |
| Common-response calibration developer candidate | [Exact response/edge controls](validation/response-calibration.md): 1,324 Python tests passed, 1,170 finite whole-profile candidates, nine gauges and independent exact graph/certificate checks | Exact supplied inputs and calibration bounds; no inferred physical calibration, inverse correction or continuous offset certificate |
| Raw-source fitting developer candidate | [Complete source/conditioning controls](validation/raw-source-fit.md): 1,273 Python tests passed; 36 matched offset/brightness fits, 144 conditional noise fits, retained adverse cases and independent geometry/Decimal checks | Supplied lens-free geometry/optics/noise and fixed source modes; no production or physical acceptance |
| Known warp-chain developer candidate | [Digital and optical controls](validation/warp-observations.md): 1,249 Python tests passed, including 24 new cases; 324 readouts and 18 separate optical fields | Known numerical composition and supplied optical models; camera calibration and image-derived parameter uncertainty remain open |
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
| Documentation alignment through PR #62 | [Coverage and checks](validation/documentation-alignment.md) | Source/review state, current commands and repository-wide documentation checks; prior product results retain their source bindings |
| Documentation review through PR #64 | [Complete inventory and checks](validation/documentation-latest.md) | Current source/navigation, API/diagnostic wording and documentation checks; no fresh full software or physical qualification |
| Documentation review through PR #66 | [Complete inventory and checks](validation/documentation-response-state.md) | Current source/review state, executable response examples, command/API contracts and repository-wide documentation checks |
| Documentation review through PR #70 | [Preceding inventory and checks](validation/documentation-pr70.md) | Current guides, remaining arc limitation, command/API consistency and documentation checks at that source; prior software regressions retain their source bindings |
| Documentation review through PR #72 | [Complete inventory and checks](validation/documentation-pr72.md) | Current source/review state, task navigation and command/API consistency; historical software and library results retain their source bindings |

Hosted results are bound to exact heads. Earlier rows retain their last recorded
results. The PR #61–#63 workbench rows retain the **November 12, 13:27 UTC**
observation. PR #64 retains its **14:08 UTC** check. PR #65 and PR #66 workbench
runs were checked on **November 12, 14:27 UTC**; PR #66's workbench result was
refreshed at **14:35 UTC**, its library result at **14:30 UTC**, and PR #67's
workbench run at **15:17 UTC**, when it had completed successfully. PR #68's
workbench and library runs were checked at **15:17 UTC**; its workbench
result was refreshed at **15:39 UTC**. PR #69's two runs were checked at
**15:39 UTC**; PR #69's workbench run was refreshed at **16:02 UTC**. PR #70's
workbench run and PR #71's run were refreshed at **16:46 UTC**. PR #72's run
was refreshed at **17:40 UTC** after its earlier in-progress observation. Each result remains
bound to its own head:

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
| `6d26727` | [Workbench run 122](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43214844810) | Exceeded the 30-minute job limit after 1,178 Python passes and 58/74 browser passes; incomplete suite |
| `6d26727` | [Library run 43](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43214844876) | Completed successfully |
| `778c339` | [Workbench run 123](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43217681248) | Completed successfully at 12:51 UTC; 1,225 Python tests and 74 browser scenarios passed |
| `778c339` | [Library run 44](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43217681198) | Completed successfully |
| `8523862` | [Workbench run 124](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43220874898) | Completed cancelled at 13:16 UTC; no complete hosted suite is inferred |
| `8523862` | [Library run 45](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43220874912) | Completed successfully |
| `ca32144` | [Workbench run 125](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43221471259) | Completed successfully at 13:16 UTC; 1,249 Python tests and all 74 browser scenarios passed |
| `ad7cc00` | [Workbench run 126](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43223199839) | Completed successfully at 13:21 UTC |
| `701aa91` | [Workbench run 127](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43227832662) | Completed successfully at 13:56 UTC |
| `701aa91` | [Library run 46](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43227832670) | Completed successfully at 13:31 UTC |
| `8b9c6a8` | [Workbench run 128](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43230540195) | Completed successfully at the 14:27 UTC check |
| `81dd087` | [Workbench run 129](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43234835732) | Completed successfully at the 14:35 UTC check |
| `81dd087` | [Library run 47](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43234835472) | Completed successfully at the 14:30 UTC check |
| `b27e48e` | [Workbench run 130](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43238706845) | Completed successfully at the 15:17 UTC check |
| `0b359ec` | [Workbench run 131](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43241865289) | Completed successfully at the 15:39 UTC check |
| `0b359ec` | [Library run 48](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43241865188) | Completed successfully at the 15:17 UTC check |
| `0d8bd37` | [Workbench run 132](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43247853904) | Completed successfully at the 16:02 UTC check |
| `0d8bd37` | [Library run 49](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43247853602) | Completed successfully at the 15:39 UTC check |
| `df53bc4` | [Workbench run 133](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43252921196) | Completed successfully at the 16:46 UTC check |
| `861de04b` | [Workbench run 134](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43255349019) | Completed successfully at the 16:46 UTC check |
| `25ff63a` | [Workbench run 136](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43266175690) | In progress at 17:32 UTC; completed successfully at the 17:40 UTC check |
| `fa853df` | [Workbench run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43272297785) | In progress, with no conclusion at the 18:07 UTC check |
| `fa853df` | [Library run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43272297950) | Completed successfully at the 18:07 UTC check |

Follow the exact run links for later results. The raw-source candidate's local 1,273-test result is
separate from hosted CI. The response-calibration candidate records its own local
regression in its validation report. Earlier observations remain in their dated validation
records; successful CI does not merge, install or qualify a physical part.
No library workflow was observed for PR #70; its changed paths do not match the
library workflow's trigger filter. This is separate from its local library
documentation tests and the historical Revision 7 release checks.

## Next engineering work

The current candidate constructs circle-consistent final joins or retains the
affected source outline with a notice. Its minimum-displacement rule does not
identify a unique physical join or qualify the corrected circle. Prioritize
finite-shape model adequacy and independent measurements that distinguish
competing boundaries. Disabling **Recover design intent** still permits blur
correction; use the [export checks](exports.md#verify-critical-arc-geometry)
to review critical curves and joins independently.

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
declared finite smoothing and shared-pixel covariance. The [warp-chain extension](validation/warp-observations.md)
now composes known earlier rectification. Realistic noise/optical-model discrepancy,
image-derived parameter uncertainty, correlated neighboring profiles and globally
ambiguous wall interpretations remain open.
The [source-space primitive](raw-source-fit.md) now fits a declared straight raw
Gaussian source with both target and model in the same retained source modes.
Its explicit raw/complement diagnostics preserve invisible model mismatch.
Unknown optics/response, radial/curved edges and jointly inferred geometry remain
open before a production correction or physical likelihood is justified.
The [response constraints](response-calibration.md) check one common curve at
exact supplied inputs; the [rectangle extension](response-rectangles.md) adds
closed input intervals and bounded mathematical CDF evaluation. The
[continuous Gaussian-domain tool](gaussian-response-domains.md) now couples
one offset/blur pair under that supplied 1D model. Unknown camera optics,
uncertain calibration coordinates, image-derived geometry and justified
camera-specific error budgets remain further engineering work.
Keep observation-error bounds separate from model discrepancy, local fit spread
and endpoint-placement sensitivity. Numerical or work-budget exhaustion must
remain unresolved rather than becoming a physical claim.

Native slicer acceptance, installed versions, actual printer/material profiles,
layer previews and physical coupons remain separate qualification tasks. No
real-photo accuracy study, physical-fit acceptance or live-AI quality comparison
is recorded by this documentation refresh.
