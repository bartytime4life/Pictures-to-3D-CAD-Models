# Capture and calibration guide

The most dependable input is a clearly separated silhouette of one part that has the same cross-section through its thickness. A flat washer, spacer, plate, or gasket is a useful starting point.

Find related workflows in the [documentation index](README.md). Define required dimensions and reserved checks with the [engineering model](engineering-model.md) before relying on the result.

## Choose the capture method

| Method | What you supply | What the workbench does |
| --- | --- | --- |
| Ordinary tracing | A clear, front-on silhouette, measured outside width or known-feature length, and measured thickness | Traces a polygon and applies one uniform scale. It does not rectify perspective or lens distortion. |
| Reference-sheet tracing | The whole flat sheet in view, its stated or measured size selected under **Scale reference**, and measured thickness | Estimates plane/lens corrections, scale and fitted geometry; thickness supports side-wall/parallax correction. Review its notes and independent dimensions. |

The bundled sample uses ordinary tracing with demonstration measurements. Choosing a sheet does not prove that it was detected: an initial upload can fall back to ordinary tracing with a warning if the sheet cannot be used. In that case, enter a measured width or retake the photo; sheet corrections and fitted primitives have not been established for that trace.

## Take the photograph

1. Lay the part flat on a plain background. Use light paper for a dark part, or a dark background for a light part.
2. Face the camera directly toward the part. Keep the camera sensor and part approximately parallel; avoid a tilted or dramatic perspective view.
3. Include the whole outline with a margin around it. Keep rulers, fingers, labels, and other objects away from the silhouette.
4. Use diffuse, even light. Hard shadows, bright reflections, and a dark background visible through holes can become false geometry.
5. Keep the image sharp enough to distinguish the smallest feature you need. A higher-resolution file cannot recover a feature that is blurred or obscured.

Upload a still PNG, JPEG, WebP, HEIC, or AVIF of at most **32 MiB** and **70 million decoded pixels**, with both dimensions at least 16 pixels. That covers phone cameras' 12 to 64 megapixel modes, so a photo can be used as the camera saved it. Animated images are rejected. A HEIC's stored rotation is applied, and a HEIC burst uses its primary image. A camera JPEG that embeds a preview or second view (MPO) is accepted, and only its primary image is traced. A 16-bit grayscale PNG is reduced to 8 bits before tracing. For ordinary tracing, the backend applies image orientation and downsizes the longest side to at most **1400 pixels**. A reference-sheet photo is traced at full resolution up to 16 megapixels; a larger one is first reduced to 16 megapixels by averaging linear light, which keeps edges in place, and a notice says so. If the orientation metadata is damaged, the image is traced as stored and a warning says so; check that the outline is oriented like the part before measuring. Inspect the resulting outline rather than assuming that every original pixel became a geometric feature.

## Review the outline before measuring

Look at both the outer boundary and each interior boundary. A dark marking can be mistaken for a hole, and a true hole can disappear if its background is too dark. The model will extrude the selected profile, so an incorrect trace remains incorrect after scaling.

Open **Trace** or **Adjust outline**. Use **Light part on a dark background** when appropriate. For ordinary tracing, keep **Choose contrast automatically** or turn it off and adjust **Contrast threshold**. For sheet tracing, the threshold is disabled because contrast is measured locally along each edge. **Recover design intent** can snap fitted geometry to square edges, equal radii and aligned axes; review its notes and disable it if those assumptions do not match the part. The detail setting changes contour approximation; increasing detail is not a substitute for a better photograph. Choose **Apply trace** to use the new result, or **Keep current outline** to leave it alone.

Tiny interior regions below the trace resolution can be omitted with a warning. Ordinary tracing ignores hole contours smaller than 9 square pixels in the working image, and specks inside a hole whose contours are below that same area; both are counted in the warning. A larger region inside a hole is rejected. Review capture notes before accepting a trace, particularly when the smallest holes matter.

If several objects are present, the app uses the largest candidate and reports additional substantial regions. Re-photograph or crop the source before uploading if it is unclear which object should be traced. Do not assume a small disconnected feature was intentionally included.

## Photograph the part on a reference sheet

This is the recommended capture. Lay the part flat on a sheet of known size, with paper showing all round it, and photograph the **whole sheet**. All four corners must be in the frame, with a contrasting surface (a table, not more paper) around the sheet. Choose the sheet as the **Scale reference** in the photo dialog before uploading, or later under **Adjust outline**. A4 (210 × 297 mm) and US Letter (215.9 × 279.4 mm) are built in; for any other sheet, choose **Custom sheet, measured** and enter its sides.

- **Measure your sheet.** Its stated size sets every dimension. ISO 216 allows ±2 mm on A4's 297 mm side, about 0.7 %; most sheets are much closer. The workbench checks the sheet's *proportions* against the photo and warns when they differ from your choice by more than 1 %, but it cannot see a uniformly wrong size.
- **Keep the sheet flat.** A curled or creased sheet breaks the straight edges used to correct the lens and the plane used for scale.
- **Enter the thickness.** For a thick part, the camera sees some of its side walls. Building re-traces the available photo when the entered thickness differs from the trace's thickness record, applying the side-wall/parallax model. A restored recipe contains no photo, so re-upload it to recompute that correction for a different thickness. A photo tilted about 10–20° gives the most reliable correction. Straight overhead, the walls are too narrow to measure, and an edge facing the camera may read up to 0.2 × the edge blur into the part; the trace says so when that happens.
- **Contrast.** A dark part on white paper is typical. For a light part, use a dark sheet on a lighter surface and tick **Light part on a dark background**.
- **Soften the light.** A shadow beside the part moves its edges outward, by more as the shadow gets darker. In the rendered tests, a shadow that removes about half the light next to an edge costs up to 0.05 mm on a hole's diameter. The effect grows with the square of the edge blur, so a sharp photo helps too. Use diffuse light from above, not a single lamp to one side.
- **Use the photo as the camera saved it.** Edges are measured after undoing the standard sRGB tone curve. Filters and edited brightness or contrast change that curve and move the edges.

With a sheet the width field is filled from the sheet. Measure the part's real width anyway, and compare: it is now an independent check, not the scale. A successful sheet trace reports the fitted geometry (circles, arcs, lines), design-intent snaps, measured edge blur, lens correction and proportions check. These are model evidence, not a real-photo accuracy guarantee. See [reference-sheet tracing](reference-sheet.md) for the method and its evidence.

## Set the scale

Without a reference sheet, supply one measured length using either the complete outside width or two points on a known feature. Both methods apply one scale factor to the entire outline; neither removes perspective or lens distortion.

### Enter the complete outside width

The reference width is the **complete horizontal span of the traced part**, from its leftmost to rightmost outline point in the image. The outline follows the outer edges of the part's boundary pixels, so a part covering 401 pixel columns spans 401 pixels. It is not an arbitrary distance between holes or the length of whichever edge is easiest to measure.

Measure that same span on the real part and enter it with an explicit unit. Align the part in the photograph so this direction is unambiguous. Use the known-feature option below if the measurement you can supply is a different edge or pair of points.

Internally, the conversion is:

```text
millimeters per pixel = measured reference width / traced horizontal pixel span
```

That factor is applied uniformly to both image axes. The model's height is therefore calculated from the image; it is not independently measured.

### Use two points on a known feature

Open **Use a known feature**. Choose two clearly visible endpoints of a feature whose physical length you have measured, then enter that distance as **Known feature length**. For example, use the centers of two holes only when the measurement is the distance between those same centers. Prefer a long, sharply defined reference on the part; a short span makes small endpoint-placement errors more influential.

Select the endpoints on the reference preview or enter their X/Y coordinates numerically. Coordinates belong to the orientation-adjusted **working image**, whose longest side is at most 1400 pixels. They are not browser-screen coordinates or necessarily the original camera-file coordinates. The numeric controls provide the same operation without pointing.

Choose **Apply reference scale** to set the complete outside width from the reference:

```text
reference pixels = sqrt((x2 - x1)^2 + (y2 - y1)^2)
millimeters per pixel = measured feature length / reference pixels
outside width = traced horizontal pixel span × millimeters per pixel
```

The reference may run horizontally, vertically, or diagonally. Its direction does not rotate the outline or give the two axes separate scales. Keep the reference and the outline being reconstructed in the same flat plane, with the camera facing that plane directly. A reference resting at a different height can give a different apparent scale.

Applying a reference makes an existing model outdated; **Next step → Update preview** rebuilds for inspection without opening Export. **Update model** rebuilds and opens export review. Editing the outside width directly clears the saved endpoint-calibration record. A successful re-trace of the same photo retains the reference and recalculates the outside width from the new outline; if the working-image frame changes, the app clears the reference with a notice. A new photo or sample starts without the earlier reference. Review the chosen points and the resulting dimensions after any source change.

Use [Explore endpoint placement](reference-sensitivity.md) inside these controls to see how an assumed endpoint shift changes the source-width calculation. This is a sensitivity scenario in working-image pixels, not an estimated measurement error, manufacturing accuracy or photograph correction.

## Enter thickness separately

Measure the part's constant thickness and enter it independently. A front-facing photograph does not supply a reliable thickness. If the part has different thicknesses, countersinks, pockets, or sloped walls, this workflow does not describe the complete part.

The supported outside width and resulting height are each **0.1–2000 mm**; thickness is **0.1–500 mm**. These are computational input bounds, not guarantees of manufacturing usefulness throughout those ranges.

Switching display units should preserve the physical measurement. Before exporting, confirm the reported width, height, and thickness, especially after restoring a project or changing units.

## Cross-check before fabrication

Use **Independent height check** to enter the **Measured outside height** of the real part, from its topmost to bottommost outline point in the photograph. This optional value supports **0.1–2000 mm**. Reserve it from setting the scale: if the same height established the endpoint reference, it is not an independent check.

The workbench compares that measurement with the source-outline height implied by the selected scale, before any explicit XY design percentage. The signed difference is `estimated height - measured height`; a positive value means the estimate is larger. Entering the check does not stretch the model or change the scale. Agreement is useful evidence for this dimension, but does not establish a physical accuracy bound or manufacturing acceptance.

Optionally enter an **Allowed height deviation** and a justified absolute **Measurement error bound**. The tool compares the complete entered interval with that allowance and reports within, outside, or inconclusive. Boundary contact stays inconclusive; unknown inputs stay undecided. Both fields start blank. This checks one source dimension under your bound, which the tool does not validate; it does not qualify a print. See the [engineering model](engineering-model.md) for the equations, examples and physical verification sequence.

Keep the physical reference and source-scale check separate from intentional design changes. For example, a 120% XY design scale makes the exported dimensions 20% larger; the source-height check still compares the reconstructed source part with its measurement.

Measure further reserved dimensions—for example, hole spacing—and compare them with the exported model in your CAD tool. A disagreement can indicate perspective distortion, endpoint placement, an incorrect boundary, or a mismatched physical reference. Record the measurement method and its limitations. If you change the scale or outline to satisfy a check, keep that earlier result and obtain a fresh check for the revised model where practical. The [independent-check worksheet](../reference-library/templates/INDEPENDENT-CHECKS.md) helps preserve these distinctions.

For a reference-sheet photo, [the photo benchmark](photo-benchmark.md) makes this comparison for a whole folder: it traces every photo, compares each dimension you measured, and reports the spread between repeat shots.

Do not stretch one axis merely to make two measurements agree without understanding the cause. Uniform scale alone does not calibrate a camera or remove lens distortion.

For a close-fitting part, inspect important features individually, apply the intended manufacturing tolerances in the downstream CAD/CAM workflow, and make an appropriate trial part. This app does not validate strength, fit, tool clearance, material choice, or manufacturing suitability.

## Build, review and keep the work

The **Next step** guide focuses missing width/thickness fields or opens invalid **Design & print** settings. **Create preview** and **Update preview** build while keeping the source and model visible; once current, **Choose an export** opens the downloads. Review the calculated dimensions and independent checks, rather than treating **Solid ready** as manufacturing acceptance. See the [guided workbench review](validation/guided-workbench.md) for the recorded interaction evidence.

Use **Save project** to download the editable recipe. If an invalid independent height or incomplete decision pair prevents saving from Export, the dialog closes and the relevant height-check field receives focus. Complete the notes or clear optional decision inputs you cannot justify. The browser's saved recipe includes endpoint calibration and independent-height decision inputs; the backend recipe in a slicer ZIP does not include those browser-only notes. Download **Save project** separately to retain them. Neither recipe contains the photo; keep the original separately if you need to retrace. See [export formats](exports.md) and [troubleshooting](troubleshooting.md) for recovery and downstream checks.

## Inputs outside this workflow

| Input | Why it needs a different approach |
| --- | --- |
| Angled photograph of a volumetric object | The visible silhouette does not describe its unseen surfaces. |
| Multiple overlapping parts | The image does not establish which hidden boundaries belong to each part. |
| Transparent or strongly reflective material | Foreground/background separation may not match the physical edge. |
| Tapered or varying-thickness part | A single extrusion cannot represent its full geometry. |
| Threaded, recessed, or countersunk features | Interior shading is not a reliable depth measurement. |
| Tiny features near the image resolution limit | Their dimensions may be dominated by blur, compression, and tracing approximation. |
