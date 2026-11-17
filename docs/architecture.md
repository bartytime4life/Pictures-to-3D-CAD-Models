# Architecture

Pictures to CAD separates measurements, editable design settings, generated geometry and downstream printing. Browser controls select a requested model; a bounded backend worker constructs the solid; the viewer and export files come from that successful build.

## Workspaces and data flow

```mermaid
flowchart LR
    P[Photo or saved recipe] --> W[Flat-part workspace]
    W --> T[Trace API: outline and holes]
    T --> M[Review source scale and thickness]
    M --> D[Editable design and process plan]
    D --> B[Build API and isolated CAD worker]
    B --> V[Current mesh and fit results]
    B --> E[Geometry, recipe and handoff ZIPs]
    E --> S[Native slicer: review settings and slice]
    L[Photo library] --> W
    L --> R[Relief workspace and mesh worker]
    K[Knowledge and Science lab] --> M
```

The hash router exposes Shape designer (`#designer`), Flat part (`#workbench`), Relief (`#relief`), Photo library (`#library`), Knowledge (`#knowledge`) Science lab (`#science`) and Creative tools (`#creative`). OpenSCAD links to the separately served companion library. Visited studio state is retained in memory during in-page navigation; this is not automatic disk persistence.

## Component map

| Area                       | Main source                                                                | Responsibility                                                                   |
| -------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Application routing        | `frontend/src/main.tsx`                                                    | Select and retain visited workspaces                                             |
| Flat-part orchestration    | `frontend/src/App.tsx`                                                     | Trace/build requests, measurements, revisions, import/export and recovery        |
| Design and process editing | `QuickEdit.tsx`, `PrintSettings.tsx`, `PrintPreparation.tsx`, `design.ts`  | Commit validated settings, inspect printer bounds and carry process notes        |
| Settings history           | `designHistory.ts`                                                         | Bounded snapshots of design settings; no export-file ownership                   |
| Geometry visualization     | `ModelViewer.tsx`, `plateInspection.ts`                                    | Camera/mesh inspection and top-down projection; no mutation of exported geometry |
| Photo cutout               | `BackgroundRemoval.tsx`, `background.ts`                                   | Browser-local outline clipping and transparent PNG generation                    |
| Learning tools             | `KnowledgeStudio.tsx`, `ScienceStudio.tsx`, `science.ts`                   | Searchable guidance, local notebooks and explicit numerical scenarios            |
| Local documentation        | `backend/documentation.py`                                                 | Read-only allowlisted Markdown guides, checksums and downloads                   |
| HTTP service               | `backend/app.py`, `backend/models.py`                                      | Bounded request contracts, job lifecycle, controlled downloads and local bridges |
| CAD construction           | `backend/worker.py`                                                        | Scale profile, prepare/split, construct CadQuery solids and export artifacts     |
| Fit planning               | `backend/printing.py`, `backend/placement.py`, `backend/curve_envelope.py` | Resolve catalog bounds and test per-piece containment                            |
| Slicer handoff             | `backend/slicer_handoff.py`, `backend/slicers.py`                          | Neutral packages, planning notes, hashes and optional fixed-program launch       |
| Relief and photo library   | `backend/relief.py`, `backend/library.py`, associated workers              | Separate image/mesh and persistent-photo workflows                               |

The [detailed API and geometry contracts](api-reference.md) describe request fields, geometry conventions, algorithms and HTTP responses. The [research index](research-index.md) links developer-only numerical APIs and archived experiments; their existence does not imply a browser feature or automatic tracing step.

## Geometry and plan boundaries

Image coordinates use the working photo's pixel frame. The worker translates the source about its center, scales into millimeters and reverses image Y to construct the CAD XY plane. Measured reference width and thickness remain recipe inputs; design percentages determine the requested output size.

Accepted fitted profiles can preserve line/arc/circle geometry. Other profiles become polygon extrusions. Detail reduction is a bounded geometric simplification tied to nozzle size, not recovered photo detail. Splits produce real solids with straight cut faces; combined files preserve assembly coordinates and individual files normalize their own XY origin.

Printer fit resolves the selected profile and checks each flat piece independently. Supported rectangular placement uses a continuous-angle search; fitted outlines use conservative bounds and retain unknown states when an enclosure is inconclusive. A positive result supplies a suggested counterclockwise XY angle. Bed inspection independently projects the preview mesh at the user's selected angle; that view never changes the saved fit result or file orientation.

Process settings are `layer_height_mm`, `wall_count`, `infill_percent`, `supports` and `adhesion`. Backend and frontend validate ranges; layer height cannot exceed the nozzle. Older recipes get defaults. The worker writes the plan into the design recipe and each handoff's hash-verified `process-plan.json`. No native process preset, support geometry, slicing action or G-code is generated.

## Revision and asynchronous work

Every geometry-affecting or saved-plan edit invalidates the current build revision. Successful builds install only when the requested sequence and revision still match. Superseded jobs are released. Downloads verify the model ID and revision after the response arrives, so a file cannot silently belong to an earlier edited state.

Project import validates and builds the replacement before installing it. A failed import preserves the user's current work. Undo/redo restores settings and requires a fresh build rather than assuming an old job still exists. Source-context changes clear design history where required.

Background removal binds its request and object URL to the current trace, aborts obsolete image work and revokes owned URLs. The cutout is independent of CAD geometry. The optional assistant uses validated proposals that require explicit Apply; stale context blocks application.

## Storage and service scope

| Data                                        | Lifetime and location                                               |
| ------------------------------------------- | ------------------------------------------------------------------- |
| Current workspace inputs and design history | Browser memory; saved recipe needed across reloads                  |
| Flat-part/relief generated job artifacts    | Backend temporary job directory; normally expire after one hour     |
| Downloaded geometry, recipes and ZIPs       | User-selected browser download location                             |
| Retained native handoff copy                | Backend handoff directory, independent of temporary CAD job cleanup |
| Photo library                               | Separate backend library store and configured original paths        |
| Knowledge notes and saved Science scenarios | Browser-profile/origin storage with separate export controls        |

The default server is a local, single-user service with no general multi-user account boundary. Same-origin JSON and loopback gates constrain native program opening and filesystem-sensitive library actions; they do not make the whole service a public authenticated deployment. See [privacy and security](privacy-security.md).

## API groups

| Group              | Representative routes                                                     |
| ------------------ | ------------------------------------------------------------------------- |
| Health and catalog | `GET /api/health`, `GET /api/printers`                                    |
| Flat parts         | `POST /api/trace`, `POST /api/build`                                      |
| Generated files    | `GET /api/download/{job_id}/{kind}`, `DELETE /api/models/{job_id}`        |
| Slicer bridge      | `GET /api/slicers`, `POST /api/models/{job_id}/slicer/{program_id}`       |
| Relief             | `POST /api/relief`, `GET /api/relief/depth`, `POST /api/relief/calibrate` |
| Blender bridge     | `GET /api/blender`, `POST /api/models/{job_id}/blender`                   |
| Photo library      | `/api/library` plus documented browse/upload/index/search/detail routes   |
| Optional assistant | `GET /api/assistant/status`, `POST /api/assistant/chat`                   |
| Local guides       | `GET /api/docs`, `GET /api/docs/{slug}`, `GET /api/docs/{slug}/download`  |

Only fixed download kinds and registered native-program IDs are accepted. Launcher commands use fixed argument arrays with `shell=False`; the browser cannot supply a command or post-processing script. A successful launch response is `launch_requested`, not confirmation of import, slicing or printing.

## Verify a change

Use focused Python tests for schema, geometry, job lifecycle and handoff contracts; pure TypeScript tests for math/history; frontend typecheck and production build; then browser tests for real interaction, download freshness and accessibility. Run native import or physical print checks only as separate explicit activities. See [development](development.md), [validation](validation.md) and [contributing](contributing.md).

## Creative tool extension boundary

The typed `studioCatalog.ts` supplies shared route metadata. `CreativeStudio.tsx` discovers bounded text tools from `backend/creative.py`; both it and the CAD assistant run through the same local-model gate and cancellation-safe inference slot. See the [extension guide](creative-tools.md) and [architecture decision](adr-local-creative-tools.md).

The shape designer uses `backend/shapes.py` for bounded inputs and the isolated `backend/shape_worker.py` for exact constructive solid operations. It recovers the planar boundary and reuses the measured-profile exporter; the UI serializes automatic rebuilds and rejects obsolete results.
