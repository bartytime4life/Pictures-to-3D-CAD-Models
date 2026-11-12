# Troubleshooting

Use the visible error message and the **Next step** guide to identify the action that is needed. The guide is deterministic input/build state, not AI advice or manufacturing acceptance. Keep the current photograph and dimensions while correcting a recoverable problem; starting over should not be the default recovery strategy. See the [documentation index](README.md) for other tasks and the [capture guide](capture-guide.md) for source preparation.

## Image and tracing problems

| Symptom | Likely cause | Next action |
| --- | --- | --- |
| Unsupported or unreadable image | The bytes are not a supported image, or the file is damaged. | Export a fresh PNG, JPEG, WebP, HEIC, or AVIF; changing the extension alone does not convert a file. A HEIC that uses a codec other than HEVC is not supported. |
| Upload rejected as too large | Encoded size or decoded image dimensions exceed the server limit. | Resize the image before uploading, keeping the relevant boundary sharp. |
| A selected reference sheet was not used | The whole sheet could not be detected or measured, and the initial upload fell back to ordinary tracing with a warning. | Enter a measured width, or retake the whole flat sheet with all four corners visible and choose the matching **Scale reference**. A fallback does not supply sheet correction or fitted geometry. |
| The part's outline is not clear enough to measure, even with all sheet corners visible | The sheet and part were found, but too few outer-edge measurements survived; weak local contrast or blur can cause this. | Retake the photo in focus with stronger contrast between the part and the sheet. Keep the whole sheet visible and use diffuse lighting that leaves the boundary clear. Alternatively choose **None: I will enter a measured width** and review the ordinary trace before relying on it. |
| Contrast threshold is disabled | Reference-sheet tracing measures contrast locally. | Review sheet choice, foreground interpretation, capture and trace notes. To use manual contrast on an ordinary silhouette, choose **None: I will enter a measured width**. |
| No useful outline | Low contrast, a blank image, or the wrong foreground interpretation. | Check the foreground setting and threshold; retake with a plain contrasting background if necessary. |
| Background selected as the part | Foreground and background are reversed or merge at the image edge. | Invert the foreground interpretation and leave a clear margin around the whole part. |
| Multiple substantial regions | Other objects, loose pieces, or a detached part appear in the image. | Use an image of one intended connected part. Review the warning and selected region. |
| Hole missing or false hole present | Reflection, shadow, texture, or thresholding changed the interior boundary. | Compare the trace with the real part and adjust the threshold or capture. Do not export an unreviewed hole pattern. |
| Outline and image appear rotated differently | Orientation or coordinate handling is incorrect. | Re-export the source with its orientation applied and report the reproducible case. The normalized display image and trace should align. |
| Warning that orientation metadata could not be read | The file's EXIF block is damaged, so the photo was traced as stored rather than rotated. | If the part appears sideways or mirrored, rotate the photo or re-export it with its orientation applied, then trace again. |

The [weak-edge recovery check](validation/contrast-recovery.md) records this
specific reference-sheet failure and subsequent successful tracing. Its guidance
does not make an unclear capture measurable or establish dimensional accuracy.

## Scale and geometry problems

An expected circle or arc may remain a traced outline when its initial fit lacks
source support or exceeds the bounded sampling work. This preserves the source
instead of extrapolating unsupported geometry; see the [fit-support check](validation/fit-support.md).
Compare the photograph and important dimensions if an analytic fit or later
design-intent correction disagrees. Use ordinary tracing with measured scale or
rebuild critical features in CAD when needed. Turning off design-intent snapping
does not disable whole-circle fitting or the initial support check.

| Symptom | Likely cause | Next action |
| --- | --- | --- |
| Width is correct but height is wrong | Perspective, image distortion, or a reference width that does not match the full horizontal span. | Review [calibration](capture-guide.md), retake front-on, and compare a second physical measurement. |
| Thickness does not match the part | The app uses the entered thickness, not a thickness inferred from the photo. | Measure and enter the constant thickness separately. |
| Invalid profile or solid | Boundaries intersect, touch incorrectly, or form unsupported topology. | Simplify the source, adjust tracing, and inspect small features or near-touching holes. |
| Build is busy | Another geometry conversion is using the bounded worker. | Let it finish, then retry. Repeated rapid submissions will not speed it up. |
| Temporary model storage is full | The service has reached its model-directory cap. | Download any needed files, then use **Capture guide → Clear temporary exports** and rebuild. This clears all completed exports on this instance. |
| Build times out | The profile is unusually complex or the kernel cannot complete it in the permitted time. | Try a coarser outline and remove irrelevant visual texture from the source. |
| Preview is marked outdated or footer says Rebuild needed | Editable source/design settings changed after the last successful build. | Use **Next step → Update preview** to rebuild and inspect without opening Export; **Update model** builds and opens export review. An old preview is not confirmation that the new settings succeeded. |
| Build or export is disabled after collapsing settings | A required measurement or design/print value is invalid. | Read the cause in **Next step**. **Enter width**, **Enter thickness** or **Fix design settings** takes you to the existing control/panel. |
| Old result remains after an error | The app preserved a previous successful result for recovery. | Correct the current input and rebuild; do not assume the visible model reflects the failed change. |

## Design and print planning

| Symptom | Next action |
| --- | --- |
| The sample shows a usable model before I enter measurements | The sample uses demonstration inputs of 80 mm width and 4 mm thickness, labeled above the workbench. Upload your own part and supply its measured scale and thickness before relying on its output. |
| Resulting size differs from the measured reference | Check the explicit XY and thickness design percentages. At 100%, each keeps the corresponding measured size; a different percentage deliberately changes the design without changing its source measurement. |
| Small feature changes after choosing relative detail | Compare against the original-detail build. Detail modes can simplify geometry; a larger nozzle or smoother display cannot recover missing photo detail. |
| A printer says the part is too large | Check the actual usable X/Y/Z volume and margin. Choose another printer or a reviewed split plan. Scaling changes the part's physical size and is a separate decision. |
| Geometric bounds fit but the slicer rejects placement | Check supports, brim/raft/skirt, excluded bed areas, clearance, and machine settings in the slicer. A rectangular fit check does not model them. |
| Split pieces still look assembled in the preview or combined file | That is expected. Use the per-part ZIP to import pieces separately; the combined mesh/STEP is not a spaced print-bed layout. |
| Pieces need a way to join | The generated cuts are straight divisions. Design and validate your own joints, fastening, clearance, and assembly plan before fabrication. |
| Preview color is absent from STL | STL does not preserve color/material. The selected appearance is preview and recipe/planning metadata; select the actual filament and slicing profile separately. |
| A selected material seems unsuitable for the printer | Check the real printer, filament, environment, and slicer profile. The material label is not a validated temperature, compatibility, or strength recommendation. |

## Export problems

**Choose an export** in the guide and **Review export** in the main controls open the same current-model chooser. **CAD & 3D printing** shows the common geometry downloads; expand **Drawings & source files** for DXF, SVG, PDF and OpenSCAD. These formats remain available even though they are collapsed initially.

If **Save editable project recipe** closes Export instead of downloading, read the validation error and the opened **Independent height check**. Invalid measured height receives focus; an incomplete decision pair focuses its missing input. Correct the notes or clear both optional decision inputs, then save again. Geometry downloads and a valid current CAD model are separate from these optional recipe notes. See the [engineering model](engineering-model.md) for the conditional check.

If a download link has expired, rebuild the current settings to create new artifacts. Download files promptly when you need a persistent copy.

If an STL appears 25.4 times too large or too small, check whether the receiving tool interpreted millimeters as inches or vice versa. If a DXF appears as a flat drawing, that is expected: DXF exports the planar profile, not thickness.

If the printed PDF is the wrong size, print it again at 100 % ("actual size") and not fitted to the page, then measure its two 100 mm rulers. If an SVG imports at the wrong size, the receiving program has ignored the millimetre size the file states; set the document's units to millimetres there, or use the DXF.

If STEP opens without the application's original sketch and extrusion history, that is also expected. Keep the recipe to regenerate the part with new dimensions. See [export formats](exports.md).

If an endpoint reference or independent-height note is absent after restoring a slicer-bundle recipe, use the JSON downloaded through the browser's **Save project** instead. The backend recipe contains build settings and reference-sheet evidence, but omits browser-only endpoint and height-decision notes.

If refreshing the page returns to the sample, restore your downloaded project through **Photo → Browse files**. The application has no automatic project persistence; the saved recipe is the recovery path.

Opening a project replaces the current work only after its CAD build succeeds. If the imported outline is invalid or the service fails, the previous outline, measurements, design settings, and temporary exports remain available. **Try again** retries the selected import; it does not rebuild the previous project. Correct an invalid imported file before retrying it.

## Viewer and startup problems

- **Blank 3D viewer:** confirm that the browser supports WebGL and that a build has actually completed. A text summary or fallback message does not establish that 3D rendering passed.
- **Interface loads but conversion fails:** the frontend can run independently of the API. Use the supplied startup scripts and check the backend output.
- **Port already in use:** identify the existing service before changing ports or stopping it. Avoid terminating an unrelated process.
- **Setup says Python 3.12 is required:** setup looked for `PICAD_PYTHON`, `python3.12`, and `python3`, and none was 3.12. Install Python 3.12 alongside your current Python, or point `PICAD_PYTHON` at an existing 3.12 interpreter. A pyenv `.python-version` message about 3.12 means pyenv has no 3.12; setup can still use a system `python3.12`.
- **Browser tests cannot launch a browser:** install Chromium or Google Chrome, or run `npx playwright install chromium`. `PLAYWRIGHT_CHROMIUM_EXECUTABLE` selects a specific executable.
- **Browser export checks report `spawnSync .venv/bin/python ENOENT`:** prepare the current checkout with `make setup-app`. The test helpers need its root Python environment even when the API starts with an interpreter from another checkout. Preserve failed reports before rerunning.
- **Dependency installation fails:** use the pinned toolchain and lockfiles, inspect the actual package or certificate error, and preserve TLS verification. Do not disable certificate checks to make setup pass.
- **App unavailable after restoring an environment:** prepared files can survive a snapshot; running processes do not. Start the application again.

## Optional local assistant problems

| Symptom | Next action |
| --- | --- |
| Ollama is not connected | Start Ollama on the **CAD backend's machine**, then use **Refresh connection**. A server on your laptop is not reachable through a cloud backend's loopback address. |
| Connected, but no model is available | Download a local model in a terminal, then refresh. The workbench does not install models automatically. See [local AI setup](ollama.md). |
| Pull fails with `403 Forbidden` | Inspect the denied registry/storage host and use the environment's supported network settings flow. A saved proposal is not an applied policy. Preserve TLS verification and the inherited proxy. |
| Port 11434 is already in use | Identify the existing Ollama service and its model directory before starting another. The app lists models from the service it actually reaches. |
| First startup cannot create `~/.ollama` | Allow the current user to create Ollama's identity files through the host's supported permissions mechanism. Do not change the app's source or disable the sandbox to conceal the failure. |
| A response takes too long | Try a smaller installed model and a shorter question. A first response also loads model weights; inference timeout leaves the CAD inputs unchanged. |
| An answer or proposal is outdated | Project inputs changed after the question was sent. Advice-only answers also carry the stale-project notice. Ask again with the current settings; applying an old proposal is blocked. |
| AI cannot send with invalid settings | Follow the deterministic **Next step** correction first. Valid settings that request oversized geometry can still ask for a repair suggestion; applying it remains explicit and validated. |
| The answer seems wrong | Ignore it or undo an applied suggestion. Check the photograph, measured part, and capture guide. A valid response format does not prove the advice is correct. |

## Report a reproducible problem

Include the failing stage, exact error text, input format and approximate dimensions, entered width and thickness with units, browser, operating system, and the relevant application revision. Attach a non-sensitive sample when possible. Avoid uploading confidential parts or credentials to an issue report.
