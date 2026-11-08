# Troubleshooting

Use the visible error message and the stage that failed. Keep the current photograph and dimensions while correcting a recoverable problem; starting over should not be the default recovery strategy.

## Image and tracing problems

| Symptom | Likely cause | Next action |
| --- | --- | --- |
| Unsupported or unreadable image | The bytes are not a supported image, or the file is damaged. | Export a fresh PNG, JPEG, or WebP; changing the extension alone does not convert a file. |
| Upload rejected as too large | Encoded size or decoded image dimensions exceed the server limit. | Resize the image before uploading, keeping the relevant boundary sharp. |
| No useful outline | Low contrast, a blank image, or the wrong foreground interpretation. | Check the foreground setting and threshold; retake with a plain contrasting background if necessary. |
| Background selected as the part | Foreground and background are reversed or merge at the image edge. | Invert the foreground interpretation and leave a clear margin around the whole part. |
| Multiple substantial regions | Other objects, loose pieces, or a detached part appear in the image. | Use an image of one intended connected part. Review the warning and selected region. |
| Hole missing or false hole present | Reflection, shadow, texture, or thresholding changed the interior boundary. | Compare the trace with the real part and adjust the threshold or capture. Do not export an unreviewed hole pattern. |
| Outline and image appear rotated differently | Orientation or coordinate handling is incorrect. | Re-export the source with its orientation applied and report the reproducible case. The normalized display image and trace should align. |

## Scale and geometry problems

| Symptom | Likely cause | Next action |
| --- | --- | --- |
| Width is correct but height is wrong | Perspective, image distortion, or a reference width that does not match the full horizontal span. | Review [calibration](capture-guide.md), retake front-on, and compare a second physical measurement. |
| Thickness does not match the part | The app uses the entered thickness, not a thickness inferred from the photo. | Measure and enter the constant thickness separately. |
| Invalid profile or solid | Boundaries intersect, touch incorrectly, or form unsupported topology. | Simplify the source, adjust tracing, and inspect small features or near-touching holes. |
| Build is busy | Another geometry conversion is using the bounded worker. | Let it finish, then retry. Repeated rapid submissions will not speed it up. |
| Temporary model storage is full | The service has reached its model-directory cap. | Download any needed files, then use **Capture guide → Clear temporary exports** and rebuild. This clears all completed exports on this instance. |
| Build times out | The profile is unusually complex or the kernel cannot complete it in the permitted time. | Try a coarser outline and remove irrelevant visual texture from the source. |
| Preview is marked outdated | Geometry-affecting settings changed after the last successful build. | Rebuild before exporting. An old preview is not confirmation that the new settings succeeded. |
| Old result remains after an error | The app preserved a previous successful result for recovery. | Correct the current input and rebuild; do not assume the visible model reflects the failed change. |

## Export problems

If a download link has expired, rebuild the current settings to create new artifacts. Download files promptly when you need a persistent copy.

If an STL appears 25.4 times too large or too small, check whether the receiving tool interpreted millimeters as inches or vice versa. If a DXF appears as a flat drawing, that is expected: DXF exports the planar profile, not thickness.

If STEP opens without the application's original sketch and extrusion history, that is also expected. Keep the recipe to regenerate the part with new dimensions. See [export formats](exports.md).

If refreshing the page returns to the sample, restore your downloaded project through **Photo → Browse files**. The application has no automatic project persistence; the saved recipe is the recovery path.

## Viewer and startup problems

- **Blank 3D viewer:** confirm that the browser supports WebGL and that a build has actually completed. A text summary or fallback message does not establish that 3D rendering passed.
- **Interface loads but conversion fails:** the frontend can run independently of the API. Use the supplied startup scripts and check the backend output.
- **Port already in use:** identify the existing service before changing ports or stopping it. Avoid terminating an unrelated process.
- **Dependency installation fails:** use the pinned toolchain and lockfiles, inspect the actual package or certificate error, and preserve TLS verification. Do not disable certificate checks to make setup pass.
- **App unavailable after restoring an environment:** prepared files can survive a snapshot; running processes do not. Start the application again.

## Report a reproducible problem

Include the failing stage, exact error text, input format and approximate dimensions, entered width and thickness with units, browser, operating system, and the relevant application revision. Attach a non-sensitive sample when possible. Avoid uploading confidential parts or credentials to an issue report.
