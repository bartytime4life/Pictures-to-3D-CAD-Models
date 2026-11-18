# Troubleshooting

Use the visible error message and the **Next step** guide to identify the action that is needed. The guide is deterministic input/build state, not AI advice or manufacturing acceptance. Keep the current photograph and dimensions while correcting a recoverable problem; starting over should not be the default recovery strategy. See the [documentation index](README.md) for other tasks and the [capture guide](capture-guide.md) for source preparation.

## Find the next recovery step

| What you see                                     | What to do                                                                                                                                                   |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Build or export unavailable                      | Read **Next step**. Fix the named measurement or setting, then rebuild; an old visible mesh can still be outdated.                                           |
| Flat-part work vanished after a page reload      | Reopen a saved snapshot in **Project library**, or open your downloaded project JSON. Reload clears the current unsaved draft. Keep source photos separately. |
| A desired size will not commit                   | Use a positive target value within supported scale/output limits. Press Enter or leave the field. An invalid draft does not replace the last committed size. |
| The nozzle or process plan is invalid            | Check **Prepare for slicing** and **Printer & split settings**. Layer height must be at least 0.05 mm, at most 1.2 mm and no larger than the nozzle.         |
| Bed rotation did not affect the downloaded model | The bed rotation is an inspection control. Apply the chosen orientation in the receiving slicer.                                                             |
| Background removal looks wrong                   | The cutout follows the current traced outline. Fix or retrace the outline first; switch back to Original for comparison.                                     |
| A command cannot run                             | Close a blocking dialog or finish the current build. Search commands only exposes actions available to the current workspace.                                |

## Knowledge, Science and view controls

| Symptom                                                    | Explanation and recovery                                                                                                                                                         |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bed footprint fits visually but the fit message is unknown | The preview uses a mesh and rectangular envelope. The saved fit check may lack support for that bed's shape/exclusions or curved enclosure. Inspect the native slicer placement. |
| Bed view is not at the suggested angle                     | Use **Use suggested turn** or **Reset view**. The fit result remains unchanged while you inspect another angle.                                                                  |
| Grid or margin is hidden                                   | Re-enable the corresponding checkbox or reset the view. Hiding the margin does not change the actual saved margin value.                                                         |
| Process notes are missing from the slicer UI after import  | This is expected: open `process-plan.json` in the handoff ZIP and enter reviewed values in the native process controls. Neutral geometry does not install a preset.              |
| Notes or scenarios are missing in another browser          | Browser storage belongs to a browser profile and origin. Export/import the relevant file; changing port, hostname or browser may select a different store.                       |
| Saving local notes reports an error                        | Storage may be full or restricted. Keep the visible text and export a copy before reloading; do not assume a success message from another action saved it.                       |
| A Science scenario gives an unexpected result              | Check units, reference spans, sign conventions and assumptions. Reset to the example and edit one input at a time. Scenarios do not modify CAD automatically.                    |
| A scenario file cannot be imported                         | Choose a file exported by the supported scenario format. Preserve the current scenario until the replacement validates.                                                          |
| Camera/grid/wireframe controls do not change exports       | They inspect the existing built mesh. Change model/design settings and rebuild for a changed solid.                                                                              |

## Image and tracing problems

| Symptom                                                                                    | Likely cause                                                                                                             | Next action                                                                                                                                                                                                                                                                                           |
| ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Sheet long edge cannot be identified, metadata disagrees, or sides are too close in length | Perspective permits competing assignments or the assignment lacks the required numerical support.                        | Retake more directly overhead with all corners visible, keep the original uncropped photo and metadata, and use a clearly rectangular measured reference. A refused detected-sheet calibration does not fall back to an uncorrected trace. [Method and limits](validation/sheet-axis-orientation.md). |
| Unsupported or unreadable image                                                            | The bytes are not a supported image, or the file is damaged.                                                             | Export a fresh PNG, JPEG, WebP, HEIC, or AVIF; changing the extension alone does not convert a file. A HEIC that uses a codec other than HEVC is not supported.                                                                                                                                       |
| Upload rejected as too large                                                               | Encoded size or decoded image dimensions exceed the server limit.                                                        | Resize the image before uploading, keeping the relevant boundary sharp.                                                                                                                                                                                                                               |
| A selected reference sheet was not used                                                    | The whole sheet could not be detected or measured, and the initial upload fell back to ordinary tracing with a warning.  | Enter a measured width, or retake the whole flat sheet with all four corners visible and choose the matching **Scale reference**. A fallback does not supply sheet correction or fitted geometry.                                                                                                     |
| The part's outline is not clear enough to measure, even with all sheet corners visible     | The sheet and part were found, but too few outer-edge measurements survived; weak local contrast or blur can cause this. | Retake the photo in focus with stronger contrast between the part and the sheet. Keep the whole sheet visible and use diffuse lighting that leaves the boundary clear. Alternatively choose **None: I will enter a measured width** and review the ordinary trace before relying on it.               |
| Contrast threshold is disabled                                                             | Reference-sheet tracing measures contrast locally.                                                                       | Review sheet choice, foreground interpretation, capture and trace notes. To use manual contrast on an ordinary silhouette, choose **None: I will enter a measured width**.                                                                                                                            |
| No useful outline                                                                          | Low contrast, a blank image, or the wrong foreground interpretation.                                                     | Check the foreground setting and threshold; retake with a plain contrasting background if necessary.                                                                                                                                                                                                  |
| Background selected as the part                                                            | Foreground and background are reversed or merge at the image edge.                                                       | Invert the foreground interpretation and leave a clear margin around the whole part.                                                                                                                                                                                                                  |
| Multiple substantial regions                                                               | Other objects, loose pieces, or a detached part appear in the image.                                                     | Use an image of one intended connected part. Review the warning and selected region.                                                                                                                                                                                                                  |
| Hole missing or false hole present                                                         | Reflection, shadow, texture, or thresholding changed the interior boundary.                                              | Compare the trace with the real part and adjust the threshold or capture. Do not export an unreviewed hole pattern.                                                                                                                                                                                   |
| Outline and image appear rotated differently                                               | Orientation or coordinate handling is incorrect.                                                                         | Re-export the source with its orientation applied and report the reproducible case. The normalized display image and trace should align.                                                                                                                                                              |
| Warning that orientation metadata could not be read                                        | The file's EXIF block is damaged, so the photo was traced as stored rather than rotated.                                 | If the part appears sideways or mirrored, rotate the photo or re-export it with its orientation applied, then trace again.                                                                                                                                                                            |

The [weak-edge recovery check](validation/contrast-recovery.md) records this
specific reference-sheet failure and subsequent successful tracing. Its guidance
does not make an unclear capture measurable or establish dimensional accuracy.

If a very small part is missed on a large reference sheet, use a smaller flat
reference with accurately measured sides and choose **Custom sheet, measured**.
Keep the whole sheet and contrasting margins visible. The
[synthetic capture study](validation/finite-moment-photo.md) retains both the
A4 detection failures and the smaller-sheet outcomes; a successful trace still
needs comparison with independent dimensions.

## Scale and geometry problems

A soft-shadow note means a fitted light model was used; it does not establish
that blur or dimensions are accurate. With zero entered thickness, an accepted
model taking at least 3 % of the light is removed from the profiles before blur
is measured again. Positive-thickness traces retain the previous width path
because of known wall/support failures. Keep the real thickness for your part;
retake with diffuse light and compare critical holes and corners with measured
features. See [shadow correction and remaining failures](reference-sheet.md#3-segmentation-and-sub-pixel-edges).

For a directional-blur note, use a steadier, sharper capture and reserve independent
feature checks. The estimator concerns rectified edge spreads. Normal-specific
edge localization alone does not validate a radius. Supported nonparallel
fillets use the full covariance, while free curves and caps retain separate
approximations; a rank/SPD check does not establish physical measurement accuracy. A missing
directional note can mean insufficient independent direction support; it does
not prove isotropic optics. Two supported directions may still supply separate
edge-search widths without a full covariance; that does not enable directional
corner or curve correction. See [model boundaries](reference-sheet.md#3-segmentation-and-sub-pixel-edges).

A note that curved edges use measurements from both the top and bottom means
the thickness correction applies different maps within their support. Their
retained blur correction is approximate; measure important radii independently.
Mixed scalar corners have unresolved radius uncertainty and cannot justify a
sharp-corner bound. Mixed supplied-covariance nonparallel corners retain the
supported source outline or the existing separately checked geometric fallback;
an invalid unsupported profile is still refused. See [blur frames](blur-frames.md).

An expected circle or arc may remain a traced outline when its initial fit lacks
source support or exceeds the bounded sampling work. This preserves the source
instead of extrapolating unsupported geometry; see the [fit-support check](validation/fit-support.md).
Compare the photograph and important dimensions if an analytic fit or later
design-intent correction disagrees. Use ordinary tracing with measured scale or
rebuild critical features in CAD when needed. Turning off design-intent snapping
does not disable whole-circle fitting or the initial support check.

A later note that a fitted arc could not be joined means the final line/circle
assembly was unavailable or ambiguous. A valid affected boundary stays as traced
lines; other accepted boundaries can remain analytic. This retained outline does
not determine the missing radius. Compare it with the photograph and measure
critical features before export. If the retained boundary cannot form a valid
profile, the request is refused; correct the capture or rebuild the feature in
CAD. The previous successful model can remain visible after that error, so check
the outdated-result notice. See [join recovery](curved-joins.md#when-a-join-cannot-be-constructed)
and [critical arc export checks](exports.md#verify-critical-arc-geometry).

| Symptom                                                  | Likely cause                                                                                      | Next action                                                                                                                                                                                            |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Width is correct but height is wrong                     | Perspective, image distortion, or a reference width that does not match the full horizontal span. | Review [calibration](capture-guide.md), retake front-on, and compare a second physical measurement.                                                                                                    |
| Thickness does not match the part                        | The app uses the entered thickness, not a thickness inferred from the photo.                      | Measure and enter the constant thickness separately.                                                                                                                                                   |
| Invalid profile or solid                                 | Boundaries intersect, touch incorrectly, or form unsupported topology.                            | Simplify the source, adjust tracing, and inspect small features or near-touching holes.                                                                                                                |
| Build is busy                                            | Another geometry conversion is using the bounded worker.                                          | Let it finish, then retry. Repeated rapid submissions will not speed it up.                                                                                                                            |
| Temporary model storage is full                          | The service has reached its model-directory cap.                                                  | Download any needed files, then use **Capture guide → Clear temporary exports** and rebuild. This clears all completed exports on this instance.                                                       |
| Build times out                                          | The profile is unusually complex or the kernel cannot complete it in the permitted time.          | Try a coarser outline and remove irrelevant visual texture from the source.                                                                                                                            |
| Preview is marked outdated or footer says Rebuild needed | Editable source/design settings changed after the last successful build.                          | Use **Next step → Update preview** to rebuild and inspect without opening Export; **Update model** builds and opens export review. An old preview is not confirmation that the new settings succeeded. |
| Build or export is disabled after collapsing settings    | A required measurement or design/print value is invalid.                                          | Read the cause in **Next step**. **Enter width**, **Enter thickness** or **Fix design settings** takes you to the existing control/panel.                                                              |
| Old result remains after an error                        | The app preserved a previous successful result for recovery.                                      | Correct the current input and rebuild; do not assume the visible model reflects the failed change.                                                                                                     |

## Design and print planning

| Symptom                                                           | Next action                                                                                                                                                                                                  |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| The sample shows a usable model before I enter measurements       | The sample uses demonstration inputs of 80 mm width and 4 mm thickness, labeled above the workbench. Upload your own part and supply its measured scale and thickness before relying on its output.          |
| Resulting size differs from the measured reference                | Check the explicit XY and thickness design percentages. At 100%, each keeps the corresponding measured size; a different percentage deliberately changes the design without changing its source measurement. |
| Small feature changes after choosing relative detail              | Compare against the original-detail build. Detail modes can simplify geometry; a larger nozzle or smoother display cannot recover missing photo detail.                                                      |
| A printer says the part is too large                              | Check the actual usable X/Y/Z volume and margin. Choose another printer or a reviewed split plan. Scaling changes the part's physical size and is a separate decision.                                       |
| Geometric bounds fit but the slicer rejects placement             | Check supports, brim/raft/skirt, excluded bed areas, clearance, and machine settings in the slicer. A rectangular fit check does not model them.                                                             |
| Split pieces still look assembled in the preview or combined file | That is expected. Use the per-part ZIP to import pieces separately; the combined mesh/STEP is not a spaced print-bed layout.                                                                                 |
| Pieces need a way to join                                         | The generated cuts are straight divisions. Design and validate your own joints, fastening, clearance, and assembly plan before fabrication.                                                                  |
| Preview color is absent from STL                                  | STL does not preserve color/material. The selected appearance is preview and recipe/planning metadata; select the actual filament and slicing profile separately.                                            |
| A selected material seems unsuitable for the printer              | Check the real printer, filament, environment, and slicer profile. The material label is not a validated temperature, compatibility, or strength recommendation.                                             |

## Export problems

**Choose an export** in the guide and **Review export** in the main controls open the same current-model chooser. **CAD & 3D printing** shows the common geometry downloads; expand **Drawings & source files** for DXF, SVG, PDF and OpenSCAD. These formats remain available even though they are collapsed initially.

If **Save editable project recipe** closes Export instead of downloading, read the validation error and the opened **Independent height check**. Invalid measured height receives focus; an incomplete decision pair focuses its missing input. Correct the notes or clear both optional decision inputs, then save again. Geometry downloads and a valid current CAD model are separate from these optional recipe notes. See the [engineering model](engineering-model.md) for the conditional check.

If a download link has expired, rebuild the current settings to create new artifacts. Download files promptly when you need a persistent copy.

If an STL appears 25.4 times too large or too small, check whether the receiving tool interpreted millimeters as inches or vice versa. If a DXF appears as a flat drawing, that is expected: DXF exports the planar profile, not thickness.

If the printed PDF is the wrong size, print it again at 100 % ("actual size") and not fitted to the page, then measure its two 100 mm rulers. If an SVG imports at the wrong size, the receiving program has ignored the millimetre size the file states; set the document's units to millimetres there, or use the DXF.

If STEP opens without the application's original sketch and extrusion history, that is also expected. Keep the recipe to regenerate the part with new dimensions. See [export formats](exports.md).

If an endpoint reference or independent-height note is absent after restoring a slicer-bundle recipe, use the JSON downloaded through the browser's **Save project** instead. The backend recipe contains build settings and reference-sheet evidence, but omits browser-only endpoint and height-decision notes.

If refreshing the page returns to the sample, use **Project library → Open in workbench** on a saved snapshot or restore a downloaded project through **Photo → Browse files**.

Opening a project replaces the current work only after its CAD build succeeds. If the imported outline is invalid or the service fails, the previous outline, measurements, design settings, and temporary exports remain available. **Try again** retries the selected import; it does not rebuild the previous project. Correct an invalid imported file before retrying it.

## Flat-part Project library

| What you see | What to do |
| --- | --- |
| **Save current snapshot** is unavailable | Finish tracing, enter valid dimensions and settings, and wait for any active operation to finish. Check browser site-storage permissions if the library itself reports an error. |
| Saving reports a height-check error | Close the dialog and correct the independent height or its decision fields. Clear both optional decision fields if you only want to save the measured height. |
| A snapshot is missing | Clear the search and print-status filter. Check the browser profile and app address used when saving, including protocol, hostname and port. A downloaded recipe can restore the model inputs. |
| A recipe opened with no print history | Use the original snapshot in its browser profile and origin. The recipe contains editable model inputs, and the library entry contains the print log. |
| Saving again selects the previous snapshot | An identical recipe reuses its existing entry. Save a changed recipe to create a version with its own status and history. |

See [saving snapshots and recording prints](workflows.md#save-snapshots-and-record-prints).

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

| Symptom                                 | Next action                                                                                                                                                                                       |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ollama is not connected                 | Start Ollama on the **CAD backend's machine**, then use **Refresh connection**. A server on your laptop is not reachable through a cloud backend's loopback address.                              |
| Connected, but no model is available    | Download a local model in a terminal, then refresh. The workbench does not install models automatically. See [local AI setup](ollama.md).                                                         |
| Pull fails with `403 Forbidden`         | Inspect the denied registry/storage host and use the environment's supported network settings flow. A saved proposal is not an applied policy. Preserve TLS verification and the inherited proxy. |
| Port 11434 is already in use            | Identify the existing Ollama service and its model directory before starting another. The app lists models from the service it actually reaches.                                                  |
| First startup cannot create `~/.ollama` | Allow the current user to create Ollama's identity files through the host's supported permissions mechanism. Do not change the app's source or disable the sandbox to conceal the failure.        |
| A response takes too long               | Try a smaller installed model and a shorter question. A first response also loads model weights; inference timeout leaves the CAD inputs unchanged.                                               |
| An answer or proposal is outdated       | Project inputs changed after the question was sent. Advice-only answers also carry the stale-project notice. Ask again with the current settings; applying an old proposal is blocked.            |
| AI cannot send with invalid settings    | Follow the deterministic **Next step** correction first. Valid settings that request oversized geometry can still ask for a repair suggestion; applying it remains explicit and validated.        |
| The answer seems wrong                  | Ignore it or undo an applied suggestion. Check the photograph, measured part, and capture guide. A valid response format does not prove the advice is correct.                                    |

## Photo library problems

| Symptom                                        | Next action                                                                                                                                                                                                                     |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Add folder** is missing                      | Folders can be named only from the workbench page on the same computer as the backend, and not with `PICAD_LIBRARY_FOLDERS=0`. Use **Add photos**, or open the app at its loopback address on that computer.                    |
| The header says **Vision model off**           | Open it for the reason. Install with `./scripts/vision-model.sh install --weights FOLDER` after requesting the weights from Meta, then restart the workbench. `./scripts/vision-model.sh status` shows what is verified.        |
| A weight file is "not verified"                | The file is damaged or is not one of the four supported LVD-1689M ViT backbones. Download it again; the name ends with the first eight digits of its SHA-256.                                                                   |
| The vision model "could not start"             | The message carries the last line of `.local/vision-model/worker.log`. A graphics driver PyTorch cannot use falls back when `PICAD_VISION_DEVICE=cpu` is set; install the ViT-S/16 weights for processor use.                   |
| No groups, or every photo alone                | Groups need the vision model and at least two photos of one subject. Photos of one part against very different surroundings can stay apart.                                                                                     |
| Two different parts share a group              | Parts that look alike can be grouped together. Groups are suggestions; choose the photo by eye.                                                                                                                                 |
| A photo has no edge blur                       | It has too few clear edges, as icons and plain graphics do. It is still indexed and sorted last by sharpness.                                                                                                                   |
| **Not read** lists files                       | Each shows its reason: over 32 MiB, over 70 megapixels, an animation, or a damaged file. Fix or remove the file and choose **Rescan**.                                                                                          |
| A crunch is slow                               | Reading is limited by memory traffic for large PNG and HEIC files, which are decoded in full. `PICAD_LIBRARY_WORKERS` sets the number of reader processes. Without a graphics card, describing is far slower; install ViT-S/16. |
| "The original file has changed" on **Open in** | The file was edited or moved after indexing. Choose **Rescan**.                                                                                                                                                                 |

## Developer numerical operators

For developer-only source-cell predictions, use the
[input and resource contract](finite-acquisition-mean.md#refusals-provenance-and-work).
`work_limit` means the whole grid was refused before stage evaluation; returned
`None` values are unknown, not black pixels. `ValueError` identifies invalid
inputs; `ArithmeticError` withholds an unresolved numerical result. A `resolved`
prediction with `adequacy="not_evaluated"` does not validate the camera model or
recover geometry. These Python operators do not add an interface mode.

The separate [area sensitivities and linear propagation](finite-cell-sensitivity.md)
use different result contracts: unknown cell Jacobians are NaN with explicit
statuses, while a refused linear call has absent arrays. Inspect every status
before assembling fields. Replacing unknown derivatives by zeros changes the
model. Neither API supplies a five-geometry-parameter fitter.

## Report a reproducible problem

Include the failing stage, exact error text, input format and approximate dimensions, entered width and thickness with units, browser, operating system, and the relevant application revision. Attach a non-sensitive sample when possible. Avoid uploading confidential parts or credentials to an issue report.
