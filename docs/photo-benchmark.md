# Photo benchmark: your photos against your calipers

Every accuracy figure in this repository so far comes from rendered photographs. `make photo-benchmark` measures the reference-sheet tracer on real ones: you photograph parts you have measured, list those measurements in a small file, and it reports how far each traced dimension lies from your calipers and how much it moves between repeat shots.

**No result from real photos is recorded yet.** The example report below comes from rendered photos and shows the format only.

Everything runs on your computer. Each photo goes through the same function as an upload to the workbench, so the report describes what the workbench would give you.

The current report's error statistics cover matched dimensions from successful
traces. Failed photos are listed separately, but their expected dimensions do
not enter the dimension totals. Size matching is greedy and can miss a valid
assignment. Read the [coverage and matching limits](#coverage-and-matching-limits)
before interpreting a small reported error as overall performance.

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
| `caliper_uncertainty_mm` | A numeric comparison threshold in mm; 0.03 if left out. Mean errors beyond it are printed in bold. Record separately whether your entered specification is an accuracy limit, absolute bound or standard uncertainty. The runner does not distinguish them or propagate a measurement uncertainty budget. |
| `name` | A label for the report. Parts need different names. |
| `photos` | File names or patterns, relative to the folder. |
| `thickness_mm` | The part's thickness. With it, the trace removes the visible side walls, as **Build** does in the workbench. Leave it out for a part thin enough to ignore. |
| `light_part` | `true` for a light part on a dark sheet. |
| `measured` | The measurements of step 2. |

A misspelt setting is refused by name, so a typing error cannot silently drop a measurement.

The generated report currently calls this threshold the calipers' uncertainty
and says smaller errors cannot be distinguished from it. That sentence is not
a statistical decision rule: no coverage factor, calibration contribution or
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

- `--json FILE` saves every reading, each photo's trace notes and the per-photo fits.
- `--markdown FILE` saves the printed tables.
- `--no-snap` traces without design-intent snapping. With snapping on, as in the workbench, near-equal radii are made equal and straight edges are squared, so four equal holes share one reading per photo.
- `--example FOLDER` writes three rendered photos and a `benchmark.json` to copy from. It takes about half a minute.

A trace takes a few seconds per photo. The command exits with an error only when the file cannot be used or no photo could be traced.

## 6. Read the report

This report is the `--example` folder: three **rendered** photos of the test plate at 22°, 9° and 0° tilt, 4 mm thick, with its design dimensions as the caliper values.

> 3 of 3 photos traced; 48 dimensions compared.
> Absolute error: median 0.005 mm, 95th percentile 0.043 mm, worst 0.104 mm.

| Dimension | Calipers (mm) | Readings | Mean error (mm) | Spread, SD (mm) | Worst (mm) | Not found |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Outline length | 120.00 | 3 | **-0.033** | 0.062 | -0.104 |  |
| Outline width | 70.00 | 3 | -0.020 | 0.033 | -0.058 |  |
| Ø22 | 22.00 | 3 | +0.000 | 0.010 | +0.012 |  |
| Ø6 (×4) | 6.00 | 12 | +0.012 | 0.023 | +0.043 |  |
| Opening 24 × 8 length | 24.00 | 3 | +0.008 | 0.018 | +0.029 |  |
| Opening 24 × 8 width | 8.00 | 3 | -0.006 | 0.009 | -0.016 |  |
| R8 (×4) | 8.00 | 12 | -0.006 | 0.008 | -0.014 |  |
| Centres 96 | 96.00 | 3 | -0.004 | 0.008 | -0.012 |  |
| Centres 50 | 50.00 | 3 | -0.002 | 0.004 | -0.006 |  |
| Centres 108.24 | 108.24 | 3 | -0.006 | 0.009 | -0.015 |  |

> Scale error -0.011 % (SD 0.017 between photos); edge offset -0.005 mm (SD 0.012 between photos), positive when boundaries are found outside the material. What the two leave unexplained: 0.008 mm RMS.

| Photo | Edge blur (mm) | Sheet proportions (%) | Worst error (mm) | Result |
| --- | ---: | ---: | ---: | --- |
| plate-1.jpg | 0.326 | 0.00 | -0.014 | Traced |
| plate-2.jpg | 0.310 | 0.00 | -0.016 | Traced |
| plate-3.jpg | 0.302 | 0.00 | -0.104 | Traced |

**The dimension table.** An error is the traced value minus your caliper value.

- **Mean error** is the observed mean signed error for the matched samples. A small study does not establish the population bias or show which physical effect caused it.
- **Spread** is the sample standard deviation of the row's errors. For one identifiable feature it describes the observed repeat-shot spread. For a row of several equal features (×4) it also includes differences between them; snapping and common calibration can correlate the readings. Twelve readings of four holes in three photos are not twelve independent captures.
- **Worst** is the largest single error, with its sign.
- **Not found** counts unmatched expected dimensions within successful traces. The size gate is 1 mm or 15 %, whichever is larger. A missing circle, or a hole described as a non-circular opening, can land here. Greedy assignment can also leave a dimension unmatched even when a full assignment exists. Dimensions from completely failed traces are absent from this count.

**Scale error and edge offset.** Least squares fits a two-term diagnostic to each photo's matched errors:

- The **scale term** changes every dimension in proportion to its size. A wrong sheet size or perspective error could produce this pattern, but the fit does not identify the cause.
- The **edge term** grows outside dimensions and shrinks holes by twice the offset, and leaves centre distances alone. Blur, shadow, tone mapping or non-vertical walls could contribute to this pattern.

The line gives their mean over the part's photos and their spread between photos. Radii take no part. The split is made only when a photo holds at least four dimensions that can separate the two: a mix of sizes, or of outside dimensions, holes and centre distances.

The unexplained RMS is evaluated on the same samples used to fit these terms.
It is an in-sample residual, not an independent prediction error or proof that
the two terms capture all physical causes.

**The photo table** shows which shot is the odd one out. In the example it is the overhead photo, which reads the outline 0.10 mm short. Its trace notes, in the JSON report, say what to suspect: seen from straight above, the 4 mm walls are too narrow to measure, and an edge may read up to 0.06 mm into the part. **Sheet proportions** is the trace's own check of the sheet's shape against the entered size; a discrepancy whose magnitude exceeds 1 % calls for review. Sheet choice, entered size, camera-model or capture error may contribute; the sign can be negative and the check does not identify the cause.

## Limits

- **Your measurements are the reference.** Instrument error, alignment, contact force and a mistyped value affect the comparison. A displayed difference below the entered threshold is not proof of agreement within a known uncertainty.
- **Features are matched by size.** The runner sorts admissible pairs by absolute size error and greedily takes unused pairs. It does not solve a global assignment or establish physical feature identity. See the counterexample below.
- **Calipers and the trace do not measure the same edge on every part.** Calipers close on the widest section. The trace follows the part's silhouette, formed by its top edge on some sides and its bottom edge on others, and assumes a vertical wall between them. A chamfer, draft, burr or a printed part's flared first layer therefore shows up as an edge offset.
- **The outline is the smallest enclosing rectangle.** That equals a caliper reading only across parallel sides.
- **Scale error and edge offset form a two-term model.** A lens the single distortion coefficient does not describe, a curled sheet or a part that does not lie flat can affect both fitted terms and the residual.
- **A few photos give a rough spread.** Three shots do not establish stable tail errors or a confidence interval, particularly with pooled or correlated features.

## Coverage and matching limits

The median, 95th percentile and worst absolute error describe **only matched
dimensions**. A bad reconstruction outside the size gate is unscored, and a
failed photo contributes no dimension samples. Always retain the per-photo
failures and unmatched counts beside these statistics.

Count requested scalar dimensions from the manifest: two for `outline`, one per
`diameters`, two per `openings` pair, one per `radii` and one per
`centre_distances`. Multiply each part's count by its photo count and add across
parts. Until the runner reports all denominators, record this conservation
check separately:

```text
requested = compared + unmatched in successful traces
                     + unavailable in failed traces
```

For example, two requested diameters across two photos create four comparison
opportunities. If one photo fails and the other compares one diameter, the
current summary can show `samples: 1, missing: 1`; it does not include the failed
photo's two dimensions in `missing`.

The matching defect is reproducible without photos:

```python
from scripts import photo_benchmark as pb
assert pb.match([6, 7], [6.4, 5], pb._scalar_cost) == [0, None]
```

The greedy first choice is 6 → 6.4. It blocks 7, although 6 → 5 and 7 → 6.4
both satisfy the unchanged gates. A future matcher should first maximize the
number of admitted matches, then minimize total admitted error. Even that
objective cannot prove physical identity for equal-size features. The gate is a
correspondence heuristic, never a manufacturing or accuracy tolerance. The
[scientific review](validation/scientific-model-review.md#benchmark-correspondence-and-coverage)
records the proposed independent tests; this documentation update does not
change the runner.

## What a report holds

File names, your measurements, the traced values, each photo's trace notes, and the figures above. It holds no image data, no camera metadata and no folder path. Nothing is sent anywhere.
