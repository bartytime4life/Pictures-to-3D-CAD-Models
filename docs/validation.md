# Validation results

Use the [documentation index](README.md) to find a guide and the revision-bound
record below to assess its evidence. This page separates local checks, hosted
CI, library releases and physical qualification. Older sections retain their
original counts and environment; they are not later retests.

For a concise source/review snapshot, use [project status](project-status.md).
The [current documentation follow-up](validation/documentation-current-state.md)
records its own checks without rerunning or relabeling the historical suites.

## Current workbench evidence — November 12, 2026

The [corner-resolution candidate](validation/sharp-corner-resolution.md) at
`a3a2397`, based on `ba94ef8`, passed **630 Python tests**, including seven new search/fallback
regressions, and **74 browser scenarios**. It checks that numerical bisection
has an upper crossing and describes sharp-corner estimates as conditional on
the blur model. Its independent rounded-corner counterexample remains a
model-adequacy limitation; no physical radius bound is established.

The preceding [radial inverse and independent-renderer candidate](validation/radial-inverse.md)
after integration of `main` at `5c07d0f` passed **623 Python tests**, including 30
new lens checks, and **74 browser scenarios** against its local CAD service.
It restricts inversion to the central camera branch and
adds separately implemented synthetic lens calculations. Higher-order lens
stress cases retain nonzero reserved-dimension errors. The separate
[30-case directional-spread study](validation/directional-spread-qualification.md)
found missed directional cases and unknown outcomes; no production warning or
anisotropic correction was added. The [documentation follow-up](validation/documentation-review-2026-11-12.md#model-checks-follow-up)
records its browser and documentation checks separately.

The [initial-fit support repair](validation/fit-support.md) adds enclosed-center
and complete assembled-boundary checks while retaining separate coarse coverage
and subpixel measurements. Integration with the merged wall/height changes passed
**529 Python tests and 74 browser scenarios**; the later complete run including
PR #43 passed **579 Python tests**. Its record separates these completed
runs from earlier development and source-substitution controls. This
does not establish final forward-model adequacy or physical accuracy.

The [November 12 documentation review](validation/documentation-review-2026-11-12.md)
covers the complete documentation set against `main` at `eec45d0`, then the
merged PR #43 at `d6a657f` and the initial-fit support candidate. It includes
the merged wall/height behavior, current benchmark schema and
retains separate records for documentation checks, code/browser tests and
research that has not entered the production pipeline.

The earlier scientific documentation follow-up reviewed `main` at
`5588a523c70e1797341329e54d056c161d0361ad`, after PR #39. Its
[scientific model review](validation/scientific-model-review.md) records new
counterexamples and documentation checks, without changing runtime behavior or
claiming the proposed fixes are implemented.

The earlier documentation refresh initially reviewed `main` at
`76f03fce60c2a9193501e73f3e4d4ad85bbcf554` after PR #36, then incorporated
PR #37's shadow correction at `567b5bdd36cbc2ab6b666b9514c84e7764a07445`.
It changes guides relative to that integrated baseline, not runtime behavior.

| Evidence | Revision and result | Scope |
| --- | --- | --- |
| Corner resolution and search validity | [Method and checks](validation/sharp-corner-resolution.md), candidate on `ba94ef8`: **630 Python tests**, **74 browser scenarios**, four-case independent corner sweep passed | Independent wedge observations, four failing original controls and three passing controls; rounded-corner mismatch remains, with conditional wording |
| Weak-edge error recovery | PR #45, merged in `4e607d9`; [record](validation/contrast-recovery.md): **583 Python tests** at its PR #44 integration | Four original failures now recover or give actionable 422 guidance; thresholds and fallback policy retained |
| Constrained fillet sectors | PR #46, merged in `5c07d0f`; [record](validation/fillet-sweep.md): **589 Python tests** at its PR #44 integration | Six failing original controls, genuine major arcs and exact STEP/DXF checks; scalar blur-model mismatch remains |
| Radial inverse and independent simulation | [Domain and checks](validation/radial-inverse.md), candidate integrated with main `5c07d0f`: **623 Python tests**, **74 browser scenarios**; the separate earlier phase passed 609/74 | Decimal numerical oracles, independent lens code and source-bound higher-order mismatch examples; no physical camera qualification |
| Directional-spread qualification | [Frozen 30-case record](validation/directional-spread-qualification.md), pinned `2d76aea`: 27 traces, 6 flags, 16 eligible-unflagged, 5 ineligible, 3 trace failures | Synthetic research, orientation counterexamples and unknown states; no production warning/correction or population-rate claim |
| Global benchmark correspondence | PR #43 merged at `d6a657f`; [candidate integration record](validation/benchmark-correspondence.md): **91 focused tests** and a fresh three-photo CLI example | Exact-cost matching oracles and coverage conservation; errors remain conditional, synthetic and separate from physical feature identity |
| Integrated initial-fit support | [Method and checks](validation/fit-support.md), `d6a657f` plus the support candidate: **579 Python tests**, build and lint passed; **74 browser scenarios** before the benchmark-only merge | Synthetic geometry, generated photos and explicit transport fixtures; API/frontend sources unchanged by that merge; no physical-accuracy claim |
| Earlier PR #44 documentation review | [Coverage and checks](validation/documentation-review-2026-11-12.md), integrated `d6a657f` plus the support candidate | Source consistency, local navigation and companion-library documentation at that revision; later model-check follow-ups retain separate evidence |
| Recorded camera-height checks | Branch `claude/camera-height`, on the narrow-wall commit: **508 Python tests**, **74 browser scenarios**, Ruff passed, as recorded [below](#camera-height-from-the-holes-roundness--november-11-2026) | Local result; synthetic photos and exact silhouettes |
| Recorded narrow-wall and blur-sampling checks | Branch `claude/narrow-walls` on `5588a52`: **505 Python tests**, **74 browser scenarios**, Ruff passed, as recorded [below](#near-frontal-wall-tone-and-cubic-blur-measurement--november-11-2026) | Local result; synthetic photos and exact profiles, including what got worse |
| Scientific documentation follow-up | [Findings and checks](validation/scientific-model-review.md), baseline `5588a52` | Circle fitting-stage and full-tracer directional-blur counterexamples, benchmark aggregation fixture, current guide corrections; not real-photo or physical qualification |
| Zero-blur fallback | PR #39, code `d02a593`; the existing targeted regression passed in this follow-up | One test of median-level fallback; not a new full Python/browser suite or measured low-contrast-photo validation |
| Recorded shadow-correction checks | `bbd665bec6c0d32b8ed950c69d2c102e5f7b00ce`: **501 Python tests**, **74 browser scenarios**, Ruff passed, as recorded [below](#edge-levels-follow-a-shadows-slope--november-11-2026) | Upstream local result, not rerun for this documentation change; synthetic photos, including the reported near-frontal regression |
| Earlier guided-workbench checks | Guided code `900999b119eb3688ed75ed4212902c185023454b`: **498 Python tests**, **74 frontend/browser tests**, build and lint passed | Real local CAD backend; synthetic inputs and explicit AI response fixtures; before PR #37 |
| Hosted guided-workbench CI | PR head `aa556cfc75c3fe23a3b68e12be8973bf88705d7a`: [Validate workbench run 88](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43120297057) completed successfully | That exact revision, separate from later tracing and documentation CI |
| Interface review | [Guided-workbench audit](validation/guided-workbench.md) | Fresh desktop captures, phone reflow, input/settings/save recovery, reference-unit and AI-staleness regressions |
| Companion library release | [Revision 7 record](../reference-library/VERIFICATION.md), dated November 9 | Independent library checks and generated synthetic examples; not a new workbench run |
| Documentation refresh | [Coverage and checks](validation/documentation-refresh.md) | Guide/source consistency, local links and anchors, existing documentation tests and generated-output reproduction |

The local checks do not establish live-model quality, native slicer acceptance,
physical fit, manufacturing accuracy or complete accessibility conformance.
See the [engineering model](engineering-model.md) for qualification inputs.

Additional November 11 records below cover continuous-angle bed placement and
exact-corner fillet fitting on the local Linux workstation, plus the FreeCAD
import check, linear-light edge measurement, phone-photo decoding, photo
benchmark runner, SVG/PDF drawings, fillet-radius correction, arc-chord fit and
stub fix in managed cloud sessions. The [reference-sensitivity record](validation/reference-sensitivity.md)
covers the endpoint explorer. The original CAD release and optional Ollama
integration retain separate historical evidence. These records do not establish
that a newly created or published cloud task has been validated.

## Camera height from the holes' roundness — November 11, 2026

Branch `claude/camera-height`, on the narrow-wall commit below. It follows up that record's "what got worse". See [reference-sheet tracing](reference-sheet.md), §5, for the method.

- **The defect.** In a frontal photo the sheet fixes neither the focal length nor the camera height. Without EXIF a typical 26 mm lens was assumed: 9 % off for the rendered 28.6 mm lens at 440 mm, which left the 4 mm plate's outline 0.105 mm off, and 35 % off for a 40 mm lens at 600 mm (0.43 mm).
- **The fix** (`edges.roundness_focal`). A hole's near side is traced on the top edge and its far side on the bottom edge, so with a wrong height the corrected hole is stretched along the direction from the nadir. The focal length whose pose makes the round holes round is searched over 10–200 mm, the walls are refined again with that camera, and the trace says so. A slot, or any hole that is not round, is left out.
- **Exact silhouettes.** Holes drawn as the overlap of a bottom outline and its magnified top outline give the focal length within 0.05 % (0.009 % measured). A hole centred on the nadir, or no round hole, determines nothing.
- **Rendered overhead photos of the 4 mm plate** (worst errors in mm; Ø6, Ø22, slot, hole position, outer; camera height found against the true one):

  | Photo | Lens assumed (narrow-wall commit) | Height from the holes | Height (mm) |
  | --- | --- | --- | --- |
  | 28.6 mm lens, 440 mm, shadow | 0.0361, 0.0074, 0.0257, 0.0256, 0.1058 | 0.0077, 0.0054, 0.0135, 0.0078, 0.0047 | 437.2 / 440.0 |
  | Same, no shadow | 0.0351, 0.0083, 0.0264, 0.0262, 0.1079 | 0.0069, 0.0057, 0.0137, 0.0057, 0.0088 | 436.4 / 440.0 |
  | 24 mm lens, 380 mm | 0.0220, 0.0059, 0.0081, 0.0245, 0.1043 | 0.0047, 0.0075, 0.0081, 0.0077, 0.0087 | 381.0 / 380.0 |
  | 40 mm lens, 600 mm | 0.1250, 0.0140, 0.0685, 0.0913, 0.4289 | 0.0033, 0.0040, 0.0125, 0.0163, 0.0347 | 623.4 / 600.0 |
  | Noise seed 3 | 0.0371, 0.0084, 0.0231, 0.0238, 0.1041 | 0.0008, 0.0060, 0.0077, 0.0078, 0.0250 | 448.5 / 440.0 |
  | Noise seed 11, no shadow | 0.0323, 0.0093, 0.0067, 0.0259, 0.1075 | 0.0046, 0.0067, 0.0053, 0.0071, 0.0100 | 435.7 / 440.0 |

  The longer lens's camera is farther away, where the parallax it measures is smaller, so its height is 3.9 % off. Photos whose focal length the sheet or EXIF gives are unchanged.
- **The narrow-wall record's inference holds.** With the height from the holes, hole positions on the overhead photo read 0.0078 mm, against 0.0256 mm with the assumed lens: the guessed height had made them worse, not the wall model.
- **Photo benchmark example.** Median absolute error 0.004 mm, 95th percentile from 0.033 to 0.014 mm, worst from 0.105 to 0.015 mm; the overhead photo's camera height is found as 444.5 mm for 440 mm.
- **Not verified.** The holes are assumed round; a hole made oval along the direction from the nadir would bias the height. A part without round holes still uses the assumed lens.
- **Zero blur.** #39 made the edge levels fall back when `edges.edge_sigma` returns 0. The wall refinement, now `reference._refine_walls`, divided by the same σ: its weights came out NaN and happened to leave the points alone, with numpy's warnings. It now returns the points as traced (`test_wall_refinement_leaves_points_as_traced_without_a_measured_blur`, which fails without the guard).
- **Checks run.** `pytest`: **508 passed**. New: `test_the_camera_height_makes_thick_holes_round_again`, the zero-blur test above; `test_frontal_photo_without_exif_finds_its_camera_height_from_the_holes` replaces the test that allowed half as much again as the limits for the assumed lens, and holds two lenses to the plain limits. Four planted faults were each caught: a slot kept in the fit, no flatness test, no parabola refinement, and the estimate found but not used. Ruff passed. All 74 browser scenarios passed with the system Chrome. The height search adds about 0.1 s to a frontal trace without EXIF.

## Near-frontal wall tone and cubic blur measurement — November 11, 2026

Branch `claude/narrow-walls`, on `main` at `5588a52` (the browser scenarios on `de6f65a`; the one change between, #39, touches only a zero-blur fallback). It addresses the near-frontal regression recorded in the next section. See [reference-sheet tracing](reference-sheet.md), §3 and §5, for the mathematics.

- **The defect.** At 5° tilt the 4 mm plate's walls are under 2.5 σ almost everywhere. No wall tone was measured, so nothing was corrected: Ø6 read 0.0205 mm off and the slot 0.0466 mm. A narrow band on its own confounds the wall tone with the edge offset.
- **The fix** (`edges.pooled_wall_tone`): one tone shared by up to 160 bands of 1–3.5 σ, the one that minimises their total fixed-tone residual. For each edge offset a band's residual is exactly quadratic in the tone (`edges._wall_tone_parabolas`), so the search takes about 0.02 s; written as repeated fits it took 1 s, and the refactor agrees with them to 2 × 10⁻⁹ px. Where the minimum is flat or at an end of the range, the old bound is noted instead.
- **What the first version found.**
  - On exact profiles the tone came out at 16.8 for 15, with edges 0.014 σ off. The two-step fit read its profiles by bilinear sampling, which is off by up to 2.1 grey levels in 200 at a blurred edge's shoulders. With Keys cubic sampling the tone is 15.11 and the edges are within 0.001 σ.
  - Cubic profiles alone made the rendered photos worse (5° Ø6 from 0.0068 to 0.0116 mm), until the blur was measured the same way. `edges.edge_sigma` also read bilinear profiles. Bilinear sampling adds a variance of 1/6 px² on average, so on exactly blurred edges it read σ 2.2–4.2 % high at 1.6 px and up to 8.4 % at 1.2 px, against 0.6 % and 2.3 % with cubic sampling. Every model that takes σ had been given the larger blur. The benchmark example's reported blur drops by 2.7 %.
  - Bands under σ are left out. On noise-free profiles under 0.4 σ, cubic sampling's 0.3-level error alone made a false minimum (186 for 15, edges 0.18 σ off) that the flatness test passed.
- **Rendered photos** (worst errors in mm; Ø6, Ø22, slot, hole position, outer):

  | Photo | `main` | This branch |
  | --- | --- | --- |
  | 5° tilt, 4 mm, 25 % shadow | 0.0205, 0.0130, 0.0466, 0.0125, 0.0072 | 0.0068, 0.0025, 0.0184, 0.0062, 0.0063 |
  | 5° tilt, 4 mm, no shadow | 0.0161, 0.0134, 0.0448, 0.0111, 0.0028 | 0.0042, 0.0053, 0.0189, 0.0052, 0.0020 |
  | Overhead, 4 mm, focal length from EXIF | 0.0159, 0.0099, 0.0305, 0.0164, 0.0203 | 0.0009, 0.0049, 0.0105, 0.0087, 0.0193 |
  | Overhead, 4 mm, phone lens assumed | 0.0505, 0.0138, 0.0475, 0.0149, 0.1048 | 0.0361, 0.0074, 0.0257, 0.0256, 0.1058 |
  | Tilted 47 % shadow (blur measurement only) | 0.0018, 0.0093, 0.0155, 0.0150, 0.0101 | 0.0006, 0.0086, 0.0143, 0.0144, 0.0088 |

  On the other documented photos ([reference-sheet tracing](reference-sheet.md), results) most figures improve slightly. The largest increase is 0.0015 mm: Ø6 on the tilted 2400 × 1800 photo, from 0.0021 to 0.0036 mm.
- **Photo benchmark example.** Median absolute error from 0.005 to 0.004 mm, 95th percentile from 0.043 to 0.033 mm, worst 0.104 to 0.105 mm (the overhead photo's outline).
- **What got worse.** Overhead with an assumed lens, hole positions go from 0.0149 to 0.0256 mm, and the benchmark example's centre distances from −0.015 to −0.035 mm at worst (the overhead photo). The likely cause is the guessed camera height: the parallax correction misplaces each hole's near side, and the wall's pull on its far side had partly offset it. With the focal length from EXIF, positions improve from 0.0164 to 0.0087 mm. This is inferred from that comparison, not isolated.
- **Tests changed.**
  - `test_two_step_wall_model_is_unbiased_with_a_known_wall_tone_and_degenerate_without` had shown the free fit's degeneracy through bilinear sampling's error. It now adds half a grey level of noise: the free fit's edges scatter by 0.14 σ, the fixed-tone fit's stay within 0.01 σ.
  - `test_inside_and_outside_fillets_of_an_l_shaped_plate` allows 0.012 mm (was 0.01 mm), and under half each fillet's reported uncertainty. At the 2.5 px blur the inside R3 fillet reads 0.011 mm large. Given the true blur it reads 0.0106 mm large in this pixel phase and 0.0001 mm with the plate moved 0.37 px. That is the test renderer's discrete blur of edges on pixel boundaries, which the 1.2 % larger bilinear blur had offset.
  - The sheet-reference browser scenario's provisional width, before a thickness is entered, now accepts 120–123 mm (was 120–121 mm). Traced without a thickness, the 4 mm part's silhouette is its top and bottom faces together. `main` kept that outline as traced and aligned it at 7.44°; the branch fits it as arcs and lines and aligns it at 6.47° (true 8.00°). With the thickness entered both trace 120 × 70 within 0.1 mm, which the scenario still checks.
- **Checks run.** `pytest`: **505 passed**. New: `test_one_wall_tone_shared_by_narrow_bands_is_recovered`, `test_edge_blur_is_measured_without_the_samplers_own_blur` and `test_a_near_frontal_thick_photo_estimates_its_wall_tone_from_narrow_bands`. Five planted faults were each caught: bilinear profiles in the two-step fit or in the blur measurement, no band rule, no flatness test, and no parabola refinement of the tone. Ruff passed. All 74 browser scenarios passed with the system Chrome. A near-frontal trace takes 0.73 s, against 0.68 s on `main`.

## Edge levels follow a shadow's slope — November 11, 2026

Branch `claude/sloped-levels`, on `main` at `76f03fc`. The figures below were taken on `47e3352`; the changes since touch no tracing code. It implements the roadmap item "edge levels that follow a shadow's slope". See [reference-sheet tracing](reference-sheet.md), §3, for the mathematics.

- **The defect.** A soft shadow brightens the paper away from an edge. The edge's mid-level, the mean of the medians at the profile's two ends, then sat too far out, about 2.7 σ² b / (b₀ − a). On the tilted rendered photo a shadow removing 25 % of the light put Ø22 0.026 mm off, and one removing 47 % 0.054 mm.
- **The fix** (`sheet.half_level_search` with σ, used in the second edge pass):
  - The paper side's light is fitted as a line beyond 2.5 σ, after removing the step's own blurred tail, and the material side keeps a flat median.
  - The level, (A(e) + B(e))/2 + (b₁ − a₁) σ/√(2π), is exact at the edge for a Gaussian-blurred step between linear plateaus.
  - The correction from the median crossing is smoothed along each ring over 20 points.
- **How it was settled.**
  - Fitting both sides read a thick part's narrow wall as a slope, so the material side keeps its median. Which side is paper comes from the classified mask 3 σ out.
  - Fitting one side alone read the step's own tail as a slope (0.011 px on a blurred hole), so the tail is removed first.
  - Without smoothing, small features got noisier. A slope-significance shrinkage gave back much of the correction (Ø22 0.0078 mm under the shadow), and 20-point smoothing did best.
- **Exact profiles.** On sloped profiles the crossing is within 0.002 px of the edge, flat plateaus included (the end medians: 0.003 px off flat, up to 0.18 px on the slopes). On blurred discs of 7.5–55 σ the radius is within 0.005 px of the blur-curvature series, and closer to it than the medians.
- **Rendered photos.**
  - Over six noise seeds of the tilted photo with the 25 % shadow, the mean errors went from 0.0103, 0.0244, 0.0290, 0.0044 and 0.0234 mm (Ø6, Ø22, slot, position, outer) to 0.0026, 0.0055, 0.0126, 0.0054 and 0.0046 mm. Without a shadow, and overhead, they are unchanged within 0.002 mm.
  - On the documented photos, the 22° photo of the 4 mm plate went from 0.0249 to 0.0058 mm on Ø22 and from 0.0173 to 0.0067 mm on the outline; the 4000 × 3000 tilted photo from 0.0103 to 0.0012 mm on Ø22.
- **What got worse.** The 5° photo of the 4 mm plate, whose walls are too narrow to model: Ø6 from 0.0078 to 0.0205 mm and the slot from 0.025 to 0.047 mm. There the shadow's outward push had cancelled the walls' inward pull; without a shadow the old trace already read Ø6 0.013 mm and the slot 0.042 mm. The photo benchmark's overhead example (4 mm thick) reads its outline 0.10 mm short, where it read 0.09 mm. That trace's notes already give the walls' bound.
- **Checks run.** `pytest`: **501 passed**. New: `test_sloped_plateau_levels_put_the_crossing_on_the_edge`, `test_ring_smoothing_averages_the_slope_correction_round_a_closed_ring` and `test_a_soft_shadow_no_longer_pushes_edges_out`, which replaces the deep-shadow test that bounded the old bias (its "tighten the bounds when this is improved"). The new shadow test fails with `main`'s edge tracer. Ruff passed. All 74 browser scenarios passed with the system Chrome. A trace of the rendered tilted photo takes 0.59 s, against 0.62 s on `main`.

## Rounded polygons are not taken for circles — November 11, 2026

Branch `claude/circle-gate`, on `main` at `363f295` (after the renderer fix below). It resolves the second item found and not fixed in the exact-corner entry below.

- **The defect.** `fit_ring` takes a whole ring as one circle when a circle fits it within max(tol, 1 % r) RMS. The radius-relative allowance keeps slightly out-of-round holes circles, but a rounded polygon passes it too. A rendered 12-gon on a 45 mm circle with R12 corners lies 1.95 px (0.39 mm) RMS from its best circle, eight times the line tolerance, and was exported as one cylinder.
- **The fix.** A ring that passes only by the allowance, not within the line tolerance itself, is also described as lines and arcs, and that description wins when it has straight edges and its worst residual is under a third of the circle's.
- **After.** The 12-gon with R12 corners and a 16-gon with R15 corners are their lines and arcs. The 12-gon's radii are within 0.033 mm. The 16-gon's 157.5° fillets are within 0.063 mm, where the reported standard deviation is 0.285 mm, because the outline moves only 0.02 times a change of radius. A rendered disc and holes 1 % and 2 % out of round stay circles.
- **Checks run.** `pytest`: **474 passed**. Both cases of the new `test_a_rounded_polygon_close_to_a_circle_is_not_taken_for_one` fail without the fix. Ruff passed.

## Exact coverage in the test renderer — November 11, 2026

Later interpretation: radius “bounds” in this historical section are conditional
blur-model resolution estimates. The [resolution-search review](validation/sharp-corner-resolution.md)
retains the original fixtures and explains why they are not physical upper bounds.

Branch `claude/edge-orientation`, on `main` at `5cebd27`. It resolves the first item found and not fixed in the exact-corner entry below.

- **The finding.** That entry blamed the sub-pixel tracer for placing edges along the pixel axes and along the diagonals about 0.03 px apart. The cause is the test renderer instead. `synthetic.coverage` sampled each pixel's coverage on eight sub-rows, exact along each sub-row and quantised across them. At rational slopes, where every pixel along an edge has the same sub-pixel phase, that quantisation does not average out: square edges at 45° and at 26.6° (slope ½) read 0.012 to 0.027 px out or in, depending on the phase, against at most 0.003 px at other angles.
- **How it was found.** An analytically blurred square, sampled at pixel centres with no rendering, traces within 0.003 px at every angle and phase tried: 0°, 26.6°, 44° and 45°, each at four sub-pixel shifts. The rendered square showed the offset, and it shrank five- to eightfold with 64 sub-rows.
- **The fix.** `coverage` now accumulates each edge's exact signed area per pixel, as a polygon rasteriser does, so the coverage is exact. Against shapely's area of each pixel square it agrees to 3 × 10⁻¹⁶ over 3000 random pixels of a turned plate with a hole and a slot, crossing the image border. It renders that plate in 5 ms. Rendered square edges now read within 0.004 px at 45° and 26.6° at either phase. The octagon's 135° R4 fillets read 0.022 mm small, where they read 0.068 mm small before, within the reported ± 0.078 mm.
- **What moved.**
  - The documented rendered-photo accuracy figures (`docs/reference-sheet.md`, results) move by at most 0.002 mm, the largest the 4000 × 3000 overhead slot from 0.0032 to 0.0015 mm; the table now shows the exact-coverage run.
  - The fillet uncertainty's 0.03 px systematic edge allowance (`fitting.EDGE_SYS_SD`) is kept, now stated as an allowance for what rendering leaves out (demosaicing, JPEG, a lens blur that is not Gaussian), not as a measured tracer offset.
  - A rendered triangle's sharp 60° corners now bound any fillet under R0.59 mm, where it was under R0.5 mm. At an acute tip the tracer's local level cannot reach both plateaus, its points sit a little off the half-level, and their residual sets the bound. The test allows R0.75 mm there and keeps R0.5 mm at right and wider corners.
- **Checks run.** `pytest`: **472 passed**. The new `test_rendered_coverage_is_exact_and_edges_keep_their_place_at_any_phase` fails with the earlier sub-row coverage. Ruff passed.

## Corner sweep script — November 11, 2026

Later interpretation: “bound” below is the historical CLI terminology. Current
output calls it a conditional radius-resolution estimate; see the
[search guard and model limits](validation/sharp-corner-resolution.md).

Branch `claude/corner-sweep`, on `main` at `48e17d2` (after the fillet-corner change below). It adds `scripts/corner_sweep.py` and `make corner-sweep`, the exact-blur corner sweep behind the entry below, so that its figures can be reproduced.

- **What it does.** It blurs filleted pentagons (corners of 60°, 90°, 120° and 150°; r = 5 to 80 px; σ = 1.6 and 2.5 px) in the continuum by vertical slices, independently of `fitting.corner_level`. It traces each half-level outline exactly and runs it through `backend.reference`'s fitting chain with snapping on. It reports the worst radius error per corner angle in units of the blur shrink, the corners lost, and the corners reported sharp whose bound is below their true radius; either of those makes the exit status 1. `--backend PATH` runs another checkout's fitting chain; `--quick` runs four cases.
- **Reproduced.** On this branch: 0.00, 0.01, 0.03 and 0.28 s at 60°, 90°, 120° and 150°, no corner lost, five small 150° fillets reported sharp with bounds of 6.42, 7.95 and 8.04 px against true radii of 5, 5 and 8 px; exit status 0. With `--backend` on `main` at `dd65399`: 1.1, 2.5, 8.0 and 19.3 s, and two corners lost (a 150° R40 px and a 120° R12.5 px corner at σ = 2.5 px); exit status 1. Each run takes about four minutes.
- **Checks run.** `tests/test_corner_sweep.py` checks the script's integral against the closed form at a disc's centre (to 10⁻¹⁰), a straight edge's half-level (to 10⁻⁸ px), and one case's fit; it takes about six seconds. `pytest`: **457 passed**. Ruff passed.

## Exact blurred corners, two-chord arcs and sharp corners — November 11, 2026

Later interpretation: the [resolution-search review](validation/sharp-corner-resolution.md)
replaces the physical upper-radius wording below with a conditional blur-model
resolution estimate. The values and counts in this historical section retain
their original matched-model fixtures and revision. They do not establish a
bound for mismatched cameras or parts.

Branch `claude/fillet-corners`, on `main` at `ae69552`. Its "before" figures were taken on `dd65399`, which has the large-radius and stub fixes below; the bed-placement change after it touches no tracing code. See [reference-sheet tracing](reference-sheet.md), §4 and §7, for the mathematics.

- **How it was found.** The fillet-radius entry below left corners other than right angles unverified. An exact continuum blur of filleted polygons (from the 2026-11-10 study, now `scripts/corner_sweep.py`, `make corner-sweep`) traced corners of 60° to 150°, and the pipeline's fitting chain was run on those outlines. That showed four defects. Every "before" figure here is `main` at `dd65399`, with the large-radius and stub fixes.
- **Defect 1: wide corners.** The disc shrink s(r) holds only in the middle of a long arc. On exact outlines, fillets read up to 19 s large at 150° and 8 s at 120°, and nothing flagged them. (Before the stub fix, which refits small arcs on their points between the lines, it was 49 s, and rendered 150° R4 corners were up to 1.9 mm off.)
- **Defect 2: two-chord arcs.** An arc cut into only two chords goes back to two lines under the large-radius fix's rule that one chord is not an arc. A 150° R40 px corner at σ = 2.5 px and a 120° R12.5 px corner lost their arcs, moving the outline 1.4 and 1.9 px.
- **Defect 3: tilted edges.** Douglas–Peucker hands each line the start of the next arc. Beside large radii that tilted the edges (0.24° beside R80 px), snapping kept the tilt, and fillets built on those edges read up to 2.5 s off at 90° and 8 s at 120°.
- **Defect 4: sharp corners.** Blur rounds a sharp corner, and it was fitted as a fillet: R0.4 to R1.1 mm on rendered sharp plates, exported as cylinders.
- **The fixes** (`backend/fitting.py`):
  - Fillets are refined against the exact blurred corner (`corner_level`), on the arc and the edges out to 5 σ. Each gets a standard deviation that carries noise, its measured correlation, a 5 % blur uncertainty and a 0.03 px systematic edge error.
  - A fillet the photo cannot tell from a sharp corner is traced sharp, with a bound on any fillet there.
  - After the large-radius rule, runs along one circle that no line fits, whose straight-looking edges each bow along that circle, are marked curved (`_curved_runs`). The bow test keeps the facets and flats that rule keeps as lines.
  - Lines are refit on their straight parts before snapping (`refit_lines`).
  - Undetermined radii and sharp corners are named in the trace's notes and warnings, each note within the profile's 300-character limit.
- **Exact outlines, before and after.** Worst radius errors in units of s over 24 cases (σ = 1.6 and 2.5 px, r = 5 to 80 px):

  | Corner | Before | After |
  | --- | --- | --- |
  | 60° | 1.1 s | 0.00 s |
  | 90° | 2.5 s | 0.01 s |
  | 120° | 8.0 s | 0.03 s |
  | 150° | 19 s | 0.28 s |

  Two corners lost their arc before, their edges meeting with no warning; none does after. Five small 150° fillets (r ≤ 3.2 σ) are traced sharp, each with a bound above its true radius. These are the counts of `make corner-sweep`, which takes every corner into account; an earlier summary that left out cases with a lost corner gave 16 s and 0.22 s for 150°.
- **Rendered plates, before and after** (5 px/mm, traced with snapping on):

  | Plate | Before | After |
  | --- | --- | --- |
  | 120 × 70, R20, 0.34 mm blur | 0.006 mm | 0.002 mm |
  | 120 × 70, R30, 0.34 mm blur | 0.005 mm | 0.001 mm |
  | 12-gon (150°), R4, 0.32 mm blur | 0.13 mm, no uncertainty | 0.11 mm (reported ± 0.19) |
  | Octagon (135°), R4, edges on the pixel axes | −0.070 mm | −0.068 mm (reported ± 0.078) |
  | Hexagon (120°), R3 | 0.014 mm | 0.014 mm |
  | L-plate, inside and outside R8 | 0.003 mm | 0.003 mm |
  | Sharp 120 × 70 plate | four R0.4 to R0.6 mm fillets | sharp, any fillet under R0.23 mm |
  | Sharp hexagon, turned | six R0.6 to R1.1 mm fillets | sharp, any fillet under R0.45 mm |
  | Sharp plate, 0.5 mm blur | four R1.1 mm fillets | sharp, any fillet under R0.28 mm |

  On the photo benchmark's three rendered photos the R8 row is unchanged (+0.005 mm). The slot width moved from −0.023 to −0.021 mm, because its sides are now fitted without their end caps' first points.
- **Statistics.** Over forty tracings with 0.1 px noise correlated over four points, radii are unbiased within four standard errors. The reported standard deviation is 1.3 to 1.4 times the observed spread, and under half without the measured correlation. At 150° with R8 px fillets the photo cannot resolve the radius (observed spread 10 px); the fit names those fillets in every tracing, with a linearised standard deviation that understates the spread, so the note says "or more".
- **Checks run.** `pytest`: **456 passed**, none skipped (OpenSCAD is installed on this workstation). 25 tests are new: 14 in `tests/test_fidelity_math.py` and 11 in `tests/test_sheet_reference.py`. The large-radius fix's tests pass unchanged. In the stub fix's `test_a_stub_cut_off_a_straight_edge_is_fitted_as_part_of_it`, the snapped case now expects the plate's three blur-rounded right angles to be sharp, each with a bound under 0.6 mm on any fillet, in place of arcs under 0.6 mm. Each of seven faults planted in this change, one at a time, failed at least one test: no two-chord runs, chords not required to bow, no systematic edge term, the disc model only, a wrong sign in the corner integral, noise correlation ignored, and lines not trimmed at arcs. Ruff passed. The two reference-sheet, eight workbench and two placement browser scenarios passed with the system Chrome; the others were not re-run. `make freecad` was not run (FreeCAD is not installed on this workstation). A full trace of the rendered plate takes 0.65 s at 2400 × 1800 and 1.89 s at 4000 × 3000, against 0.57 and 1.72 s on `main`.
- **Found and not fixed.**
  - The sub-pixel tracer places edges along the pixel axes and along the diagonals about 0.03 px apart. A 135° corner magnifies that twelve times, so the octagon's fillets read 0.07 mm small; the systematic edge term carries it into the reported uncertainty. (Later traced to the test renderer, not the tracer: see "Exact coverage in the test renderer" above.)
  - The circle gate (RMS within 1 % of the radius) accepts a rounded 12-gon with R12 corners on a 45 mm circumradius as one circle.
  - With snapping off, short free arcs at wide corners are still biased; they are only named.
- **Not verified.** No real photo. A real lens's blur is not exactly Gaussian, and the model assumes it is.

The [suggested split-plan record](validation/split-plans.md) covers the subsequent
bounded search for the fewest fitting pieces, explicit apply/rebuild behavior
and preservation of measurements and exports.

The [curved-placement record](validation/curved-placement.md) covers conservative
fitted-curve enclosures, CAD-solid witness checks, and measurements independent
of export triangulation.

## Continuous-angle bed placement — November 11, 2026

Branch `codex/analytic-bed-placement`, based on `main` at `dd65399`, in an
isolated local worktree. The original checkout on `codex/slicer-integration`
was preserved. See [the derivation](research.md#continuous-angle-rectangular-placement)
and [user controls](print-planning.md).

- Reproduced before the change: a 125 × 10 × 4 mm bar was reported too large
  for a 100 × 100 mm usable rectangle because only 0° and 90° were checked.
  The new solver finds 45°, with a 95.459415 × 95.459415 mm footprint.
- Exact-fit synthetic rectangles rotated by 0.1234567°, 17.1234567°,
  67.8912345° and 123.456789° are recovered without an angle grid. Each is
  refused when both bed dimensions are reduced by 0.0001 mm.
- Thirty seeded polygon cases retain constructed feasible placements; random
  beds are compared with 3601 independently sampled angles. Returned witnesses
  are also checked with Shapely rotation. This checks software containment,
  not photographic or manufacturing accuracy.
- Real CAD builds of single and split bars preserve dimensions, volume, source
  recipes and export orientation. Applying each suggested turn to its actual
  output mesh independently satisfies the selected envelope. Both slicer
  manifests and the split manifest preserve the same placement result.
- Fitted curves retain a conservative solid-bounds check. An unsuccessful XY
  enclosing-rectangle check reports unknown; no sampled polygon is promoted
  to proof that the exact curved outline fits. Shaped/excluded/ambiguous beds,
  margins, build height and the legacy 90° flag retain coverage.
- `python -m pytest -q`: **431 passed**. The fitted-build assertion was also
  rerun after adding the geometry-basis check. Production TypeScript/Vite
  build, `make lint` and `git diff --check` passed.
- All **49 Chromium scenarios** passed across two batches: the new desktop and
  390 px mobile scenarios plus four existing print planning scenarios (6),
  followed by all remaining browser scenarios (43). They exercise keyboard
  disclosure, displayed angle and footprint, unchanged measurements, edit
  invalidation and rebuild, automated axe checks, capture/calibration, import
  recovery, reference-sheet tracing, assistant proposals and slicer exports.
- One 2000-vertex convex-polygon refusal took 0.077 seconds locally. This is
  one synthetic timing sample, not a throughput or latency guarantee.

The accepted [desktop](images/diagonal-placement-desktop.png) and
[mobile](images/diagonal-placement-mobile.png) screenshots were visually inspected.
No native slicer import, toolpaths, physical print, deployment or release was
validated by these checks. Reference-library code and outputs were unchanged.

## Stubs go back to their edges — November 11, 2026

Branch `claude/compassionate-darwin-rpfrg8`, on `main` at `7fc0d22`, run in a managed cloud session. This is the last item in the entry below's list of defects found and not fixed. See [reference-sheet tracing](reference-sheet.md), §7, for the method.

- **The defect as reported.** `fit_ring` returned `None`, and the outline stayed a polyline, when a breakpoint cut a short straight stub off a straight edge next to a sharp corner. The stub is too short to be a line. It was fitted with the corner's blur-rounded join as one arc, and that arc failed the residual check.
- **Reproduced first.** The reported script gave `None` at `sigma_px` 1.0 for flats of 4, 6 and 10 mm, and five lines and five arcs at 1.6. At 1.0 one breakpoint edge is 2.44 mm long, against a `min_line` of 2.47 mm, with a line RMS of 0.02 tolerances. The arc through it and the corner has a radius of 3.23 mm and a largest residual of 8.0 tolerances, against a limit of 6. The breakpoint is there because a chord between two corners' rounded joins runs parallel to the edge between them: every point of the edge is equally far from it, and which one counts as farthest is a matter of rounding.
- **It was wider than `None`.** Where the same arc passed the residual check, the outline was fitted with it and nothing was reported.
  - On exact geometry, a 100 × 60 rectangle whose ring starts 0.4 to 2.8 mm before or past a corner came out as four lines and an arc with a radius of 3 to 13 million. A ring's first point is always a breakpoint.
  - 330 rings were rendered from nine sharp-cornered shapes at 5 px/mm (a rectangle, an L, a five-sided plate, a triangle, a plate with two chamfers, a plate with five facets, and the reported plate with its three flats) and a 30 mm part at 5 and 10 px/mm, each at ten rotations from 0° to 45° and blurs of 1.1, 1.7 and 2.4 px, which is 0.22, 0.34 and 0.47 mm at 5 px/mm. 21 were `None`. Of the 309 fitted, 11 had the fitted outline more than 1 mm from the part, up to 7.5 mm. The 286 right-angle corners of the rectangle and the L were arcs of 1.9 to 18 blur widths, 85 of them over 3.
  - 13 rendered photos of the test plate with sharp corners in place of R8 were traced through the API with snapping on: nine of the plate as rendered for the tests, overhead and at 22°, with four noise seeds and blurs of about 0.3 to 0.5 mm, and four of the 4 mm plate with its thickness entered. 2 outlines were polylines and 3 traces were refused. Of the 8 fitted, 5 had the outline's size 0.67 to 3.77 mm off: a corner arc that swept 146° to 200° stood out from the plate.
- **The fix.** An arc with eight or more points clear of its lines has the points near those lines trimmed before its fit, a stub's among them. A smaller arc was fitted to all of its points. Now each line beside a smaller arc runs on to the last of the arc's points within half the tolerance of it, and the arc is fitted to the points between. Fewer than three points define no circle: the arc is dropped and its two lines meet at a corner. The change is in the trimming step of `fit_ring`.
- **Two tests on breakpoint edges were tried first and measured.**
  - Joining a short edge to the line edge beside it when the two together still fit one line within tolerance, as first proposed. It ended every `None` in the 330 rings, and on the outlines of the nine thin-plate photos above, taken from the API's traces, it read the plate's size within 0.06 mm. But a long line outweighs what it takes in. Every sharp-cornered ring lost corner arcs to its lines, and so did real fillets: on rendered 60 × 40 mm plates 23 of 24 R0.5 corners and 15 of 24 R1 corners became sharp, R2 corners read up to 0.23 mm off where they had read 0.02, and lines held points 9 to 14 tolerances from them.
  - Testing the short edge's own points against the line, to an RMS of half the tolerance times the edge's share of `min_line`. It kept the fillets and ended 20 of the 21 `None`s. But a stub often shares its edge with the rise of the corner, and edge noise of a fifth of the tolerance is already at that limit for a stub under 0.4 of `min_line`. On the nine outlines from the API four still had a corner arc sweeping 158° to 177°, with the size 0.37 to 1.52 mm off. With the test on points all nine are within 0.053 mm.
- **After the change.**
  - The reported plate at `sigma_px` 1.0 is five lines and five arcs for flats of 4, 6 and 10 mm. The R30 arc reads 0.006 to 0.007 mm small, and the three right-angle corners are arcs of 0.51 to 0.54 mm.
  - Of the 330 rings none is `None`. The 21 that were are within 0.54 mm of the part. Of the other 309, 120 are closer to the part by more than 0.05 mm and none is further by more than 0.03 mm. 4 remain more than 1 mm away, for the two reasons given under "Found and not fixed". The 300 right-angle corners are arcs of 1.4 to 2.2 blur widths. 19 rings have fewer corner arcs: corners with fewer than three points between their lines.
  - On the exact outline of a blurred sharp-cornered plate the corner arcs are 1.71 to 1.87 blur widths at 25 ring starts, where they were 1.71 to 20.2. With edge noise of a fifth of the tolerance they are 1.61 to 2.23, where 8 of 25 outlines had been `None`. Opposite edges stay the plate's width and height apart within 0.0005 mm, and 0.002 mm with the noise.
  - Through the API, 11 of the 13 photos are four lines and their corner arcs, with the outline's size within 0.058 mm with snapping on and 0.107 mm with it off. The holes and the slot are within the test limits in every trace, before and after. The other two are refused as before, for the reason given under "Found and not fixed".
- **Rounded corners are fitted as before.** 90 rings of R8 and R20 plates and a stadium, at the same rotations and blurs, are identical before and after, as are 300 noisy R8 rectangles. On 72 rendered rings with R0.5 to R3 corners at 5 and 10 px/mm, R2 and larger at 5 px/mm and R1 and larger at 10 px/mm are unchanged. Smaller fillets read closer. Fitted freely at 5 px/mm, R1.5 was up to 0.55 mm off and is up to 0.07, and R1 was up to 0.56 and is up to 0.17. Snapped, R1 and R1.5 read within 0.02 mm before and after. R0.5 at 5 px/mm, an arc shorter than the blur is wide, read up to 0.83 mm off and reads up to 0.34.
- **The related case.** A 120 mm plate with R20 corners and a 4 mm flat between them, rendered at 5 px/mm with `sigma_px` 1.6 and not rotated, came out as four lines and four arcs before and after in ten constructions of its outline, so the reported failure was not reproduced. The same failure appears at R12 with a 3 mm flat at `sigma_px` 1.0: breakpoints cut the flat into edges of 1.60 and 2.20 mm, neither is a line, and both corners and the flat are fitted as one arc of radius 14.02. It is the same after this change, and of 108 such plates (R12 to R40, flats of 3 to 12 mm, three blurs) it is the only one that is not four lines and four arcs with radii within 0.05 mm. It needs a different change: the flat has no line edge beside it to go back to, and what would make it a line is a test of consecutive short edges that together reach `min_line`.
- **Checks run.** `pytest`: **416 passed** and 2 skipped (the OpenSCAD checks; OpenSCAD is not installed in this session). 9 tests are new: 3 in `tests/test_fidelity_math.py` and 6 in `tests/test_sheet_reference.py`. All 9 fail on the unchanged code. Ruff passed. Twenty faults were planted in the new step, one at a time, and 18 failed a test. One of the other two matters only at a corner so shallow that points lie within half the tolerance of both its lines. The other matters only if a stub of the line before an arc runs through the ring's first point, and no test has one. The browser scenarios, Prettier and `make freecad` were not run; nothing in the frontend changed.
- **Found and not fixed.**
  - A straight edge shorter than `min_line` that is not part of a longer one is still not a line. That is the related case above, a facet of 3.2 mm that the ring's first point cut in two (one of the 4 rings still over 1 mm off), and any chamfer under `min_line`. Its points are fitted as an arc: on exact geometry a chamfer of 0.2 to 2.8 mm across a rectangle's corner comes out with a radius of 2 to 8 million, before and after.
  - A sharp corner's arc is the blur's rounding, about 1.8 blur widths. Where it is not made a tangent fillet, the radius correction for blur enlarges it about its centre by about a sixth, it sweeps about 120° and stands out from its two edges. That is the 0.04 to 0.11 mm by which the outline's size is off with snapping off, and it is the same before and after.
  - At an acute corner the blur rounds the outline further than an arc follows. Three of the 30 triangles, all at the 0.47 mm blur, have a fitted outline that crosses itself (5 before), which the tracer answers with the polyline.
  - A 4 mm plate with sharp corners photographed at 22° is refused, before and after. Its outline crosses itself at a corner once the thickness correction has moved its points, before anything is fitted.
  - With edge noise of 0.4 of the tolerance, twice what the rendered photos carry, one corner in 196 was five nearly collinear points and came out with a radius in the thousands of blur widths.
- **Not verified.** No real photo. Every figure above is from rendered images or exact outlines.

## Large-radius corners stay arcs — November 11, 2026

Branch `claude/keen-brahmagupta-imy1g4`, on `main` at `5508f49`, run in a managed cloud session. This is the defect the fillet-radius entry below left as found and not fixed. See [reference-sheet tracing](reference-sheet.md), §7, for the method.

- **The defect.** A rounded corner could be cut into a run of short straight lines. `fit_ring` places a breakpoint only where the outline bows 1.5 × tolerance from a chord, so on an arc of radius R it leaves chords of up to √(12 R tol). Any breakpoint edge of at least `min_line` whose points fit a line within tolerance was taken as a line, and chords that long pass both tests. It was reported for R20 at a 0.34 mm blur. The condition is wider than that: on rendered, blurred plates it also broke R25 and larger at a 0.23 mm blur, R12 at 0.46 mm, and R5 on a 36 mm plate, whose `min_line` is 1 mm.
- **What it cost.** On rendered photos of the test plate with R20 corners in place of R8, traced through the API, the overhead photo's outline fell back to a polyline of 67 segments. With R25 corners the overhead photo gave 20 lines and 10 arcs with the outline 0.96 mm off in size, and the 22° photo of the 4 mm plate gave 22 lines and 16 arcs with the outline 2.66 mm off. The test plate itself, with R8 corners, was never affected.
- **Reproduced first.** The reported harness (a 120 × 70 mm plate rendered at 5 px/mm and blurred) gave four lines and four arcs at R12 and R16, twelve lines and five arcs at R20, and 37 pieces at R30. Twelve of the new tests failed on the unchanged code. The other two guard straight edges and pass before and after.
- **The fix.** Each edge taken as a line is tested against the circle fitted to its neighbours, and joins the arc when its own points lie on that circle to an RMS of half the tolerance. Edges are tested in order, so an arc grows chord by chord. A chord absorbed on its own, still between two lines, becomes a line again.
- **After the change.**
  - The reported cases, R20 and R30 at a 0.34 mm blur, are four lines and four arcs. Their radii read within 0.003 mm fitted freely and 0.006 mm as fillets, and opposite edges are the plate's width and height apart within 0.002 mm.
  - Through the API, the plate with R20 corners reads its radii 0.005 mm small on the overhead photo, with the outline's size 0.002 mm off. With R25 corners the radii are 0.015 mm large on the 22° photo and within 0.001 mm on the 22° photo of the 4 mm plate, whose outline is 0.016 mm off.
  - 18 rounded plates and stadiums from R2 to R60, each rendered at blurs of 0.23, 0.34 and 0.46 mm and four rotations, make 216 rings. 41 came out as their design's lines and arcs before, and all 216 after.
  - 42 rendered photos of plates and stadiums with R5 to R30 corners were traced through the API: blurs of 0.29 to 0.55 mm, up to three noise seeds, overhead and at 22°. None gave the design's lines and arcs before, and all 42 after. The 989 chords absorbed in them sat at a median of 0.17 and at most 0.45 of the tolerance from their circle, against the limit of 0.5.
- **Straight edges.** The existing accuracy tests pass at their unchanged limits, and the test plate's slot is still two lines and two arcs. A stadium's 4 mm sides between R30 ends stay lines, on exact geometry and in four rendered photos. So does a 4 mm flat running tangentially off the end of an R60 arc, on exact geometry at a 0.03 tolerance. A corner turned by three 4 mm facets is fitted as before, on exact geometry and in four rendered photos. On 351 plates whose short side is a 3 to 12 mm flat between two R12 to R40 corners (216 on exact geometry, 135 rendered), the flat stayed a line and both corners kept their radius in all but one. In that one the flat's own breakpoint edge was shorter than `min_line`, so it was never a line.
- **What is absorbed that was a line.** Five 3.2 mm facets turning a corner in 15° steps bow 0.10 mm from a circle. At a 0.47 mm blur that is 1.5 × tolerance, and in two rendered photos the corner became an arc; at 0.29 mm the fit was unchanged. A flat running tangentially off the end of an arc is kept once it is about as long as the arc's longest chord. On exact geometry at R60 and a 0.05 tolerance, where that chord is 6.0 mm, the flat is kept from 4.5 mm and absorbed at 4 mm.
- **Checks run.** `pytest`: **407 passed** and 2 skipped (the OpenSCAD checks; OpenSCAD is not installed in this session). 14 tests are new: 7 in `tests/test_fidelity_math.py` and 7 in `tests/test_sheet_reference.py`. Ruff passed. Ten faults were planted in the new step, one at a time, and each failed at least one test. The browser scenarios, Prettier and `make freecad` were not run; nothing in the frontend changed.
- **Found and not fixed.**
  - A corner whose traced edge wanders from its circle by more than half the tolerance over one chord is still cut up, and its outline stays a polyline as before. Of 18 rendered photos of the test plate with R20 and R25 corners, two still failed: R25 at blurs of 0.47 and 0.55 mm. With R25 corners the plate's Ø6 holes sit 2.2 mm from the corner's edge, and nine of the eleven chords left as lines lie within 3.2 mm of a hole. The same corners without the holes passed at both blurs.
  - A short arc's radius is poorly determined. Strips with a 12° or 15° bend at R45 to R115 came out with both arcs at blurs of 0.22 and 0.34 mm and four rotations, where they had been cut up, but a freely fitted radius was up to 2 mm off. At 0.45 mm one of the two arcs was missing.
  - An arc that meets a straight edge at a sharp corner, as on a half disc, keeps one chord as a short line beside each corner.
  - A straight stretch shorter than `min_line` beside a sharp corner is fitted as an arc with a large residual, and the whole ring then stays a polyline. This is the same before and after the change. It has since been fixed where the stretch is part of a longer straight edge: see "Stubs go back to their edges" above.
- **Not verified.** No real photo. Every figure above is from rendered images, and a real edge's roughness is not modelled: an edge rougher than half the tolerance would leave a large-radius corner cut up as before.

## Fillet radii under blur — November 11, 2026

Branch `claude/fillet-blur`, on top of `claude/drawing-exports` (`ee03d72`). See [reference-sheet tracing](reference-sheet.md), §4, for the mathematics.

- **The defect.** With design-intent snapping on, which is the default, a rounded corner between two straight edges is fitted as a fillet tangent to both. Its radius came out too large by about four times the blur shrink s = σ²/(2R): 0.027 mm on an R8 corner at a 0.34 mm edge blur, 0.053 mm on R4, and 0.16 mm on R2.5 at a 0.46 mm blur. The exported STEP and DXF carried those radii.
- **How it was found.** The photo benchmark's rendered example showed the R8 corners 0.029 mm large with snapping on and 0.008 mm with it off. No earlier test compared a snapped corner's radius with its design.
- **The cause.** A fillet's centre is tied to its radius, and blur moves the traced arc toward the centre without moving the centre. A radius-only fit that ignores the blur settles three shrinks large, and the correction written for free circles added a fourth.
- **The fix.** Fillets are fitted with the blur in their model and are not corrected afterwards. Points within about 2.5 σ of where the arc meets an edge are left out.
- **Reproduced first, then fixed.** On exact geometry the earlier fit leaves fillets 3.7 to 4.0 s large and the new one is within 0.3 s. On rendered, blurred plates the three cases above now read within 0.007 mm. On the benchmark's three rendered photos the R8 row's mean error fell from +0.029 to +0.005 mm (worst from +0.036 to +0.012 mm), and no other row changed.
- **Checks run.** `pytest`: **393 passed** and 2 skipped (the OpenSCAD checks; OpenSCAD is not installed in this session). 7 tests are new: 4 in `tests/test_fidelity_math.py` and 3 in `tests/test_sheet_reference.py`. Five of six faults planted in the fix failed a test; the sixth, a wrong derivative of the shrink, changes only how fast the fit converges on these inputs. Ruff passed. `make freecad` passed, with the plate's corner cylinders at 7.999 mm where they were 8.025 mm (design 8). The two reference-sheet browser scenarios passed with Playwright's bundled Chromium; the others were not re-run locally.
- **Found and not fixed.** A corner of large radius can be cut into short straight pieces. On a rendered 120 mm plate at a 0.34 mm blur, one of four R20 corners was traced as a run of short lines, and the arcs left around it were several millimetres off in radius; the other three corners read within 0.07 mm. At R30 every corner broke up. R16 and smaller were not affected, nor was R20 at a 0.23 mm blur. The tolerance that accepts a stretch as straight grows with the blur, and a 3 mm chord of a large arc can then pass. This is the same before and after this change. It has since been fixed: see "Large-radius corners stay arcs" above.
- **Not verified.** No real photo. Corners other than right angles: the fit handles any angle, and the factor of three was derived and tested for right angles only.

## SVG and 1:1 PDF drawings — November 11, 2026

Branch `claude/drawing-exports`, on top of `claude/photo-benchmark` (`bfaa21e`). See [export formats](exports.md) for their use.

- **What they are.** Every build now also writes the DXF's loops as `profile.svg`, at one user unit per millimetre, and as `drawing.pdf`, a page that prints at 1:1 with a 100 mm ruler along each axis and a centre mark in each round hole (`backend/drawing.py`). Both are written directly, without an SVG or PDF library. The PDF page is 210 × 279.4 mm, the area A4 and US Letter share.
- **Read back by four programs that share no code with the writer**, on the fitted build of the rendered 4 mm plate, whose solid is 120.0175 × 70.0168 mm:
  - Chromium 153 (SVG): outline 120.0175 × 70.0168 mm, slot 23.9797 × 7.9764 mm, bore 21.9749 mm.
  - FreeCAD 1.0.2 (SVG import): the same sizes, and an outline perimeter of 366.2904 mm against 366.2905 from the fitted lines and arcs. FreeCAD's importer turns every edge into a B-spline, so the DXF and STEP remain the route into CAD.
  - MuPDF 1.28.6 (PDF): outline 120.017 × 70.017 mm, bore 21.975 mm, both rulers 100.000 mm.
  - pypdf 7.0.1 in strict mode (PDF): one page of 210.0 × 279.4 mm, the title and the four text lines, with no structural complaint.
- **A defect found by the tests and fixed before any release.** An SVG arc is defined by its end points and radius. For a half turn, such as a slot's end, rounding the end points moved the arc by the square root of the rounding: 0.02 mm at four decimals on a 4 mm slot end. Arcs are now written in pieces of at most a third of a turn, with five decimals, and a test with slots at five angles fails without that.
- **Checks run.** `pytest`: **386 passed** and 2 skipped (the OpenSCAD checks; OpenSCAD is not installed in this session). 21 tests are new: 18 in `tests/test_drawing.py`, which read both files back with parsers written for the tests and compare the enclosed regions with the design, and one each for plain, fitted and split builds through the API. Twenty faults planted one at a time in the writer (a mirrored drawing, a reversed arc, a wrong scale, a wrong page, a wrong ruler, a broken cross-reference table and others) each failed a test. Ruff and Prettier passed. The production build and the 10 browser scenarios of `workbench.spec.ts` and `sheet-reference.spec.ts` passed with Playwright's bundled Chromium, including downloads of both new files; the other scenarios were not re-run locally.
- **Not verified.** No page was printed: this session has no printer. Whether a printer keeps the scale is what the rulers are for. No laser-cutter or vector-editor program other than the two above read the SVG. The PDF names the standard Helvetica font without embedding it, as PDF allows; it was not checked against PDF/A.

## Photo benchmark runner — November 11, 2026

Branch `claude/photo-benchmark`, on top of `claude/phone-photo-decoding` (`bd5dc55`). See [the photo benchmark](photo-benchmark.md) for its use.

- **What it is.** `make photo-benchmark PHOTOS=folder` (`scripts/photo_benchmark.py`) traces a folder of reference-sheet photos with the workbench's own trace function and compares each trace with caliper measurements listed in the folder's `benchmark.json`: outline, hole diameters, non-round openings, radii and distances between hole centres. It reports each dimension's mean error, its spread between readings and its worst reading, and splits each photo's errors into a scale error and an edge offset.
- **No real photo was measured.** No photo taken by a camera and no calipered part was available in this session. The runner is the means to record such a result; none is recorded.
- **Checked against the test suite's own measure.** On three rendered photos of the 4 mm test plate, the runner's worst errors per feature equal those of `tests/synthetic.py`'s `feature_errors` to four decimals (for the 22° photo: Ø6 0.0166, Ø22 0.0251, slot 0.0236, outer 0.0174 mm).
- **On rendered photos** (22°, 9° and 0° tilt, 4 mm thick, design dimensions as the caliper values): 48 dimensions, median absolute error 0.019 mm, 95th percentile 0.036 mm, worst 0.088 mm. The worst is the outline length in the overhead photo, whose trace notes that the walls are too narrow to measure. Distances between hole centres stayed within 0.016 mm in every photo.
- **Two observations from that run.** In the two tilted photos the split gives an edge offset of +0.009 mm with a scale error under 0.001 %, which agrees with the shadow being the main remaining error there. With design-intent snapping on, the R8 corners read 0.029 mm large on average, against 0.008 mm with it off; the cause has not been investigated.
- **Formats.** A folder mixing a JPEG, a PNG and a HEIC of the rendered photos traced all three.
- **Checks run.** `pytest`: **365 passed** and 2 skipped (the OpenSCAD checks; OpenSCAD is not installed in this session). 41 tests are new, in `tests/test_photo_benchmark.py`. Sixteen faults planted one at a time in the runner (a wrong sign, a dropped tolerance, a reused feature, a miscounted miss and others) each failed at least one test. Ruff passed. The browser scenarios were not run locally; no backend or frontend code changed.
- **Not verified.** Real photos, real calipers and real parts. The matching of caliper values to traced features by nearest size has been exercised on one plate design only.

## Phone photos: HEIC, AVIF and up to 70 megapixels — November 11, 2026

Branch `claude/phone-photo-decoding`, on top of `claude/colour-edge-mix` (`3b55fca`).

- **Before.** The tracer accepted PNG, JPEG and WebP up to 10 MiB and 16 megapixels. A 24-megapixel JPEG was refused for its size, and HEIC and AVIF for their format.
- **Formats.** HEIC is decoded by pi-heif 1.4.0 (libheif 1.23.0, libde265 1.1.0). AVIF is decoded by Pillow 13.0.0. Two HEIC fixtures written with pillow-heif 1.8.1 trace like the same pixels saved as JPEG, including a stored rotation, and return the EXIF 35 mm focal length. No photo taken by a phone was available, so an iPhone's tiled HEIC with a gain map or depth image is not verified.
- **A decoder crash, found and contained.** Mutating one or a few bytes of a valid HEIC 150 times produced one segmentation fault in pi-heif while it read metadata; two changed bytes are enough. HEIC is therefore decoded in a child process (`backend/heic.py`). Through that path, 805 mutated or truncated HEIC files gave no crash of the service and no unhandled error. The same mutation of 3005 AVIF files in the service gave no crash; Pillow reported damage as `RuntimeError`, which is now a refusal and not a server error.
- **Size.** Uploads may be 32 MiB and 70 megapixels; other request bodies keep the 10 MiB limit. A reference-sheet photo above 16 megapixels is reduced to 16 by averaging linear light. Over all pixel phases that left a blurred edge's mean position within 0.015 source pixels at 24 and 50 megapixels, where averaging saved values moved it by about 0.04. An 18-megapixel rendered photo traced within 0.01 mm on a 60 mm disc.
- **Checks run.** `pytest`: **324 passed** and 2 skipped (the OpenSCAD checks; OpenSCAD is not installed in this session). Ruff and Prettier passed. The production build and the 15 scenarios of `workbench.spec.ts` and `recovery.spec.ts` passed with Playwright's bundled Chromium, including a new one that uploads a HEIC whose type the browser does not report. The other browser scenarios were not re-run locally.
- **Time and memory.** Rendered reference-sheet photos of 25 megapixels (JPEG and HEIC) and 51 megapixels (JPEG) traced in 8 to 10 seconds with a peak of 0.9 GB in the service, the same peak as a 16-megapixel photo, and 0.4 GB in the HEIC child. Each read a 60 mm disc to about 0.001 mm. These renders are flat colour and compress to under 1 MB; a real photo of that size takes longer to decode.
- **Not verified.** No real phone photo was decoded. The child's memory and processor limits apply on POSIX systems only. The frontend's HEIC acceptance was exercised in Chromium only.


## Edges measured in linear light — November 11, 2026

Branch `claude/linear-light-edges` (from `020c0e2`). See [reference-sheet tracing](reference-sheet.md), §3 and Results, for the method and the re-measured accuracy table.

- **The defect.** The reference-sheet tracer measured edge positions on the photo's saved values. A camera blurs in linear light and then saves through a tone curve, so the mid-level of a blurred edge sat 0.53 σ inside the darker side for the test plate's tones. The synthetic photos could not show it, because `tests/synthetic.py` mixed and blurred tones on the saved scale.
- **Reproduced first.** With the renderer changed to mix light linearly and save through the sRGB curve, the unchanged tracer failed the existing accuracy tests. On the overhead photo it gave 0.263 (Ø6), 0.250 (Ø22), 0.257 (slot) and 0.353 mm (outer), against limits of 0.03 to 0.06 mm.
- **After the change** the tracer decodes the photo as sRGB and measures in linear light. The same photo gives 0.003 mm or less, and every existing accuracy test passes at its unchanged limit.
- **Found in review and fixed in a follow-up** (branch `claude/colour-edge-mix`, from `33c9972`). Measuring on luminance alone lost parts that the tracer could still find: a pure green part on a 220 grey sheet, and a grey sheet on a green table, both traced before this change and failed after it. The change was merged before the fix was pushed. The measurement mix is now chosen per photo, by the contrast it leaves at the boundary's weakest stretch: luminance while that is at least 24 saved grey levels, otherwise the candidate mix with the best weakest stretch. Both cases trace within 0.002 mm on a 60 mm disc. A first version of this fix chose the mix from the part's typical colour; review showed that a part of two colours could then lose the boundary of its smaller colour (a plate read 66 mm wide, not 80, and lost a hole), which the weakest-stretch rule prevents and a test now holds. A yellow part on white paper on a darker table is not found as a sheet's content, before or after; that is unchanged.
- **Checks run.** `pytest`: **313 passed** and 2 skipped (the two OpenSCAD checks; OpenSCAD is not installed in this session). That is the 304 tests before, plus 11 new: 4 in `tests/test_fidelity_math.py` and 7 in `tests/test_sheet_reference.py`. The production build and all **46 browser scenarios** passed with Playwright's bundled Chromium on the first commit, and the two reference-sheet scenarios again after the review fix, after the fixture `tests/e2e/fixtures/plate-on-a4.jpg` was regenerated as `render(thickness=4.0, quality=85)`. Ruff and Prettier passed. `make freecad` passed on the new photo: one valid solid of 8 planes and 11 cylinders, 120.017 × 70.017 × 4.000 mm, radii 2.992, 3.988, 8.025 and 10.987 mm.
- **Shadows are now the main remaining error** in the rendered tilted photos, and are not corrected. In the renderer a shadow now removes a stated share of the light. The test photos' 25 % shadow darkens the saved paper by about 12 %, lighter than the 25 % the earlier renderer applied to saved values; a 47 % shadow reproduces that earlier look and roughly doubles the errors (0.054 mm on Ø22). Both depths are tested.
- **The wall model's benefit depends on the shadow.** Without a shadow it cuts the 9° photo's hole errors about eightfold. With the 25 % shadow and this plate's dark walls, the uncorrected trace reads the holes better, because the wall and shadow biases have opposite signs.
- **Not verified.** No real photo was measured. A real camera's tone mapping on top of the sRGB curve is not modelled by the renderer or undone by the tracer. A plain-gamma camera costs 0.02 mm at 2.2 and 0.11 mm at 1.8 on the overhead photo. The comparison that chose the wall model's 1–3 σ taper, and the hand-cropped rows of the accuracy table, were recorded with the earlier renderer and were not repeated. Tracing without a reference sheet is unchanged and still works on saved values.

## FreeCAD import of fitted exports — November 11, 2026

`make freecad` (new; `scripts/freecad_check.py`) traces and builds the synthetic tilted 4 mm plate photo with the workbench API on `main` at `2c0dc34`, then has FreeCAD 1.0.2 (the official `conda-Linux-x86_64-py311` AppImage, extracted; `FREECADCMD` set to its `freecadcmd`) import the STEP and DXF exports. It closes the "open the fitted STEP/DXF in a CAD package" item left open on #16. The plate's design is 120 × 70 mm with R8 corners, 4 × Ø6 holes, a Ø22 bore and a 24 × 8 slot.

- **STEP:** one valid solid of 8 planes and 11 true cylinders, 119.999 × 70.006 × 4.000 mm. Cylinder radii are 2.996 (×4, design 3), 3.985 (×2, slot ends, design 4), 8.004 (×4, corners, design 8) and 10.987 mm (bore, design 11). The volume is 0.032% above design.
- **DXF**, through FreeCAD's own DXF importer: 6 lines, 6 arcs and 5 circles with the same radii, and no other edge types.
- The check fails on a wrong face type, a radius more than 0.05 mm off, a size more than 0.1 mm off, a volume more than 0.2% off, or a wrong DXF entity count; each case was confirmed with a corrupted report. Without FreeCAD it stops with a message instead of passing.
- FreeCAD shares the OpenCascade kernel with the STEP export, so this shows that a separate CAD application imports the files as exact geometry of the right size; it is not an independent kernel check. The photo is synthetic, and FreeCAD is not installed by setup or run in CI.

## Reference-sheet tracing and mathematical verification — November 10, 2026

Branch `claude/photo-fidelity-phase1` (from `09d2f46`). See [reference-sheet tracing](reference-sheet.md) for the method and the accuracy table.

- `PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/google-chrome ./scripts/test.sh` passed twice: production typecheck/build and **46 Chrome browser scenarios** (44 before, plus 2 in `tests/e2e/sheet-reference.spec.ts`), with no failures or skips. The final code then passed **300 Python tests** (237 before, plus 63 new: 37 in `tests/test_sheet_reference.py` and 26 in `tests/test_fidelity_math.py`) and a rerun of the sheet, workbench and recovery browser specs (16 scenarios) after the last backend change, which turned unexpected reference-trace failures into recoverable 422 responses. `make lint` passed Ruff and Prettier.
- Six hostile inputs (blank, noise, a 20-pixel image, an empty sheet, stripes, and a part over the sheet edge) each return a specific, recoverable message instead of a server error.
- The new browser scenarios trace a rendered tilted phone photo of a 4 mm plate on an A4 sheet. They check the width taken from the sheet, a single thickness-correcting re-trace on build, export dimensions 120 × 70 × 4 mm within 0.1 mm, 11 cylindrical STEP faces, DXF `ARC`/`CIRCLE` entities without polylines, 5 OpenSCAD `circle()` calls, a version 3 project, an accessibility scan of the photo dialog, the sheet-proportions warning for a wrongly chosen US Letter sheet, and switching the reference in the outline dialog.
- Mathematical verification found and fixed four defects before any accuracy figure was recorded:
  - the fixed-point lens inverse, 4.6 px wrong at the image corners for k₁ = −0.25 (now Newton's method, ≤ 1.4 × 10⁻¹² px);
  - `cv2.remap`'s 1/32-pixel position quantisation, up to 0.086 px in the measurement image (now exact float64 cubic resampling);
  - an off-centre first edge pass that grew holes by about 0.09 px (now two passes);
  - a test-renderer compositing error that biased every synthetic edge by about 0.017 mm.
- The two-step wall model was kept only in the range where it improved results. Over 0.25–4 σ it made the 22° thick photo worse (Ø6 0.021 against 0.010 mm without it). The tapered 1–3 σ range improved every feature at 9° tilt and four of five at 22°.
- These are synthetic photographs; no real photo, physical part, slicer or print was measured.

## Bambu Studio and PrusaSlicer handoff — November 9, 2026

The workbench exports neutral 3MF geometry and tailored handoff ZIPs for Bambu Studio 2.9.1 and the requested PrusaSlicer 2.9.7. Optional direct opening uses fixed installed executables and a retained local model copy. Neither slicer is installed or launched by setup or the checks below.

- `PICAD_TEST_URL=http://127.0.0.1:18001 make test-app` passed: **237 Python tests**, production typecheck/build, and **39 Chrome browser scenarios**, with no failures or skips. `make lint` passed Ruff and Prettier. After the final cleanup-copy and development-proxy fixes, the production build, all **12 slicer/workbench browser scenarios**, and lint passed again.
- Independent 3MF readers verified package relationships, millimetre units, object/build references, per-object dimensions, closed and consistently oriented meshes, hole topology and volume against the final CAD solids. Combined split objects retain assembly coordinates; individual part files start at XY zero and bottom Z zero. Every archived payload hash and referenced filename was checked.
- Browser checks downloaded real 3MF and both handoff ZIPs, preserved the selected printer/material plan, required an explicit native-open click, recovered from status/launch failures, blocked stale geometry downloads, and exercised selection, keyboard and selected axe A/AA rules at a 390-pixel viewport. Native discovery/launch replies in browser tests were fixtures; geometry and downloads used the real CAD service.
- Launcher tests used mocked processes to verify fixed arguments without a shell, retained copies, disabled/missing-program states, arbitrary-path/argument rejection, same-origin loopback restrictions, attempt cooldown and repeated request cancellation. Independent review found and corrected a development proxy Host rewrite and inaccurate cleanup wording. A real Vite proxy check accepted the local origin through to model lookup and rejected a cross-origin request with 403, without launching any software.
- The refreshed local service passed the sample smoke check. Read-only status reported neither requested slicer executable available and direct opening disabled. The original browser project was saved locally before refreshing the service; its open tab was preserved and its recipe restored in a separate preview tab.

This run used Python 3.12.3, Node.js 22.13.1 and Google Chrome 157.0.8103.50. Native Bambu Studio/PrusaSlicer import, installed-version verification, slicing and physical printing remain unverified. These are software and synthetic-geometry results; they do not establish material suitability, physical dimensions, fit or strength. Reference-library source and dependencies did not change. Remote CI results belong to the new revision.

## Repository and OpenSCAD integration — November 9, 2026

The full repository workbench now includes OpenSCAD source export and opens the preserved Revision 7 companion workspace from its header. The app serves published companion files on the same origin through an explicit allowlist; local build outputs, environments, and scratch files remain outside that route.

- `make test-app` passed: **202 Python tests**, production typecheck/build, and **34 Chrome browser scenarios**, with no failures or skips. The Python suite completed in 21.95 seconds and the browser scenarios in 2.9 minutes. `make lint` passed Ruff and Prettier checks.
- Native OpenSCAD rendered exported source for scaled and simplified profiles containing two through-holes, both as a single part and as a split assembly. The library's independent mesh checker confirmed closed, manifold, consistently oriented meshes, matching CAD bounds and volume, and the expected hole topology. Both selected split pieces also matched their CAD dimensions and volume. These tests use the final prepared polygons and effective thickness rather than the source-image outline or unscaled inputs.
- Browser checks downloaded the new `.scad` source through the export dialog and opened `/reference-library/index.html#cad` in a separate tab while the original model and its download remained available. Existing measurement, design, assistant, recovery, accessibility, and mobile scenarios also passed. The refreshed workbench screenshot was visually reviewed.
- Route checks served the bundled public handbook, drawing, worksheet, SCAD example, and PDF, and rejected private directories, personal output paths, traversal, null-byte paths, and an allowlisted symlink escaping the library.

This run used Python 3.12.3, Node.js 22.13.1, OpenSCAD 2021.01, and Google Chrome 157.0.8103.50. The tests used synthetic geometry and generated imagery; no personal source photo was used, and no part was sliced, printed, or physically qualified for dimensions, fit, or strength. This is local evidence; remote CI results belong to the new revision. The companion's separate verification record covers its own library, browser, and native-build checks.

## Measured-feature scale and recovery improvements — November 9, 2026

The workbench now supports an explicitly applied two-point reference in the orientation-adjusted working image, alongside manual outside-width entry. An optional independent outside-height comparison stays separate from XY design scaling. Version 2 recipes retain validated endpoint/length/frame notes and the optional check without embedding a photograph.

- `PICAD_TEST_URL=http://127.0.0.1:18000 make test-app` passed: **180 Python tests**, production typecheck/build, and **33 Chromium browser scenarios**, with no failures or skips. `make lint` passed. Dependencies and lockfiles did not change.
- The ten added browser scenarios verify real CAD dimensions, inch conversion, save/restore started in inches, held-out height comparison before design scaling, blank checks, invalid drafts/imports, manual width overrides, same-frame and changed-frame retracing, failed-retrace retention, fixture-assisted retrace/Undo, and printer-search recovery on desktop and mobile.
- The endpoint checks include a 3–4–5 diagonal and reversed endpoints, draft edits that do not change applied scale, and independent mobile touch-to-image mapping at device pixel ratio 2. The expanded measurement tools pass the selected axe WCAG A/AA rules at a 390-pixel phone viewport with no horizontal overflow. Complete screen-reader, cross-browser, and device-lab qualification remain outside this run.
- Damaged PNG compressed-data chunks now return a recoverable HTTP 422 instead of an uncaught decoder error. A regression checks rejection followed by a successful valid trace.
- Personal source photos, private project folders and local model providers were not used. Assistant answers and deliberately changed trace frames in lifecycle checks are fixtures; geometry builds and exports use the real local CAD service.
- The reference-library files are unchanged in this update. Its separate release and CI evidence remain attached to Revision 6 / pull request #9; this workbench run does not replace those results.

The run used Python 3.12.14, Node.js 22.13.1 and the system Chrome fallback. These are software and synthetic geometry checks. No physical part was sliced or printed, and the endpoint/height tools do not establish metrology accuracy, fit or manufacturing acceptance. GitHub CI results belong to this update's pull request.

## Review fixes: recovery, tracing accuracy, and input checks

Separate code reviews of the backend, frontend, and reference library found 30 defects. This change set fixes them, removes the warnings from CI and the test runs, and adds a regression test for every code fix. The run below used the local workstation: Python 3.12.3, Node.js 22.13.1, Google Chrome 157.0.8103.38 through the system-Chrome fallback, and OpenSCAD 2021.01.

- **CI and build.** Both workflows use the Node 24 releases of their actions (v7 of `checkout`, `setup-python`, `setup-node`, and `upload-artifact`), run on `ubuntu-26.04`, and run once per pull-request push instead of twice. The tests and smoke check use `httpx2`, which Starlette's test client now expects. The production build puts three.js (1,003 kB, 272 kB gzip) and the other libraries (289 kB) in their own chunks, apart from the application's 76 kB. The development server binds to loopback by default, as `dev.sh` already did.
- **Frontend (10 fixes).**
  - **Try again** repeats only the failed step, using the inputs on screen. Before, an error with no retry of its own replayed an earlier step and could silently restore old dimensions and design settings.
  - A failed retrace no longer marks the model outdated.
  - An AI answer no longer takes focus from a field being edited.
  - Focus returns to the control that started busy work.
  - Undoing a suggestion that was never built keeps the model current.
  - Unit switching converts out-of-range entries.
  - Restored project names are cleaned like typed ones.
  - The outline toggle is disabled without a photo.
  - Printer profiles that describe one bed are not reported as ambiguous.
  - Leaving or reloading the page releases its temporary model files.
- **Backend (12 fixes).**
  - Malformed EXIF no longer returns HTTP 500.
  - Camera MPO JPEGs and 16-bit grayscale PNGs trace.
  - A speck inside a hole is ignored like a tiny hole.
  - Outlines now follow pixel edges, not boundary-pixel centres. The old tracing made outer spans 1 px short and holes 1 px large; a 51 px hole in a 401 px part was 2.2 % oversize. The sample is now 34.05 mm tall at 80 mm wide (previously 34.01 mm).
  - Negated wording such as "don't change the thickness" no longer authorizes a size proposal.
  - Expiry deletes only directories holding this application's job files, and it survives a failed pass.
  - Null bytes in frontend paths return 404.
  - Job files use explicit UTF-8.
  - Each hole ring is bounded before parsing.
  - The traversal test now reaches the download route.
  - The benchmark's dimension hint judges the model's raw proposal.
- **Workbench results.** `make test-app` passed with **179 Python tests** (146 before), production typecheck/build, and **23 Chromium browser scenarios** (15 before). The backend tests produced no warnings. `make lint` passed. `scripts/smoke.py` passed against the running service.
- **Regression checks.** 27 new or changed backend tests and 9 browser scenarios failed on the previous code. The strengthened traversal test passes on both versions, because that route was already safe.
- **Reference library (8 fixes; see its [changelog](../reference-library/CHANGELOG.md)).** `make release` passed over `file://` with **157 Python tests**, **25 Node test groups**, **101 page assertions**, **49 Photos assertions**, and **16/16** plate checks. `make test-library` passed the same counts over loopback HTTP.

HawkScan was not run because no `HAWK_API_KEY` is configured. These are software and geometry checks of synthetic fixtures; no part was sliced or printed. The CI results for this change set belong to its pull request.

## Reference library Photos fix: blob-URL race

After Revision 4 merged, both library CI runs failed. The Photos check's final assertion found two "Not allowed to load local resource: blob:null/…" console errors. The same failure appeared locally in about 1 run in 4, and in 1 of 20 instrumented runs, always as a filtered gallery refreshed. The gallery revoked its previous thumbnails' object URLs while those images still referenced them, so a lazy load that started late requested a revoked URL. The fix creates URLs only for the gallery actually shown and detaches old thumbnails before revoking. A new deterministic assertion (49 in total) fails on the previous code and passes now. The library and workbench results for this fix are in its pull request and the library's [verification record](../reference-library/VERIFICATION.md).

## Reference library Revision 4: Photos workspace

This change set adds the library's offline Photos workspace (Revision 4). It shares the browser checks' loopback server so the Photos check runs over both transports, and it keeps `reference-library/.venv` out of the library archive. The workbench code is unchanged. The run below used the same workstation and tools as the section that follows.

- Root commands: `make setup-library` completed, then `make test-library` passed. It ran **129 Python tests** and **22 Node test groups**, then **99 page assertions** and **48 Photos assertions** over loopback HTTP.
- Library: `make release` passed with both browser checks over `file://` (99 and 48 assertions) and **16/16** plate checks after an OpenSCAD render. Two PDF, HTML, and archive builds were each byte-identical, and ReportLab 4.4.9 and 4.5.1 produced the same PDF.
- Workbench: **146 Python tests** and `make lint` passed. The Chromium scenarios were not rerun because no workbench code changed.

The Photos checks use generated images in fresh browser contexts. They do not establish that a particular browser keeps photos for a `file://` page, and they are not a reconstruction or accuracy benchmark.

## Mesh interoperability and library review fixes

This change set addresses the automated review findings on the reference library's STL checker and homography calculator. It also adds `tests/test_mesh_interop.py`, which runs the library's independent STL checker on workbench exports. The run below used the local Linux workstation: Python 3.12.3, Node.js 22.13.1, uv 0.11.16, Google Chrome 157.0.8103.38 through `PLAYWRIGHT_CHROMIUM_EXECUTABLE`, and OpenSCAD 2021.01.

- Workbench: `./scripts/test.sh` passed with **146 Python tests** (the previous 142 plus 4 interoperability tests), production typecheck/build, and **15 Chromium browser scenarios**. `make lint` passed.
- Interoperability: the combined STL, an STL built from a traced photograph with two round holes, and both pieces of a 2 × 1 split bundle are closed, manifold, consistently oriented, and outward-facing. Each has one component and one genus per hole. Their volumes are within 0.01 % of the CAD solid, and split pieces start at the origin. The documented `python3 -m cadkit meshcheck … --expect-mm 80` command exits 0 on a workbench export.
- Reference library: `make release` passed with **129 Python tests**, **12 Node test groups**, **98 browser assertions** over `file://`, and **16/16** plate checks after an OpenSCAD render. The same 98 assertions also passed over loopback HTTP. Regenerated HTML matched the committed file, and the PDF matched its recorded SHA-256.

These are software and geometry checks of synthetic fixtures. They do not establish dimensional accuracy for an arbitrary photograph, and no part was sliced or printed. The CI results for this change set belong to its pull request.

## Repository command integration

The root Makefile exposes setup, build, test, and lint commands for the workbench and reference library while preserving each component's existing entry points. The combined `make setup` completed successfully. `PICAD_TEST_URL=http://127.0.0.1:8001 make test` then passed against an isolated workbench instance:

- Workbench: **142 Python tests**, production typecheck/build, and **15 Chromium browser scenarios**.
- Reference library: **119 Python tests**, **11 Node tests**, and **98 browser assertions** over loopback HTTP.

There were no failed or skipped tests in that completed run. `make lint`, shell and JavaScript syntax checks, and documentation file-link checks also passed. The library HTTP server closed after both a successful check and a deliberately failed browser launch. Interpreter paths containing spaces were checked through the library Makefile. No generated library content or dependency versions changed.

Direct library browser checks retain the `file://` default. This managed browser blocks that transport; the local pass above establishes HTTP behavior. The library CI checks both transports. Remote results below apply only to their named commits.

## Current design, print and assistant changes

The complete `PICAD_TEST_URL=http://127.0.0.1:8001 ./scripts/test.sh` run passed against an isolated instance of the design, print, and assistant implementation: **142 Python tests**, production typecheck/build, and **15 Chromium browser scenarios**, with no failures or skips.

The Python checks comprise 34 original CAD/API tests, 26 real geometry/printing tests, 6 printer-catalog tests, 69 assistant tests, and 7 benchmark tests. The browser run includes the original six workflows, five assistant-control scenarios, and four design/print scenarios.

Additional verified behavior:

- XY/thickness design scales change real STEP/STL geometry while preserving measured source inputs. Split solids are distinct pieces, preserve total volume, and match their preview meshes and ZIP manifest.
- Nozzle-relative simplification changes the actual CAD/DXF outline and retains holes. Printer checks use the exact matching nozzle profile, mark ambiguous/shaped/excluded beds unverified, and check margins, height, and 90-degree rotation.
- Version 2 saves restore design and appearance; version 1 imports still work. Invalid oversized recipes preserve the current project, and backend-normalized printer dimensions reach the interface and resaved recipe.
- Apply is explicit. Undo after a completed AI-assisted build restores the prior actual preview and settings; exports stay stale until a correct rebuild. Manual edits invalidate old proposals; stopped waits ignore late answers.
- Actual split meshes support assembled/separated inspection without changing downloaded ZIP bytes. A real WebGL context loss recovers through Retry. A retired-canvas event regression was found and fixed before this passing run.
- The expanded controls pass the selected axe-core checks on a 390 px viewport. Printer search tolerates punctuation and spacing. These checks are not a claim of complete accessibility conformance.
- The catalog contains 429 model groups, 70 manufacturer/profile families, and 1,106 nozzle profiles. Two imports of the pinned source produced identical bytes; three familiar models were independently checked against their inheritance chains. Unknown hardware capabilities remain unknown.

Ruff, touched frontend/browser-source Prettier checks, shell syntax, and local documentation links pass. The new printer data is fetched only when the design panel opens. No model weights or Ollama binaries are committed or downloaded in CI.

## Original CAD release: local results

| Check | Observed result |
| --- | --- |
| `./scripts/setup.sh` | Passed. Reused the Python environment, performed a frozen uv sync and clean npm install, and built the frontend successfully. |
| `./scripts/test.sh` | Passed: 34 backend tests, production typecheck/build, and 6 Chromium browser tests. No failed or skipped tests in that completed run. |
| Mobile typography follow-up | The affected keyboard/accessibility/mobile scenario passed again after the final helper-text adjustment. |
| Python lint and shell syntax | Ruff and `bash -n` passed for the application, backend tests, smoke helper, and shell scripts. |
| Frontend formatting | Prettier check passed for TypeScript, TSX, CSS, HTML, and browser-test/configuration files. |
| Package advisory check | `npm audit` reported zero known advisories at the time of this check, including development dependencies. |
| Running development service | The smoke helper passed through the Vite proxy on port 4173: served interface, traced sample, built solid, and downloaded STEP. |
| Visual comparison | [Passed](../design-qa.md), with paired source/implementation evidence and desktop/mobile captures. |

## Optional local assistant

The assistant uses the deterministic tracing and CAD pipeline. Proposals require user review; measured width and thickness are never proposal fields. Explicit design percentages can resize the resulting geometry.

- The 69 assistant checks and 7 benchmark-report checks are included in the complete 142-test run above. They use a local test HTTP daemon or explicit fixtures and do not measure an LLM's quality.
- The assistant checks cover loopback-only connections, rejected remote URLs and cloud aliases, unavailable/empty model lists, no automatic pulls, bounded context, discarded invalid or dimensional proposals, malformed output, timeout recovery, and the cancellation/concurrency boundary.
- Ruff passed across `backend`, `scripts`, and `tests`; the Ollama shell helper passed syntax checks and a verified-install run. Frontend type checking/build and touched-source Prettier checks passed.
- The actual **Ollama 0.40.15** runtime downloaded from its official GitHub release, matched SHA-256 `628c018404a4206493efd38e46251c154ede5141b8b8dc85c659b3b027c47379`, and started on `127.0.0.1:11434` with `OLLAMA_NO_CLOUD=1`.
- Live API checks reported the runtime version and an empty model list. The CAD backend correctly reported Ollama running with no models and returned HTTP 409 for an uninstalled model without changing CAD state.
- The actual `qwen3:1.7b` pull failed at the model manifest because the managed proxy denied `registry.ollama.ai`. The [recorded comparison preflight](benchmarks/ollama-preflight.json) found all three shortlisted models missing and attempted **zero inferences**. Model weights, answer quality, memory use, and inference speed remain unverified.

The model shortlist is provisional. See [local AI setup](ollama.md) and [model research](ollama-models.md). Network draft changes must be applied before downloading and comparing the candidates; integration fixtures are not substitutes for that test.

## GitHub-hosted CI

Both workflows completed with **Success** for merge commit `5d6a446d6175e4ad1bd0c01c0166b05e0d1e393a`:

| Workflow | Recorded run | Scope |
| --- | --- | --- |
| Validate workbench | [42528803054](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/42528803054) | Locked workbench setup/build, Chromium installation, Ruff, Python and browser workflow checks |
| Validate reference library | [42528803055](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/42528803055) | Library regeneration and drift checks, Python/Node tests, required OpenSCAD plate pipeline, and browser checks |

These runs use `ubuntu-latest`, Python 3.12, and Node.js 24. They validate that exact merge commit. They do not validate later repository-command or browser-transport changes before those changes receive their own completed runs.

Earlier workbench evidence remains available: the [feature run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/42528243229) passed for `f4b924517c6f58fe34686f380c478e55ba67d4ef`; the [original CAD run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/42519068333) passed for `96d73c6ef1b6ee50759f1835e63717835772b4f1`.

The library has a separate [verification record](../reference-library/VERIFICATION.md) describing its 157 Python tests, 25 Node test groups, and browser assertions. Those checks are additional to the workbench's 179 Python tests and 23 browser scenarios; they do not evaluate real photograph reconstruction, physical printing, or LLM quality. Counts, skips, and browser transport belong to the particular recorded invocation rather than the mere presence of a test command.

## Geometry and API evidence

The synthetic reference profile is 100 × 60 units with two 10 × 10 square holes. Scaling to 80 mm width and extruding 4 mm produces an 80 × 48 × 4 mm solid with expected volume **14,848 mm³**.

The backend suite verifies:

- Correct dimensions, positive volume, expected hole count, and matching settings revision.
- STEP re-import as one valid solid with the expected dimensions and volume.
- Binary STL structure, expected bounds, and exactly two incident triangles at every welded mesh edge.
- Independent STL checks by the reference library's `cadkit` (see above): closure, vertex manifoldness, orientation, one component, and one genus per hole for combined, traced, and split exports.
- DXF millimeter units and three closed profile rings for the two-hole fixture.
- Reproducible project-recipe content.
- Trace hierarchy, foreground inversion, EXIF orientation, and removal of source metadata from the normalized display image.
- Invalid image data, empty/edge-clipped images, upload and decoded-pixel limits.
- Nonfinite/invalid dimensions, invalid or intersecting profiles, invalid download paths, expiry, and deletion.
- CAD timeout cleanup, storage-capacity preservation, one-at-a-time image tracing, repeated request cancellation, and cleanup protection during active CAD work.

These fixtures establish software behavior under their stated conditions. They do not establish a dimensional accuracy guarantee for arbitrary photographs or replace physical measurement.

## Browser evidence

The original six scenarios below also passed in the complete 15-scenario run against the current built application:

1. Trace the supplied sample, render the actual solid, and download STEP, STL, and DXF files with format checks.
2. Change thickness, invalidate old exports, rebuild, switch display units without altering physical size, save a recipe, and restore/rebuild it.
3. Upload a photo, require measured dimensions, build a part, and preserve the prior valid result after a malformed upload.
4. Check keyboard dialog opening/closing and focus restoration, run axe-core A/AA rules on the workbench, and operate the export dialog at a 390 px mobile width without horizontal overflow.
5. Remove the current server artifact, surface its failed download in the UI without downloading an error file, and rebuild successfully.
6. Clear temporary exports through the interface, retain editable dimensions and outline, and build again.

The sample scenario recorded no JavaScript page exceptions or browser console errors. Expected failed HTTP requests in negative scenarios were checked as recovery behavior. The workbench returned zero violations in the selected axe-core rules. Complete screen-reader, cross-browser, and device-lab testing remain outside this run.

The final mobile typography change was followed by a passing rerun of scenario 4 against the development server. The local HTML Playwright report reflects the most recent local invocation. The GitHub workflow retains its own browser reports and failure traces according to its seven-day artifact policy.

## Runtime and reproducibility

- Tested runtime: Python 3.12.14, Node.js 24.22.1, npm 11.9.0, uv 0.13.5.
- Dependencies are recorded in `uv.lock` and `package-lock.json`; setup preserves both locks.
- Python is restricted to 3.12 because the selected CAD binary stack includes VTK 9.3.1 wheels through CPython 3.12. The project does not claim Python 3.13 support.
- The local machine already provided uv. The setup script's uv-absent bootstrap branch was not separately exercised in the local validation run.
- The service uses one API process and bounded CAD subprocesses. No GPU or third-party reconstruction API was required.
- A development startup and shutdown were exercised; the final single-service startup serves the built interface and API together.
- The Sites preview relay was unavailable. Actual Chromium against the application provided browser evidence; there is no published site or user-facing hosted preview.

## Remaining notices and limits

The build and backend tests run without warnings. The 3D stack is still the largest download: three.js is a 1,003 kB chunk (272 kB gzip) that loads with the page because the preview is on the first screen. The build's chunk-size limit sits just above it, so unexpected growth still warns. In the browser console, React Three Fiber 9.8.2 logs a `THREE.Clock` deprecation warning. It comes from the library, not this application, and only its version 10 pre-releases change it. Renderer dependency warnings are distinct from application console errors.

This is a working single-user, constant-thickness profile workbench. It has no public-service authentication, collaborative project database, arbitrary-object reconstruction, manufacturing certification, or validated metrology. See [scope](roadmap.md), [capture guidance](capture-guide.md), and [data handling](privacy-security.md).

## Independent height decision

The [engineering check](engineering-model.md) uses explicit user-entered bounds and a strict interval decision. [Audit and verification](validation/engineering-audit.md) records the scope, baseline finding, arithmetic oracle, recipe/state checks and browser evidence. This is synthetic software evidence; physical accuracy remains unqualified.
