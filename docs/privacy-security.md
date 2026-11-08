# Data handling and security boundaries

## Where photos go

The browser uploads the selected photograph to the app's Python backend for decoding and tracing. A backend on your computer processes it on that computer. A backend in a cloud environment receives the upload in that environment.

The conversion workflow does not send photographs to an external AI service. This is different from a claim that photos never leave the browser or device.

The tracing response includes a normalized image so the browser can align the outline with the displayed pixels. The upload is closed after reading, and the original is not retained as a permanent project file. The normalized response omits source image metadata. The photograph can still be present in browser memory while the workbench is open.

## Temporary artifacts and saved projects

Generated meshes, CAD files, and recipe data are stored under `.local/jobs` by default; `PICTURES_CAD_JOB_DIR` can select another directory. The running service expires model directories after **one hour**, checks expiry on startup and builds, and runs a cleanup check every **60 seconds**. It caps stored model directories at 20 per process. The API supports deletion of one model with `DELETE /api/models/{job_id}`, or all completed temporary models with `DELETE /api/models`. Clearing all models is blocked while a CAD build is active.

Download the exports you want to retain; a temporary artifact URL is not durable project storage. Cleanup depends on the service running. Stopping the service, taking a filesystem snapshot, or backing up its storage can retain files beyond the running service's intended lifetime.

The interface releases superseded builds after a replacement succeeds. **Capture guide → Clear temporary exports** deletes all completed generated files on this instance, including the current model's files. Your current outline and dimensional inputs remain in the browser; rebuild to export again. Copies already downloaded are unaffected.

The project recipe preserves geometry and settings for regeneration and excludes the photograph. Keep the original source image separately when you need a record of how the model was derived. Saving a local recipe does not create a cloud account, synchronize another device, or provide a backup service.

There is no automatic project persistence across page refreshes. Download a recipe before leaving the workbench if you need to recover its current settings.

Browser downloads are governed by the browser and host environment. Deleting an artifact from the running app does not delete copies already downloaded or stored in a host backup or environment snapshot.

## Input and execution boundaries

The backend validates the decoded image format and dimensions rather than trusting a filename extension alone. It limits upload and geometry size, rejects invalid dimensional inputs, and checks planar geometry before running CAD operations.

CAD construction runs with bounded execution and concurrency. Export routes accept the supported artifact types and generated identifiers; user project names are not filesystem paths.

These controls reduce accidental resource exhaustion and malformed-input failures. They are not a substitute for authentication and resource isolation when serving untrusted users.

## Single-user scope

The included application has no account system or per-user authorization. Keep its access consistent with a single-user workbench. A random artifact identifier is not an authorization policy.

Before hosting it as a shared public service, implement and test authentication, authorization, request quotas, durable job isolation, explicit retention, deletion guarantees, and operational monitoring. Also define which administrators and infrastructure providers can access uploads and generated parts.

## Logs and sensitive parts

Do not place image contents, CAD payloads, credentials, or raw environment dumps in support reports. A useful report normally needs the operation, error text, relevant software version, and a non-sensitive reproduction image.

The app does not require third-party API keys for conversion. If future integrations add credentials, store them through the hosting environment's supported secret mechanism rather than embedding them in a project recipe or frontend bundle.
