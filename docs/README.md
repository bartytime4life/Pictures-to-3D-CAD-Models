# Documentation

Start with the guide for your task. Pictures to CAD reconstructs one flat,
constant-thickness part; the companion library also covers broader reconstruction
methods, offline reference photos, calculators and parametric OpenSCAD examples.

Read [project status and evidence](project-status.md) for the source revision and
the distinction between integrated code, pending review and qualification.

## Use the workbench

| Task | Guide |
| --- | --- |
| Install, start and try the sample | [Project README](../README.md), [setup and development](development.md) |
| Photograph and measure a part | [Capture guide](capture-guide.md) |
| Use paper to estimate scale and correct a suitable capture | [Reference-sheet tracing](reference-sheet.md) |
| Set scale from two known points and explore endpoint placement | [Reference sensitivity](reference-sensitivity.md) |
| Interpret an independent source-height check | [Engineering model and verification](engineering-model.md) |
| Resize, inspect printer fit or make straight-cut pieces | [Print planning](print-planning.md), [printer catalog](printer-catalog.md) |
| Choose CAD, mesh, drawing or source files | [Exports and dimensional checks](exports.md) |
| Prepare Bambu Studio or PrusaSlicer handoffs | [Slicer integration](slicers.md) |
| Ask the optional text-only local assistant | [Ollama setup and controls](ollama.md), [model evaluation plan](ollama-models.md) |
| Recover from an error or missing result | [Troubleshooting](troubleshooting.md) |
| Understand photo, model and local-data handling | [Privacy and security](privacy-security.md) |

The **Next step** guide directs you to a missing measurement, invalid setting,
preview update or export. A current preview means its geometry matches the shown
settings. Physical dimensions, fit and strength need their own evidence.

## Develop and evaluate

| Task | Guide |
| --- | --- |
| Make and validate a change | [Contributing](contributing.md), [development](development.md) |
| Choose a numerical CLI or repeat a study and audit its outputs | [Developer-tool catalog](developer-tools.md) |
| Understand components, API and data flow | [Architecture](architecture.md) |
| Call the local API and handle expired or rejected requests | [API examples and recovery](api-examples.md) |
| Identify the latest reviewed implementation and its evidence | [Project status](project-status.md) |
| Read mathematical methods and their limits | [Research and algorithms](research.md), [engineering model](engineering-model.md) |
| Review original scientific findings and remaining model limits | [Scientific model review](validation/scientific-model-review.md) |
| Understand initial fitted-boundary coverage | [Fit-support repair and evidence](validation/fit-support.md) |
| Understand weak-edge refusal and recovery | [Contrast-recovery validation](validation/contrast-recovery.md) |
| Understand arc-sector preservation after fillet movement | [Fillet-sweep repair](validation/fillet-sweep.md) |
| Understand tangent geometry for tapered rounded ends | [Tapered-cap repair, exact geometry and native exports](validation/tapered-caps.md) |
| Interpret sharp-corner radius estimates and unresolved searches | [Corner-resolution evidence](validation/sharp-corner-resolution.md) |
| Investigate radius compatibility under explicit fixed-model bounds | [Conditional corner CLI](corner-feasibility.md), [independent checks](validation/corner-feasibility.md) |
| Include bounded blur uncertainty without mixing per-point fits | [Version-2 joint domains](corner-feasibility.md#joint-blur-domains-version-2), [projection checks](validation/corner-blur-domains.md) |
| Model known pixel-area averages instead of center samples | [Version-3 pixel apertures](pixel-apertures.md), [independent checks](validation/pixel-apertures.md) |
| Analyze a declared signed resampling operator | [Version-4 signed stencils](signed-stencils.md), [whole-radius checks](validation/signed-stencils.md) |
| Investigate material gradients in actual edge-profile functions | [Repeatable study](material-gradients.md), [development outcomes](validation/material-gradients.md) |
| Understand nearest-edge choices and unresolved level contacts | [Crossing rule](edge-crossings.md), [independent checks](validation/edge-crossings.md) |
| Examine joint lighting/wall ambiguity and bounded source fits | [Model and repeatable experiment](wall-gradients.md), [complete results](validation/wall-gradients.md) |
| Review wall localization, sampling operators and retained camera regressions | [Method and comparison](wall-localization.md), [source-bound development record](validation/wall-localization.md) |
| Understand correlated profile samples and compose a known smoothing filter | [Fixed observations and covariance](profile-observations.md), [complete controls](validation/profile-observations.md) |
| Include known perspective/lens resampling and inspect raw optical assumptions | [Warp-chain model](warp-observations.md), [complete digital and optical controls](validation/warp-observations.md) |
| Fit a supplied straight raw optical source without inverting weak profile modes | [Source-space variable projection](raw-source-fit.md), [complete controls and limitations](validation/raw-source-fit.md) |
| Check externally bounded calibration for one common scalar response | [Exact response consistency](response-calibration.md), [edge/calibration controls](validation/response-calibration.md) |
| Carry input intervals through one common response and bound supplied Gaussian inputs | [Rectangle quantifiers and outward CDF bounds](response-rectangles.md), [finite experiment and independent checks](validation/response-rectangles.md) |
| Enclose continuous shared edge-offset/blur domains without choosing independent inputs | [Gaussian response domains](gaussian-response-domains.md), [complete boxes, controls and independent replay](validation/gaussian-response-domains.md) |
| Understand the lens inverse domain and independent synthetic camera checks | [Radial inverse and lens mismatch](validation/radial-inverse.md) |
| Review why the blur diagnostic remains research only | [Directional-spread qualification](validation/directional-spread-qualification.md) |
| Understand global feature matching and dimension coverage | [Benchmark correspondence record](validation/benchmark-correspondence.md) |
| Run a benchmark with measured photos | [Photo benchmark](photo-benchmark.md) |
| Review completed checks | [Validation overview](validation.md), [design QA](../design-qa.md) |
| Check current documentation coverage and source consistency | [Current coverage](validation/tapered-caps.md#documentation-coverage), [earlier complete review through PR #66](validation/documentation-response-state.md), [response implementation coverage](validation/response-calibration.md#documentation-coverage) |
| Interpret incomplete hosted runs and the overall job limit | [Runtime-budget evidence](validation/ci-runtime-budget.md), [exact-head CI status](project-status.md#evidence-by-scope) |
| Review the recent interface changes | [Guided-workbench audit](validation/guided-workbench.md) |
| Review scope and future work | [Roadmap](roadmap.md), [change log](changelog.md) |
| Reproduce bundled printer data | [Printer source record](../data/PRINTER_SOURCES.md) |

Historical validation reports retain their original revision, environment and
counts. They describe those runs, rather than the current installed application
or a later commit. Start at the validation overview for the relevant evidence.

Detailed records cover [height decisions](validation/engineering-audit.md),
[curved placement](validation/curved-placement.md), [suggested splits](validation/split-plans.md),
[project import recovery](validation/project-import-recovery.md),
[endpoint sensitivity](validation/reference-sensitivity.md), and the earlier
[documentation refresh](validation/documentation-refresh.md).

## Companion reference library

| Resource | Purpose |
| --- | --- |
| [Offline reader](../reference-library/index.html), [library README](../reference-library/README.md) | Handbook, catalog, Toolkit, Photos, OpenSCAD and worksheets |
| [Handbook](../reference-library/HANDBOOK.md), [research record](../reference-library/RESEARCH-NOTES.md) | Methods, assumptions and review depth |
| [Source directory](../reference-library/REFERENCES.md), [GitHub snapshot](../reference-library/GITHUB.md) | Annotated catalog and dated repository metadata |
| [OpenSCAD workflow](../reference-library/OPENSCAD.md), [examples](../reference-library/examples/README.md) | Synthetic plate/coupon sources, native builds and handoff checks |
| [cadkit commands](../reference-library/cadkit/README.md) | Calculators, STL inspection and project scaffolding |
| [Build instructions](../reference-library/BUILD.md), [contributing](../reference-library/CONTRIBUTING.md) | Source editing, generated HTML/PDF and test commands |
| [Verification record](../reference-library/VERIFICATION.md), [library changelog](../reference-library/CHANGELOG.md) | Separate library evidence and revision history |
| [Project brief](../reference-library/templates/PROJECT-BRIEF.md), [capture checklist](../reference-library/templates/CAPTURE-CHECKLIST.md) | Record inputs, requirements and capture conditions |
| [Independent checks](../reference-library/templates/INDEPENDENT-CHECKS.md), [print acceptance](../reference-library/templates/PRINT-ACCEPTANCE.md) | Reserve evaluation dimensions and record physical outcomes |

The library's browser-stored Photos collection is separate from the workbench's
backend upload. Its image limits and persistence rules differ; follow the guide
for the component you are using. The repository and portable library have
separate build and verification records.
