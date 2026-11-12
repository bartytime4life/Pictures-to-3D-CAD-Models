# Photo benchmark: your photos against your calipers

Every accuracy figure in this repository so far comes from rendered photographs. `make photo-benchmark` measures the reference-sheet tracer on real ones: you photograph parts you have measured, list those measurements in a small file, and it reports how far each traced dimension lies from your calipers and how much it moves between repeat shots.

**No result from real photos is recorded yet.** The example report below comes from rendered photos and shows the format only.

Everything runs on your computer. Each photo uses the workbench's reference-sheet trace function with the sheet, thickness and snapping settings specified here. The benchmark requires a successful sheet trace; it does not use the initial upload dialog's fallback to ordinary tracing when a sheet cannot be found.

The report counts every requested dimension, including those unavailable when
a photo fails. Error statistics still cover matched dimensions only. Size
correspondence first maximizes admitted match count, then minimizes total size
error within the unchanged gates. Read the [coverage and matching limits](#coverage-and-matching-limits)
before interpreting a small reported error as overall performance.

This guide describes the global matcher and coverage fields merged in
[PR #43](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/43)
at `d6a657f`. The [correspondence record](validation/benchmark-correspondence.md)
separates earlier and integrated checks; older checkouts can still produce the
previous report schema and greedy assignments.

## What you need

- One or more flat parts of constant thickness, each with a few dimensions you can measure well.
- Calipers, and a steel rule for the sheet.
- A sheet of A4 or US Letter paper, or any flat rectangular sheet you have measured.
- The camera you normally use. HEIC, JPEG, PNG, WebP and AVIF are read.

## 1. Measure the sheet

The sheet's stated size sets the scale of every traced dimension. ISO 216 allows ±2 mm on A4's long side, about 0.7 %, which is 0.8 mm on a 120 mm part. Measure both sides with a steel rule. If they differ from the nominal size, enter them as `"sheet": [width, height]`.

## 2. Measure each part

Measure each dimension three times and enter the mean. The file takes five kinds of measurement, all in millimetres. Use the ones your part has.

| Kind | What to measure | How the trace measures it |
| --- | --- | --- |
| `outline` | The part's length and width across its parallel sides: `[120.02, 70.01]` | The sides of the smallest rectangle that encloses the outline |
| `diameters` | Each round hole, and a round part's outside | Each boundary the trace fitted as one circle |
| `openings` | Length and width of each hole that is not round, such as a slot: `[[24.0, 8.0]]` | The smallest rectangle that encloses the hole |
| `radii` | Corner and fillet radii, from a radius gauge | The radius of each fitted arc |
| `centre_distances` | The distance between the centres of two round holes | The distance between the centres of the fitted circles |

For a centre distance, measure the gap between the two holes' near edges and the span across their far edges, and enter the mean of the two. The hole diameters cancel.

Enter a repeated feature once per feature: four 6 mm holes are `[6.0, 6.0, 6.0, 6.0]`. If you measured them individually and they differ, enter the four values.

## 3. Take the photos

Follow [the capture guide](capture-guide.md#photograph-the-part-on-a-reference-sheet): the whole sheet in view, a contrasting surface around it, diffuse light, the photo as the camera saved it.

Take at least three shots of each part, and pick the part up and put it down between shots. Record tilt, light, distance, phone and processing settings outside the manifest; the runner has no fields for these conditions. Keep each condition in a separately named part entry.

Changing one factor at a time can help diagnose an obvious problem, but it does
not test interactions. For a small planned study, cross two modest tilts with
two lighting conditions and repeat each combination, keeping part, distance and
phone fixed. Choose the settings and evaluation dimensions before adjusting the
algorithm, vary capture order, and reserve fresh views and dimensions for a
final check. This is a proposed study, not a completed experiment or a powered
accuracy qualification. [NIST's experimental-design guidance](https://www.itl.nist.gov/div898/handbook/pri/section2/pri212.htm)
explains why one-factor studies miss interactions.

## 4. Write `benchmark.json`

Put the photos in one folder with a `benchmark.json` beside them:

```json
{
  "sheet": [209.8, 297.1],
  "caliper_uncertainty_mm": 0.03,
  "parts": [
    {
      "name": "bracket, overhead",
      "photos": ["bracket-overhead-*.jpg"],
      "thickness_mm": 4.02,
      "measured": {
        "outline": [120.02, 70.01],
        "diameters": [22.01, 6.02, 6.01, 6.03, 6.02],
        "openings": [[24.0, 8.02]],
        "radii": [8, 8, 8, 8],
        "centre_distances": [96.01, 50.0]
      }
    }
  ]
}
```

| Setting | Meaning |
| --- | --- |
| `sheet` | `"a4"` (the default), `"letter"`, or the sheet's measured `[width, height]`. A part may carry its own `sheet`. |
| `caliper_uncertainty_mm` | A numeric comparison threshold above 0 and at most 5 mm; 0.03 if left out. Mean errors beyond it are printed in bold. Record separately whether your entered specification is an accuracy limit, absolute bound or standard uncertainty. The runner does not distinguish them or propagate a measurement uncertainty budget. |
| `name` | A label for the report. Parts need different names. |
| `photos` | File names or patterns, relative to the folder. |
| `thickness_mm` | The part's thickness. With it, the trace removes the visible side walls, as **Build** does in the workbench. Leave it out for a part thin enough to ignore. |
| `light_part` | `true` for a light part on a dark sheet. |
| `measured` | The measurements of step 2. |

A misspelt setting is refused by name, so a typing error cannot silently drop a measurement. Each measurement kind accepts at most **128 features per part**; an opening pair is one feature with two scalar dimensions. Matching also limits each kind to **2048 detected candidates** and **131072 expected-candidate pairs**. Exceeding a work limit stops the command with an explanation before matching costs are evaluated; it does not silently discard candidates. Split a large measurement list into smaller, separately named part entries, or simplify the outline.

The generated report labels this field a display threshold. It is not a
statistical decision rule: no coverage factor, calibration contribution or
reference-measurement model is evaluated. Keep the instrument specification and
measurement procedure with your study. [NIST's terminology](https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-appendix-d1-terminology)
distinguishes accuracy, uncertainty and repeatability.

## 5. Run it

```bash
make photo-benchmark PHOTOS=path/to/folder
```

or, with options:

```bash
.venv/bin/python scripts/photo_benchmark.py path/to/folder --json report.json --markdown report.md
```

- `--json FILE` saves every reading, each photo's trace notes and fits, and complete dimension coverage at photo, part and summary levels.
- `--markdown FILE` saves the printed tables.
- `--no-snap` traces without design-intent snapping. With snapping on, as in the workbench, near-equal radii are made equal and straight edges are squared, so four equal holes share one reading per photo.
- `--example FOLDER` writes three rendered photos and a `benchmark.json` to copy from. It takes about half a minute.

A trace takes a few seconds per photo. The command exits with an error when the manifest cannot be used, a correspondence work limit is exceeded, or no photo could be traced. A successful exit is not a dimensional-accuracy or manufacturing-acceptance decision.

## 6. Read the report

This report is the `--example` folder: three **rendered** photos of the test plate at 22°, 9° and 0° tilt, 4 mm thick, with its design dimensions as the caliper values.

> 3 of 3 photos traced.
> Dimensions: 48 of 48 requested compared; 0 unmatched in successful traces; 0 unavailable in failed traces.
> Matched dimensions only: absolute error median 0.004 mm, 95th percentile 0.015 mm, worst 0.015 mm.

| Dimension | Reference (mm) | Readings | Mean error (mm) | Spread, SD (mm) | Worst (mm) | Unmatched |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Outline length | 120.00 | 3 | +0.007 | 0.007 | +0.015 |  |
| Outline width | 70.00 | 3 | +0.003 | 0.009 | +0.011 |  |
| Ø22 | 22.00 | 3 | -0.002 | 0.005 | -0.005 |  |
| Ø6 (×4) | 6.00 | 12 | -0.003 | 0.001 | -0.004 |  |
| Opening 24 × 8 length | 24.00 | 3 | -0.004 | 0.009 | -0.015 |  |
| Opening 24 × 8 width | 8.00 | 3 | -0.005 | 0.009 | -0.015 |  |
| R8 (×4) | 8.00 | 12 | -0.003 | 0.009 | -0.015 |  |
| Centres 96 | 96.00 | 3 | +0.003 | 0.006 | +0.007 |  |
| Centres 50 | 50.00 | 3 | +0.001 | 0.003 | +0.005 |  |
| Centres 108.24 | 108.24 | 3 | +0.003 | 0.008 | +0.011 |  |

> Fitted scale term +0.002 % (SD 0.007 between photos); edge term +0.002 mm (SD 0.001 between photos), positive when boundaries are found outside the material. In-sample residual: 0.003 mm RMS. These diagnostic terms do not identify physical causes or predict held-out error.

| Photo | Edge blur (mm) | Sheet proportions (%) | Worst error (mm) | Result |
| --- | ---: | ---: | ---: | --- |
| plate-1.jpg | 0.320 | 0.00 | -0.015 | Traced |
| plate-2.jpg | 0.303 | 0.00 | -0.015 | Traced |
| plate-3.jpg | 0.294 | 0.00 | +0.015 | Traced |

**The dimension table.** An error is the traced value minus your caliper value.

- **Mean error** is the observed mean signed error for the matched samples. A small study does not establish the population bias or show which physical effect caused it.
- **Spread** is the sample standard deviation of the row's errors. For one identifiable feature it describes the observed repeat-shot spread. For a row of several equal features (×4) it also includes differences between them; snapping and common calibration can correlate the readings. Twelve readings of four holes in three photos are not twelve independent captures.
- **Worst** is the largest single error, with its sign.
- **Unmatched** counts expected scalar dimensions without an admitted match in a successful trace. The size gate is 1 mm or 15% of the expected dimension, whichever is larger. Both sides of an outline/opening pair must pass. A missing circle, or a hole described as a non-circular opening, can land here. Dimensions from completely failed traces are counted separately as **unavailable**.

**Fitted scale term and edge term.** Least squares fits a two-term diagnostic to each photo's matched errors:

- The **scale term** changes every dimension in proportion to its size. A wrong sheet size or perspective error could produce this pattern, but the fit does not identify the cause.
- The **edge term** grows outside dimensions and shrinks holes by twice the offset, and leaves centre distances alone. Blur, shadow, tone mapping or non-vertical walls could contribute to this pattern.

The line gives their mean over the part's photos and their spread between photos. Radii take no part. The split is made only when a photo holds at least four dimensions that can separate the two: a mix of sizes, or of outside dimensions, holes and centre distances.

The unexplained RMS is evaluated on the same samples used to fit these terms.
It is an in-sample residual, not an independent prediction error or proof that
the two terms capture all physical causes.

**The photo table** shows which shot is the odd one out. In the example none is: every photo's worst error is about 0.015 mm. The trace notes, in the JSON report, still say what each photo relied on. In the overhead photo neither the sheet nor the metadata gave the focal length, so it was estimated from the holes' roundness. Without suitable round holes a typical phone lens is assumed, and a wrong camera height scales the top face's edges by the wrong amount. Before hole-derived height was implemented, the assumed height left this example's outline 0.10 mm short; that is a historical result, not the current example's error. **Sheet proportions** is the trace's own check of the sheet's shape against the entered size; a discrepancy whose magnitude exceeds 1 % calls for review. Sheet choice, entered size, camera-model or capture error may contribute; the sign can be negative and the check does not identify the cause.

## Limits

- **Your measurements are the reference.** Instrument error, alignment, contact force and a mistyped value affect the comparison. A displayed difference below the entered threshold is not proof of agreement within a known uncertainty.
- **Features are matched by size.** The runner maximizes admitted one-to-one matches, then minimizes their total absolute size error. Equal optima use deterministic value order and stable traversal. This global objective does not establish physical feature identity; equal-size features can remain ambiguous.
- **Calipers and the trace do not measure the same edge on every part.** Calipers close on the widest section. The trace follows the part's silhouette, formed by its top edge on some sides and its bottom edge on others, and assumes a vertical wall between them. A chamfer, draft, burr or a printed part's flared first layer therefore shows up as an edge offset.
- **The outline is the smallest enclosing rectangle.** That equals a caliper reading only across parallel sides.
- **Scale error and edge offset form a two-term model.** A lens the single distortion coefficient does not describe, a curled sheet or a part that does not lie flat can affect both fitted terms and the residual.
- **A few photos give a rough spread.** Three shots do not establish stable tail errors or a confidence interval, particularly with pooled or correlated features.

## Coverage and matching limits

The median, 95th percentile and worst absolute error describe **only matched
dimensions**. A bad reconstruction outside the size gate is unscored, and a
failed photo contributes no dimension samples. Always retain the per-photo
failures and unmatched counts beside these statistics.

The JSON report includes `requested`, `compared`, `unmatched` and `unavailable`
in each photo's and part's `coverage` object and directly in `summary`:

```text
requested = compared + unmatched + unavailable
```

Requested scalars are two for an `outline`, one per `diameters` value, two per
`openings` pair, one per `radii` value and one per `centre_distances` value.
Each part's resolved photo list is deduplicated across patterns before counting;
separately named part entries remain separate experiments. `unmatched` refers
to successful traces only; `unavailable` includes all requested dimensions in
failed traces. The old summary names `samples` and `missing` remain aliases for
`compared` and `unmatched`, respectively.

For example, two requested diameters across two photos create four comparison
opportunities. If one photo fails and only one diameter can be matched in the
other, the summary reports `requested: 4, compared: 1, unmatched: 1,
unavailable: 2`. Those two unavailable dimensions are retained in the total,
not assigned invented errors or included in the conditional percentiles.

The repaired assignment is reproducible without photos:

```python
from scripts import photo_benchmark as pb
assert pb.match([6, 7], [6.4, 5], pb._scalar_cost) == [1, 0]
```

This matches 6 → 5 and 7 → 6.4, both within the unchanged gates. The earlier
greedy first choice, 6 → 6.4, left 7 unmatched. The new matcher also minimizes
summed error among maximum-count assignments. The gate remains a correspondence
heuristic, never a manufacturing or accuracy tolerance.

The [repair and validation record](validation/benchmark-correspondence.md)
describes the independent exhaustive assignment oracle, coverage-conservation
tests and work limits. The [scientific review](validation/scientific-model-review.md#benchmark-correspondence-and-coverage)
preserves the original findings at `5588a52`; its benchmark defect is historical
following this repair. The benchmark change does not resolve the separate
fitting and camera-model findings. Later records cover the
[initial-fit guard](validation/fit-support.md),
[independent lens inverse and mismatch cases](validation/radial-inverse.md), and
[directional-spread qualification](validation/directional-spread-qualification.md).

## What a report holds

File names, your measurements, the traced values, each photo's trace notes, and the figures above. It holds no image data, no camera metadata and no folder path. Nothing is sent anywhere.
