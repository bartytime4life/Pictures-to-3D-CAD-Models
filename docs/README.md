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
| Check documentation coverage and source consistency | [Current documentation audit](validation/documentation-restoration-draft.md), [source and CI snapshot](project-status.md), [preceding published review](validation/documentation-defect-corrector.md) |
| Review the recent interface changes | [Guided-workbench audit](validation/guided-workbench.md) |
| Review scope and future work | [Roadmap](roadmap.md), [change log](changelog.md) |
| Diagnose fixed-normal residual information and its original failed normal control | [Method and rotation identity](finite-residual-information.md), [derived finite-chord proposal](finite-residual-information.md#finite-chord-shape-derivative-a-derived-proposal), [retained failed protocol](validation/finite-residual-information.md), [portable saved-data audit](../studies/fixtures/finite-residual-information-v1/README.md) |
| Evaluate signed finite-material normal-angle sensitivities | [Experimental API and units](finite-normal-derivative.md), [complete failed qualification](validation/finite-normal-derivative.md), [portable archive](../studies/fixtures/finite-normal-derivative-v1/README.md) |
| Review later analytic-normal research on its recorded branch | [Pinned result and geometric counterexamples](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/blob/0f1adbd391f7fa015f458cca60dcfe2a0e2dad9e/docs/validation/finite-analytic-normal-information.md); this is separate from current-main qualification |
| Test a Gaussian hypothesis against known acquisition stages | [Method and completed outcomes](finite-acquisition-operator.md), [recorded-source validation](validation/finite-acquisition-operator.md), [123-artifact archive and saved-only workflow](../studies/fixtures/finite-acquisition-operator-v1/README.md) |
| Inspect the independent source-cell acquisition mean | [Executable example](finite-acquisition-mean.md#small-executable-example), [API limits and resource accounting](finite-acquisition-mean.md#refusals-provenance-and-work), [complete qualification](validation/finite-acquisition-mean.md), [frozen plan](../studies/finite-acquisition-mean-v1.json), [portable archive](../studies/fixtures/finite-acquisition-mean-v1/README.md); no automatic trace or inverse integration |
| Evaluate five unrounded cell-area sensitivities and propagate signed fields | [Boundary flux and fixed linear acquisition](finite-cell-sensitivity.md), [small executable example](finite-cell-sensitivity.md#small-executable-example), [first frozen qualification and limits](validation/finite-cell-sensitivity.md), [portable saved-data archive](../studies/fixtures/finite-cell-sensitivity-v1/README.md); no geometry recovery or rounded-pipeline derivative claim |
| Review the separate local five-geometry/unknown-brightness prototype | [Model, search and rank limits](finite-acquisition-recovery.md), [original and predictor protocols, all 24 rows and first audit limitation](validation/finite-acquisition-recovery.md); research snapshot only, without its runtime in main or workbench controls |
| Review coupled and source-event recovery | [Seven-parameter surrogate](finite-acquisition-coupled.md), [source-code events](finite-acquisition-events.md), [completed 11/12 results and remaining miss](validation/finite-acquisition-continuations.md); separate local research |
| Review protected-source-bin proposals | [Original local projection](finite-acquisition-protected.md), [eight failed first controls](validation/finite-acquisition-protected.md), [exact active-face follow-up](finite-acquisition-protected-active.md), [retained first expectation failure](validation/finite-acquisition-protected-active.md), [corrected selected controls and completed 11/12 study](validation/finite-acquisition-physical-rounding.md); local research only |
| Understand rational-to-physical rounding | [Original five gates and negative corner census](finite-acquisition-physical-rounding.md), [49 controls and complete negative 128-corner diagnostic](validation/finite-acquisition-physical-rounding.md); no new fit or improvement |
| Review the inward-point representation step | [Exact construction and unchanged gates](finite-acquisition-inward-margin.md), [103 focused controls, 128/128 feasible new corners and saved-data audit](validation/finite-acquisition-inward-margin.md); local feasibility only |
| Review the actual PNG cost test | [Paired replay and acceptance rule](finite-acquisition-inward-literal.md), [162 selected controls and complete negative result](validation/finite-acquisition-inward-literal.md); exact baseline, higher candidate cost, no recovery improvement |
| Review the observed-defect correction | [One equality-restoration step](finite-acquisition-defect-corrector.md), [220 controls and first actual training improvement](validation/finite-acquisition-defect-corrector.md); zero training cost for one supplied synthetic PNG context, full recovery not rerun |
| Review the prospective live restoration controller | [Draft method, accounting and evidence gates](finite-acquisition-restoration.md); authored and unrun, no new recovery score or main command |
| Review saved-record consistency and packaging | [Archive inventory, completed audits, first failures and precision gaps](finite-acquisition-saved-audit.md); no forward-model or physical qualification |
| Reproduce bundled printer data | [Printer source record](../data/PRINTER_SOURCES.md) |

Before running an archived audit, check its
[source-binding requirements](developer-tools.md#historical-source-checks-in-saved-data-audits).
Some saved-only tools compare against the checkout's current source and therefore
report a provenance mismatch on later main revisions.

Historical validation reports retain their original revision, environment and
counts. They describe those runs, rather than the current installed application
or a later commit. Start at the validation overview for the relevant evidence.

Detailed records cover [height decisions](validation/engineering-audit.md),
[curved placement](validation/curved-placement.md), [suggested splits](validation/split-plans.md),
[project import recovery](validation/project-import-recovery.md),
[endpoint sensitivity](validation/reference-sensitivity.md), and an
[earlier documentation refresh](validation/documentation-refresh.md).

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
