# Capture and calibration guide

The most dependable input is a clearly separated silhouette of one part that has the same cross-section through its thickness. A flat washer, spacer, plate, or gasket is a useful starting point.

## Take the photograph

1. Lay the part flat on a plain background. Use light paper for a dark part, or a dark background for a light part.
2. Face the camera directly toward the part. Keep the camera sensor and part approximately parallel; avoid a tilted or dramatic perspective view.
3. Include the whole outline with a margin around it. Keep rulers, fingers, labels, and other objects away from the silhouette.
4. Use diffuse, even light. Hard shadows, bright reflections, and a dark background visible through holes can become false geometry.
5. Keep the image sharp enough to distinguish the smallest feature you need. A higher-resolution file cannot recover a feature that is blurred or obscured.

Upload a still PNG, JPEG, or WebP of at most **10 MiB** and **16 million decoded pixels**, with both dimensions at least 16 pixels. Animated images are rejected. The backend applies image orientation and downsizes the longest side to at most **1400 pixels**. Inspect the resulting outline rather than assuming that every original pixel became a geometric feature.

## Review the outline before measuring

Look at both the outer boundary and each interior boundary. A dark marking can be mistaken for a hole, and a true hole can disappear if its background is too dark. The model will extrude the selected profile, so an incorrect trace remains incorrect after scaling.

Use the foreground/background control when the part is lighter than its background. Adjust the threshold to separate the part from the background. The detail setting changes contour approximation; increasing detail is not a substitute for a better photograph.

Tiny interior regions below the trace resolution can be omitted with a warning. The current tracer ignores hole contours smaller than 9 square pixels in the working image. Nested regions inside a hole are rejected. Review capture notes before accepting a trace, particularly when the smallest holes matter.

If several objects are present, the app uses the largest candidate and reports additional substantial regions. Re-photograph or crop the source before uploading if it is unclear which object should be traced. Do not assume a small disconnected feature was intentionally included.

## Set the reference width

The reference width is the **complete horizontal span of the traced part**, from its leftmost to rightmost outline point in the image. It is not an arbitrary distance between holes or the length of whichever edge is easiest to measure.

Measure that same span on the real part and enter it with an explicit unit. Align the part in the photograph so this direction is unambiguous. If your intended reference is a different edge or pair of points, retake or rotate the source image so the full horizontal span corresponds to the measurement you can supply.

Internally, the conversion is:

```text
millimeters per pixel = measured reference width / traced horizontal pixel span
```

That factor is applied uniformly to both image axes. The model's height is therefore calculated from the image; it is not independently measured.

## Enter thickness separately

Measure the part's constant thickness and enter it independently. A front-facing photograph does not supply a reliable thickness. If the part has different thicknesses, countersinks, pockets, or sloped walls, this workflow does not describe the complete part.

The supported reference width and resulting height are each **0.1–2000 mm**; thickness is **0.1–500 mm**. These are computational input bounds, not guarantees of manufacturing usefulness throughout those ranges.

Switching display units should preserve the physical measurement. Before exporting, confirm the reported width, height, and thickness, especially after restoring a project or changing units.

## Cross-check before fabrication

Measure a second dimension on the real part—for example, its height or hole spacing—and compare it with the exported model in your CAD tool. A disagreement can indicate perspective distortion, an incorrect boundary, or a mismatched reference width.

Do not stretch one axis merely to make two measurements agree without understanding the cause. Uniform scale alone does not calibrate a camera or remove lens distortion.

For a close-fitting part, inspect important features individually, apply the intended manufacturing tolerances in the downstream CAD/CAM workflow, and make an appropriate trial part. This app does not validate strength, fit, tool clearance, material choice, or manufacturing suitability.

## Inputs outside this workflow

| Input | Why it needs a different approach |
| --- | --- |
| Angled photograph of a volumetric object | The visible silhouette does not describe its unseen surfaces. |
| Multiple overlapping parts | The image does not establish which hidden boundaries belong to each part. |
| Transparent or strongly reflective material | Foreground/background separation may not match the physical edge. |
| Tapered or varying-thickness part | A single extrusion cannot represent its full geometry. |
| Threaded, recessed, or countersunk features | Interior shading is not a reliable depth measurement. |
| Tiny features near the image resolution limit | Their dimensions may be dominated by blur, compression, and tracing approximation. |
