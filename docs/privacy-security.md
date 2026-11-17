# Data handling and security boundaries

[Documentation index](README.md) · [Local AI controls](ollama.md) · [Engineering model](engineering-model.md)

## Where photos go

The browser uploads the selected photograph to the app's Python backend for decoding and tracing. A backend on your computer processes it on that computer. A backend in a cloud environment receives the upload in that environment.

The conversion workflow does not send photographs to an external AI service. This is different from a claim that photos never leave the browser or device.

The tracing response includes a normalized image so the browser can align the outline with the displayed pixels. The upload is closed after reading, and the original is not retained as a permanent project file. The normalized PNG omits the original image metadata. The decoder can use orientation and 35 mm-equivalent focal-length metadata for tracing; reference-sheet provenance can retain a derived camera height and the focal source (`sheet`, `exif`, `assumed` or `holes`). With entered thickness, suitable holes assumed round can supply the height estimate when the sheet and metadata do not. The recipe does not embed the original EXIF block. The selected file and normalized photograph can remain in browser memory while the workbench is open.

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

The interface releases superseded builds after a replacement succeeds. **Capture guide → Clear temporary exports** deletes all completed generated files on this instance, including files for both Flat part and Relief. In the current page, both studios retain their editable inputs and require a new build before exporting again. Relief keeps its source picture and settings and shows explicit rebuild guidance; switching back to it does not recreate files automatically. A failed cleanup preserves the existing exports. Copies already downloaded are unaffected.

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

Bambu Studio, PrusaSlicer, QIDI Studio, OrcaSlicer and UltiMaker Cura handoff downloads include generated geometry, the editable outline recipe and printer/material/process planning notes. They do not include the original photograph or assistant conversation. Neutral 3MF files contain geometry without native slicing settings.

The optional host launcher is disabled by default. Explicit local opening accepts only the five registered program IDs (`bambu`, `prusa`, `qidi`, `orca`, `cura`), configured installed executables and a generated model ID. It requires same-origin JSON over HTTP from a loopback client/host and uses an argument array without a shell. HTTPS loopback and remote workbenches use handoff ZIP downloads instead. Opening requests do not slice, send G-code, or contact a printer. Once open, the external slicer runs with its own settings and permissions.

A retained copy under `.local/slicer-handoffs/` (or `PICAD_SLICER_HANDOFF_DIR`) survives temporary-job expiry and Clear temporary exports. These copies stay local and remain until manually removed. Discovery does not execute any of these programs or verify their versions; the interface distinguishes launch requests from confirmed native imports.

## Browser notes, scenarios and documentation

Knowledge notebook notes/pins and valid Science scenarios save to this browser profile's local storage for the application's origin. They are independent of CAD project recipes, temporary model cleanup and the photo library. Clearing site data can remove them; their JSON exports provide portable copies. A different browser, profile, host name or port can have separate saved state. Do not treat browser storage as encrypted or backed up.

These learning tools do not send notes or scenarios to the CAD backend or apply them to model settings. The local documentation API reads a fixed allowlist of repository guides and supplies their Markdown text, checksum and download. It does not accept arbitrary file paths. Following an external research or repository link opens that external service under its own policies.

Background removal clips the current working photo using the reviewed outline in the browser. Its transparent PNG is separate from geometry and does not change the original file. The original trace/upload still follows the ordinary backend processing described above.

## Photo library

The photo library keeps derived data until you remove it, unlike built models, which expire after an hour. Under `.local/library` (or `PICAD_LIBRARY_DIR`) it stores a SQLite catalogue with each photo's path, name, SHA-256, size, capture time and camera model, a JPEG preview of at most 512 pixels with no metadata, edge-blur measurements, and, with the optional vision model, feature vectors and a 28 × 28 subject region. Location tags are never read. A photo added through the browser is stored whole under `uploads` there with owner-only permissions, because no other copy is reachable. **Remove** on a folder or an uploaded photo, or **Clear library**, deletes that derived data; files in your own folders are never changed, moved or deleted.

A page can name a folder on the host only when the request comes from a loopback client to a loopback host, with a same-origin `Origin` and a JSON body: the gate used for opening a slicer. Another site's page, a form post and another computer are refused. `PICAD_LIBRARY_FOLDERS=0` turns folder access off entirely. Every route that changes the library, uploads and picture searches included, also refuses a browser request whose `Origin` is not this service, so another site's page cannot post files into a library on this computer. Anyone who can reach the page on the host itself can browse folder names and add any folder that the backend's user can read, so keep the default loopback address for personal collections. Linked folders are not followed and hidden folders are skipped. An original is served back only while its size and modification time match what was indexed.

Photos are decoded with the workbench's decoders and limits in separate reader processes; a file that fails is listed with its reason and does not stop the rest. A CSV export writes cells that a spreadsheet would run as a formula as text.

The optional DINOv3 model runs in its own process on this computer with no network access. Its weights are never downloaded by this project: `./scripts/vision-model.sh` links files you obtained from Meta after checking each against a pinned SHA-256, the workbench checks again before every load, and the file is read as tensors only (`weights_only=True`), not as executable pickle code. Installing PyTorch and the DINOv3 code does download packages, from the Python package index and the DINOv3 repository at one pinned commit, into `.local/vision-env`. A separate process contains crashes; it is not a security sandbox. A picture used for **Search by picture** is described and discarded.

## Relief studio and Blender handoff

A relief or lithophane upload is written to its private job folder, read once by the worker and deleted before the surface is computed. The derived height map, meshes and Blender ZIP stay with the temporary exports and expire with them. Recipes and Blender ZIPs contain settings and geometry, never the source picture. The preview image returned to the browser is computed from the thickness map, not copied from the upload.

The Blender launcher is disabled by default (`PICAD_ENABLE_BLENDER_LAUNCH=1` enables it). It runs only the repository's static `build_relief.py`, whose bytes are checked against the repository file by the test suite, with the generated JSON and PNG beside it. Project names and other settings are data in `relief.json`, never code. The ZIP's members must match a fixed list of flat names before anything is extracted. Requests need same-origin JSON from a loopback client and use an argument array without a shell; `PICAD_BLENDER` must be one absolute executable path. Retained copies under `.local/blender-handoffs/` remain until you remove them. Once open, Blender runs with its own settings and permissions.

The optional AI depth model runs inside the same worker, on the CPU, with no network access. It is downloaded only when you run `./scripts/depth-model.sh install`, from a pinned Hugging Face revision, and its SHA-256 is checked both by the script and before every load; a mismatched file is refused. The estimated depth map (`depth-estimate.png`) is derived from the upload like the height map and expires with the other temporary exports. `GET /api/relief/depth` reports availability without reporting the file's location.
