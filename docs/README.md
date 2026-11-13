# Documentation

Start with the guide for your task. Pictures to CAD reconstructs one flat,
constant-thickness part; the companion library also covers broader reconstruction
methods, offline reference photos, calculators and parametric OpenSCAD examples.

Read [source scope and status](project-status.md) first when switching branches.
Workbench tracing, corner/frame repairs and separate research APIs have
different source and validation histories.

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
| Find the commands available in this checkout | [Developer tools and output behavior](developer-tools.md) |
| Understand components, API and data flow | [Architecture](architecture.md) |
| Read mathematical methods and their limits | [Research and algorithms](research.md), [engineering model](engineering-model.md) |
| Investigate conditional finite-material intensity fitting | [Developer model and numerical limits](finite-shape-inverse.md) |
| Understand batched affine probabilities, resource limits and measured fit latency | [Shared-panel mathematics](finite-affine-evaluation.md), [complete qualification record](validation/finite-affine-batch.md) |
| Prepare fixed samples from a measured ring and compare covariance hypotheses | [Observation contract](finite-shape-inverse.md#prepare-a-measured-ring-observation-set), [paired saved-field replay](validation/finite-photo-intensity-v2.md) |
| Review original scientific findings and remaining model limits | [Scientific model review](validation/scientific-model-review.md) |
| Understand initial fitted-boundary coverage | [Fit-support repair and evidence](validation/fit-support.md) |
| Understand weak-edge refusal and recovery | [Contrast-recovery validation](validation/contrast-recovery.md) |
| Understand arc-sector preservation after fillet movement | [Fillet-sweep repair](validation/fillet-sweep.md) |
| Understand directional blur at nonparallel fitted corners and traced-outline recovery | [Anisotropic corner model](anisotropic-corners.md) |
| Understand blur units after thickness correction and mixed-curve warnings | [Blur frames and support rules](blur-frames.md) |
| Understand circle-consistent final joins, retained outlines and critical CAD checks | [Curved joins](curved-joins.md), [arc export checks](exports.md#verify-critical-arc-geometry) |
| Understand the lens inverse domain and independent synthetic camera checks | [Radial inverse and lens mismatch](validation/radial-inverse.md) |
| Distinguish the earlier blur diagnostic from current directional tracing | [Historical qualification](validation/directional-spread-qualification.md), [current method](reference-sheet.md), [rank repair](validation/directional-blur-rank.md) |
| Understand global feature matching and dimension coverage | [Benchmark correspondence record](validation/benchmark-correspondence.md) |
| Run a benchmark with measured photos | [Photo benchmark](photo-benchmark.md) |
| Review completed checks | [Validation overview](validation.md), [design QA](../design-qa.md) |
| Check documentation coverage and source consistency | [Current PR #93 documentation review](validation/documentation-pr93-state.md), [preceding affine-source review](validation/documentation-affine-state.md), [measured-ring evidence](validation/finite-photo-intensity-v2.md) |
| Review the recent interface changes | [Guided-workbench audit](validation/guided-workbench.md) |
| Review scope and future work | [Roadmap](roadmap.md), [change log](changelog.md) |
| Read a proposed diagnostic without mistaking it for a current capability | [Residual information and acquisition-model limits](finite-residual-information.md); no archived-data replay result yet |
| Reproduce bundled printer data | [Printer source record](../data/PRINTER_SOURCES.md) |

Historical validation reports retain their original revision, environment and
counts. They describe those runs, rather than the current installed application
or a later commit. Start at the validation overview for the relevant evidence.

Detailed records cover [height decisions](validation/engineering-audit.md),
[curved placement](validation/curved-placement.md), [suggested splits](validation/split-plans.md),
[project import recovery](validation/project-import-recovery.md),
[endpoint sensitivity](validation/reference-sensitivity.md), and this
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
