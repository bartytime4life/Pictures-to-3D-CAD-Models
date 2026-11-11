# Photo benchmark: your photos against your calipers

Every accuracy figure in this repository so far comes from rendered photographs. `make photo-benchmark` measures the reference-sheet tracer on real ones: you photograph parts you have measured, list those measurements in a small file, and it reports how far each traced dimension lies from your calipers and how much it moves between repeat shots.

**No result from real photos is recorded yet.** The example report below comes from rendered photos and shows the format only.

Everything runs on your computer. Each photo goes through the same function as an upload to the workbench, so the report describes what the workbench would give you.

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

Take at least three shots of each part, and pick the part up and put it down between shots. The spread between repeat shots is half of what this benchmark measures. To learn what a condition costs, change one thing at a time between sets (tilt, light, distance, phone) and give each set its own entry in the file.

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
| `caliper_uncertainty_mm` | Your calipers' stated accuracy; 0.03 if left out. Mean errors beyond it are printed in bold. |
| `name` | A label for the report. Parts need different names. |
| `photos` | File names or patterns, relative to the folder. |
| `thickness_mm` | The part's thickness. With it, the trace removes the visible side walls, as **Build** does in the workbench. Leave it out for a part thin enough to ignore. |
| `light_part` | `true` for a light part on a dark sheet. |
| `measured` | The measurements of step 2. |

A misspelt setting is refused by name, so a typing error cannot silently drop a measurement.

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
> Absolute error: median 0.013 mm, 95th percentile 0.035 mm, worst 0.088 mm.

| Dimension | Calipers (mm) | Readings | Mean error (mm) | Spread, SD (mm) | Worst (mm) | Not found |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Outline length | 120.00 | 3 | -0.018 | 0.061 | -0.088 |  |
| Outline width | 70.00 | 3 | -0.002 | 0.034 | -0.041 |  |
| Ø22 | 22.00 | 3 | -0.016 | 0.010 | -0.025 |  |
| Ø6 (×4) | 6.00 | 12 | +0.002 | 0.025 | +0.035 |  |
| Opening 24 × 8 length | 24.00 | 3 | -0.007 | 0.020 | -0.019 |  |
| Opening 24 × 8 width | 8.00 | 3 | -0.021 | 0.007 | -0.028 |  |
| R8 (×4) | 8.00 | 12 | +0.005 | 0.006 | +0.012 |  |
| Centres 96 | 96.00 | 3 | -0.002 | 0.009 | -0.011 |  |
| Centres 50 | 50.00 | 3 | -0.002 | 0.004 | -0.007 |  |
| Centres 108.24 | 108.24 | 3 | -0.005 | 0.009 | -0.015 |  |

> Scale error -0.009 % (SD 0.017 between photos); edge offset +0.002 mm (SD 0.013 between photos), positive when boundaries are found outside the material. What the two leave unexplained: 0.008 mm RMS.

| Photo | Edge blur (mm) | Sheet proportions (%) | Worst error (mm) | Result |
| --- | ---: | ---: | ---: | --- |
| plate-1.jpg | 0.326 | 0.00 | -0.025 | Traced |
| plate-2.jpg | 0.310 | 0.00 | -0.028 | Traced |
| plate-3.jpg | 0.302 | 0.00 | -0.088 | Traced |

**The dimension table.** An error is the traced value minus your caliper value.

- **Mean error** is the bias: what stays wrong however often you shoot.
- **Spread** is the sample standard deviation of the row's errors. For one feature it is the repeat-shot spread. For a row of several equal features (×4) it also holds the differences between them.
- **Worst** is the largest single error, with its sign.
- **Not found** counts caliper values for which a photo's trace held no feature of that kind within 1 mm or 15 %, whichever is larger. A hole that did not trace, or traced as an outline and not a circle, lands here. It is never dropped silently.

**Scale error and edge offset.** Each photo's errors are split into two causes by least squares:

- A **scale error** changes every dimension in proportion to its size. It points at the sheet's entered size or the perspective correction.
- An **edge offset** is a boundary found off the true edge. It grows outside dimensions and shrinks holes by twice the offset, and leaves centre distances alone. It points at blur, shadow, the camera's tone curve, or an edge that is not a sharp vertical wall.

The line gives their mean over the part's photos and their spread between photos. Radii take no part. The split is made only when a photo holds at least four dimensions that can separate the two: a mix of sizes, or of outside dimensions, holes and centre distances.

**The photo table** shows which shot is the odd one out. In the example it is the overhead photo, which reads the outline 0.09 mm short. Its trace notes, in the JSON report, say what to suspect: seen from straight above, the 4 mm walls are too narrow to measure, and an edge may read up to 0.06 mm into the part. **Sheet proportions** is the trace's own check of the sheet's shape against the entered size; a value above 1 % means the wrong sheet was chosen or a side was mistyped.

## Limits

- **Your measurements are the reference.** The benchmark cannot show an error smaller than your calipers' own, and a mistyped value looks like a tracing error.
- **Features are matched by size.** A caliper value takes the nearest traced feature of its kind. Two different features of nearly the same size cannot be told apart, and a wrong match shows as a large error.
- **Calipers and the trace do not measure the same edge on every part.** Calipers close on the widest section. The trace follows the part's silhouette, formed by its top edge on some sides and its bottom edge on others, and assumes a vertical wall between them. A chamfer, draft, burr or a printed part's flared first layer therefore shows up as an edge offset.
- **The outline is the smallest enclosing rectangle.** That equals a caliper reading only across parallel sides.
- **Scale error and edge offset are a two-cause model.** A lens the single distortion coefficient does not describe, a curled sheet or a part that does not lie flat all end up in what the two leave unexplained.
- **A few photos give a rough spread.** A standard deviation from three shots is uncertain by about half its value.

## What a report holds

File names, your measurements, the traced values, each photo's trace notes, and the figures above. It holds no image data, no camera metadata and no folder path. Nothing is sent anywhere.
