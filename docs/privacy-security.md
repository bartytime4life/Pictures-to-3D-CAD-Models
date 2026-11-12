# Data handling and security boundaries

[Documentation index](README.md) · [Local AI controls](ollama.md) · [Engineering model](engineering-model.md)

## Where photos go

The browser uploads the selected photograph to the app's Python backend for decoding and tracing. A backend on your computer processes it on that computer. A backend in a cloud environment receives the upload in that environment.

The conversion workflow does not send photographs to an external AI service. This is different from a claim that photos never leave the browser or device.

The tracing response includes a normalized image so the browser can align the outline with the displayed pixels. The upload is closed after reading, and the original is not retained as a permanent project file. The normalized PNG omits the original image metadata. The decoder can use orientation and 35 mm-equivalent focal-length metadata for tracing; reference-sheet provenance can retain a derived camera height and the focal source (`sheet`, `exif` or `assumed`). It does not embed the original EXIF block in the recipe. The selected file and normalized photograph can remain in browser memory while the workbench is open.

## Optional local assistant

When you ask a question, the browser sends that text and bounded project context to the CAD backend: entered measurements when present, trace settings, detected hole count, warnings, image/model presence flags, design and printer settings, and dimensions of the available built geometry and parts. The backend forwards those fields and bounded relevant printer-catalog facts to a local Ollama server. It does not forward photographs, outline vertices, CAD meshes, or exported files.

The assistant's inference endpoint must be HTTP loopback on the backend machine. The included startup helper disables Ollama cloud features, and the application rejects cloud models. There is no paid API fallback. On a cloud-hosted workbench, the backend and Ollama still run on that cloud host; “local” does not mean the question stays on your device.

This assistant path is text-only even when a selected model supports vision.
Opening its panel for the first time or refreshing the connection checks installed models; a chat
request is sent only after **Ask local AI**. The workbench's **Next step** guide
uses local interface state and does not require an AI request. See the
[guided-workbench review](validation/guided-workbench.md) for the tested controls.

Questions and answers are not added to saved project recipes or stored by this app as conversation history. They can remain in browser/process memory while in use. Host administrators, process debugging, external logging configuration, or environment snapshots have their own access and retention properties. Avoid entering confidential information unless that host is appropriate for it.

Model downloads contact the configured Ollama registry and storage hosts. Once weights are installed, local inference does not require a hosted AI service. Downloaded weights remain on disk until removed and have their own licenses. See [local AI setup](ollama.md).

An AI response is untrusted advice. The application validates its limited trace/design/print-setting proposal separately from its prose. It does not execute generated code, overwrite source measurements, build geometry, or export files from a response. A proposed design-scale change can alter resulting dimensions only after the user applies it and rebuilds. The user must review the resulting geometry and print plan.

Changes to project inputs mark an unapplied answer outdated, including an answer
without a proposal. A stale proposal cannot be applied. Invalid design fields
prevent sending a question with an explanation; a supported set of fields whose
requested geometry is oversized can still receive a repair suggestion. Undo
waits for an active CAD or Apply operation, rather than treating a geometry-size
error as work in progress. These controls do not establish the truth of the prose.

Applying a retrace with a two-point reference retains the user's measured feature length and endpoints. It recalculates the derived outside width for the new outline. The browser's endpoint calibration, independent height measurement and optional height-decision allowance/error bound are not included in assistant context or the CAD build request. Their saved form is described below.

## Temporary artifacts and saved projects

Generated meshes, CAD files, and recipe data are stored under `.local/jobs` by default; `PICTURES_CAD_JOB_DIR` can select another directory. The running service expires model directories after **one hour**, checks expiry on startup and builds, and runs a cleanup check every **60 seconds**. Expiry removes only UUID-named directories containing a job file this service writes (`input.json`, `result.json`, or `error.json`); directories without those markers are left in place. A failed cleanup check is logged and retried at the next interval. New builds are refused when 20 UUID-named directories are present, counting those without a marker too; existing models are not evicted to make room. The API supports deletion of one model with `DELETE /api/models/{job_id}`, or all completed temporary models with `DELETE /api/models`. The workbench requests deletion of its own current model when the page is closed or reloaded; that browser request is best effort, so expiry remains a fallback. Clearing all models is blocked while a CAD build is active.

Download the exports you want to retain; a temporary artifact URL is not durable project storage. Cleanup depends on the service running. Stopping the service, taking a filesystem snapshot, or backing up its storage can retain files beyond the running service's intended lifetime.

The interface releases superseded builds after a replacement succeeds. **Capture guide → Clear temporary exports** deletes all completed generated files on this instance, including the current model's files. Your current outline and dimensional inputs remain in the browser; rebuild to export again. Copies already downloaded are unaffected.

The browser's **Save project** / **Save editable project recipe** download preserves the source outline, measured width/thickness, design settings, color/material choices, and printer/split plan. It uses version 2 for polygon outlines or version 3 when fitted primitives/reference-sheet provenance are present. When entered, it also preserves two-point calibration, independent height measurement, and the height-decision allowance/error bound. It excludes the photograph and assistant conversation. This JSON is assembled in the browser; saving it does not upload those extra measurement notes to the backend.

The backend also writes a build recipe as `project.json`, used in export/handoff bundles. That recipe retains the submitted profile, dimensions and build provenance, including fitted/reference-sheet data where present; versions 2 and 3 also retain resolved design settings. It does not add the browser-only two-point calibration or height-check notes. Use the browser's editable-project save when those notes need to be retained. See [export contents](exports.md).

Keep the original source image separately when you need a record of how the model was derived. Saving a local recipe does not create a cloud account, synchronize another device, or provide a backup service.

There is no automatic project persistence across page refreshes. Download a recipe before leaving the workbench if you need to recover its current settings.

Browser downloads are governed by the browser and host environment. Deleting an artifact from the running app does not delete copies already downloaded or stored in a host backup or environment snapshot.

## Input and execution boundaries

The backend validates the decoded image format and dimensions rather than trusting a filename extension alone. It limits upload and geometry size, rejects invalid dimensional inputs, and checks planar geometry before running CAD operations.

HEIC photos are decoded in a short-lived child process, not in the service. Their decoders (libheif and libde265, through pi-heif) are native code, and a damaged file can crash them: changing two bytes of a valid file caused a segmentation fault in pi-heif 1.4.0 while it read the file's metadata. In the child, a crash, a timeout or an oversized image becomes an ordinary refusal and the service keeps running. This contains failures; it is not a security sandbox, because the child runs as the same user with the same file access. PNG, JPEG, WebP and AVIF are decoded in the service by Pillow.

CAD construction runs with bounded execution and concurrency. Export routes accept the supported artifact types and generated identifiers; user project names are not filesystem paths.

These controls reduce accidental resource exhaustion and malformed-input failures. They are not a substitute for authentication and resource isolation when serving untrusted users.

## Single-user scope

The included application has no account system or per-user authorization. Keep its access consistent with a single-user workbench. A random artifact identifier is not an authorization policy.

Before hosting it as a shared public service, implement and test authentication, authorization, request quotas, durable job isolation, explicit retention, deletion guarantees, and operational monitoring. Also define which administrators and infrastructure providers can access uploads and generated parts.

## Logs and sensitive parts

Do not place image contents, CAD payloads, credentials, or raw environment dumps in support reports. A useful report normally needs the operation, error text, relevant software version, and a non-sensitive reproduction image.

The app does not require third-party API keys for conversion. If future integrations add credentials, store them through the hosting environment's supported secret mechanism rather than embedding them in a project recipe or frontend bundle.

## Local slicer handoff

Bambu Studio and PrusaSlicer handoff downloads include generated geometry, the editable outline recipe and printer/material planning notes. They do not include the original photograph or assistant conversation. Neutral 3MF files contain geometry without native slicing settings.

The optional host launcher is disabled by default. Explicit local opening accepts only two fixed program IDs, configured installed executables and a generated model ID. It requires same-origin JSON from a loopback client/host and uses an argument array without a shell. Opening requests do not slice, send G-code, or contact a printer. Once open, the external slicer runs with its own settings and permissions.

A retained copy under `.local/slicer-handoffs/` (or `PICAD_SLICER_HANDOFF_DIR`) survives temporary-job expiry and Clear temporary exports. These copies stay local and remain until manually removed. Discovery does not execute either program or verify its version; the interface distinguishes launch requests from confirmed native imports.
