# Documentation

Start with a task, follow its workflow, and keep a saved recipe before leaving the application. Pictures to CAD has a shape designer, a measured flat-part workbench, a relief studio, image inspection, a photo library, Creative tools, and supporting Knowledge and Science workspaces.

## Start and finish a part

| Your task                                                 | Read                                                                                                                   |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Install, run and finish the sample                        | [Getting started](getting-started.md)                                                                                  |
| Choose the right workspace and complete a project         | [Workflow guide](workflows.md)                                                                                         |
| Capture a useful photograph                               | [Capture guide](capture-guide.md)                                                                                      |
| Use A4, Letter or a measured sheet                        | [Reference-sheet tracing](reference-sheet.md)                                                                          |
| Set scale from a known feature or common-object reference | [Reference sensitivity](reference-sensitivity.md) and [measurement workflow](workflows.md#scale-and-check-a-flat-part) |
| Resize, split and inspect individual pieces               | [Print planning](print-planning.md) and [printer catalog](printer-catalog.md)                                          |
| Prepare a package for any of the five slicers             | [Slicer integration](slicers.md)                                                                                       |
| Choose a file format and verify imported units            | [Exports](exports.md)                                                                                                  |
| Make reliefs, lithophanes, globes or Blender handoffs     | [Relief studio](relief.md)                                                                                             |
| Organize and choose source photos                         | [Photo library](photo-library.md)                                                                                      |
| Recover work or diagnose a problem                        | [Troubleshooting](troubleshooting.md)                                                                                  |

The **Next step** guide points to the next missing measurement, invalid setting, build or export review. **Quick edit** changes design size; the original reference measurements stay explicit. **Prepare for slicing** keeps process notes with the built revision. View-only controls never modify an exported solid.

Create a part without a photo using the [shape designer](shape-designer.md). Explore ideas and find a making workspace with [Creative tools](creative-tools.md). Developers can use its workspace catalog and text-tool registry to add tools without duplicating navigation or inference plumbing.

Use [Image inspection](image-inspection.md) for region histograms, exposure/contrast
readings and pixel-aligned A/B comparison before tracing.

## Understand the result

| Topic                                                             | Read                                                                                     |
| ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Scale, perspective, layer height and fit scenarios                | [Science guide](science.md)                                                              |
| Define an engineering requirement and independent check           | [Engineering model](engineering-model.md)                                                |
| Interpret conditional endpoint sensitivity                        | [Reference sensitivity](reference-sensitivity.md)                                        |
| Understand where photos and files live                            | [Privacy and security](privacy-security.md)                                              |
| Optional advice from local Ollama                                 | [Local assistant](ollama.md) and [model evaluation](ollama-models.md)                    |
| Distinguish current application behavior from historical research | [Research and validation index](research-index.md) and [source scope](project-status.md) |

Knowledge articles and Science scenarios are part of the browser interface. Their saved notes/scenarios are separate from the CAD project recipe. Export the relevant file when moving between computers or browser profiles.

## Develop and evaluate

- [Architecture](architecture.md): workspaces, data flow, state, persistence and integration boundaries.
- [Detailed API and geometry contracts](api-reference.md): requests, outputs, units and implementation details.
- [Development](development.md), [developer tools](developer-tools.md), [contributing](contributing.md): environment, commands and review process.
- [Research methods](research.md), [research index](research-index.md), [validation overview](validation.md): mathematical methods and revision-bound results.
- [Precision Studio review](validation/precision-studio.md): interface captures, corrected defects and current local verification scope.
- [Pull-request verification](validation/precision-studio-pr.md): current-main integration checks and the scope of earlier evidence.
- [Studio follow-up](validation/studio-followup.md): documentation integration, shared-export recovery and narrow-phone label verification.
- [Photo benchmark](photo-benchmark.md): compare source images with independent measurements.
- [Roadmap](roadmap.md), [change log](changelog.md): planned work and recorded changes.

Historical evidence retains its original revision, inputs, failures and limits. A later green test run does not rewrite an earlier result, establish camera accuracy or prove a physical print.

## Companion reference library

Open the application's **OpenSCAD** link for the separate reference workspace, or use [the offline reader](../reference-library/index.html). Its [README](../reference-library/README.md), [handbook](../reference-library/HANDBOOK.md), [OpenSCAD guide](../reference-library/OPENSCAD.md), [cadkit commands](../reference-library/cadkit/README.md) and [build guide](../reference-library/BUILD.md) describe its own tools and checks.

Use the [project brief](../reference-library/templates/PROJECT-BRIEF.md), [capture checklist](../reference-library/templates/CAPTURE-CHECKLIST.md), [independent checks](../reference-library/templates/INDEPENDENT-CHECKS.md) and [print acceptance](../reference-library/templates/PRINT-ACCEPTANCE.md) templates to record a project beyond the browser session.

- [Creative workspace verification](validation/creative-workspaces.md): local Ollama inference, common-shape CAD, workspace UI checks, fixes and captured evidence.
