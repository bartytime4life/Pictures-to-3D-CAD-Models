# Image inspection

Open **Image inspection** (`#image`) to investigate a source picture before tracing
or generating relief. It needs no model and makes no analysis network requests.

1. Open A (PNG/JPEG/WebP/AVIF, 1 byte–32 MiB, at most 40 megapixels).
2. Drag a region or enter Left/Top/Width/Height percentages. Full image resets it;
   Escape or a cancelled gesture retains the previously committed region.
3. Read the histogram, brightness, tonal spread and edge support.
4. Optionally open B to compare the same normalized region in two pixel-aligned
   images. Matching sampled dimensions are required; no alignment is performed.
5. Save readings as JSON or send the unchanged original into Flat part or Relief.
   The region does not crop your source and does not set CAD dimensions.

The Photo library also offers **Inspect image**, deliberately reading its stored
original from the local service. Inspection itself sends no image to a server or
AI model. The receiving Flat part or Relief studio uploads the original when you
choose a handoff. Convert a copy of any HEIC file to a supported format for inspection.
Frames survive studio navigation
in tab memory; Clear releases one, and page reload discards both. Clearing or
replacing a pending import prevents its late completion from restoring an image.
A failed replacement retains the previous image.

## Methods and limits

The browser samples to at most 720 pixels on the longest side, preserving aspect
ratio. Transparency is composited over **white** in both display and analysis.
The original file remains unchanged. Regions round outward to sampled pixels.

| Reading | Definition and limits |
| --- | --- |
| Brightness, 0–255 | Mean rounded `0.2126R + 0.7152G + 0.0722B` of displayed sRGB values; not linear luminance or lux. |
| P05–P95 | Exact nearest-rank 5th/95th percentiles; not optical dynamic range. |
| Dark / bright tones | Share at or below 15 / at or above 240. A white background naturally has many bright pixels; this does not prove lost detail. |
| Edge strength | Mean 3×3 Sobel magnitude divided by `255√20`, reported as 0–100%. Texture/contrast proxy, not calibrated focus, blur or percentage of edge pixels. |
| Edge support | Only centres whose entire 3×3 neighbourhood is inside the region. Below 3 pixels in either dimension means **Unavailable**, distinct from measured zero. |
| Histogram | 16 bins covering every selected sampled pixel. |
| A/B difference | Mean absolute luma difference and share differing by at least 24 levels. Lighting, movement and compression also cause differences. |

The Sobel maximum follows by enumerating all 512 binary vertices of a 3×3 patch:
the largest squared magnitude is `20 × 255²`. A convex norm of a linear operator
attains a box maximum at a vertex. Tests use an independent kernel oracle, exact
crops, transparent images and missing-support cases.

**Save readings** exports schema `pictures-to-cad-image-inspection-v1`: filenames,
original/sample dimensions, selected region, effective pixel bounds, readings,
comparison and method `picad-srgb-white-sobel-v1`. It includes no image bytes or
filesystem paths. Null comparison means absent images or mismatched sample sizes,
not zero difference. This is not a signed hash or calibrated physical measurement.

## Architecture decision and DVR provenance

**Decision:** Accepted for this implementation, November 17, 2026. Add a bounded
browser tool to the typed studio catalog, separate from geometry/model inference,
with the existing one-shot original-file handoff. Sampling cannot alter CAD scale.

Methods adapt Intelligent-DVR-Tool's
[image-science.mjs](https://github.com/bartytime4life/Intelligent-DVR-Tool/blob/9dfba23cf954f60531a7b541e5b482ee01d96c5c/src/image-science.mjs)
(Git blob `ccfa2a89f928d617ddf36f89b32cbf3386a46362`) and
[diagnostics guide](https://github.com/bartytime4life/Intelligent-DVR-Tool/blob/9dfba23cf954f60531a7b541e5b482ee01d96c5c/docs/facility-image-diagnostics.md),
reviewed at DVR main `9dfba23cf954f60531a7b541e5b482ee01d96c5c`. This app uses
white instead of the DVR's black backing to match its flat-part workflow; the
method/schema identify that difference.

Server processing could reuse HEIC decoding but would upload images and compete
with CAD jobs. A vision model would add weights without improving these arithmetic
readings. The selected approach keeps two bounded samples and original files in
memory; decoding up to 40 megapixels can use more transient memory, and browser
codec support varies. Existing linear-light subpixel tracing, calibration, blur
measurements and optional vision workers remain separate.
