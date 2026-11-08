# Pictures to CAD

Turn a photograph of a **flat, constant-thickness part** into a scaled CAD solid. Review the traced outline beside an interactive 3D model, enter a real width and thickness, then export for your next tool.

The workbench is designed for plates, gaskets, spacers, and templates. It traces what is visible in the photograph; it does not recover hidden geometry or infer physical dimensions.

![Pictures to CAD workbench showing the traced sample beside its generated CAD solid](docs/images/workbench.png)

Browser-rendered workbench with the demonstration part. The source photo is generated sample imagery; the displayed solid is constructed from its traced outline.

## Start the app

Use **Python 3.12**, Node.js 22.12 or later (24 recommended), and npm. Setup uses [uv](https://docs.astral.sh/uv/) if available, or installs a pinned local copy. From this repository:

```bash
./scripts/setup.sh
./scripts/start.sh
```

Setup installs the locked dependencies and builds the interface. Startup runs the API and built interface together. No account, paid API, GPU, or third-party AI credential is required.

The server listens on the local machine at port **8000**. In a managed cloud environment, use the environment's supported browser or forwarding mechanism. A server running on a remote machine is not your device's localhost.

For development with frontend hot reload:

```bash
./scripts/dev.sh
```

See [development and setup](docs/development.md) for prerequisites, commands, and troubleshooting.

## Optional local AI guidance

Open **Local AI assistant** for help with capture, tracing, design changes, print planning, and export choices. Choose an installed Ollama model, ask a question, and review its answer. Suggestions show their proposed settings before an explicit **Apply**, with undo available. You still enter measured dimensions and decide when to build and export.

The assistant uses your question and current project settings; it does not receive the photograph or outline. It runs on the same machine as the CAD backend, with no paid API or cloud-model fallback. The regular CAD workflow works without it.

For the included Linux x86_64 setup:

```bash
./scripts/ollama.sh install
./scripts/ollama.sh serve
```

Keep that terminal running. In another terminal, download the initial small model:

```bash
./scripts/ollama.sh pull qwen3:1.7b
```

Refresh the assistant's connection after the download. This is a provisional CPU-friendly starting model, not a measured quality winner. See [local AI setup and controls](docs/ollama.md) and the [model comparison plan](docs/ollama-models.md). The recorded cloud setup has a verified Ollama runtime, but model downloads and live comparisons are pending network access.

## Try the complete workflow

1. **Start with the sample.** The supplied demonstration image is traced and converted by the same pipeline as an uploaded photograph.
2. **Choose a photo.** Upload a PNG, JPEG, or WebP containing one flat part against a contrasting background.
3. **Review the outline.** Check the boundary and every through-hole. Adjust the tracing controls if the selection is wrong.
4. **Set the dimensions.** Enter the measured width of the entire part along the image's horizontal axis, then enter its measured thickness separately.
5. **Choose design and print settings.** Keep the measured size or set explicit XY and thickness scales, preview a color and material, choose a printer or custom volume, and decide whether to keep one piece or generate straight-cut parts.
6. **Inspect and export.** Rotate the model, compare it with the photograph, rebuild after edits, review each piece's geometric bed fit, and choose a format.

The sample's dimensions are demonstration inputs, not measurements recovered from the photograph. Measure your own part before using its output.

Design scales preserve those source measurements: an 80 mm reference width at 125% requests a 100 mm design, while the entered reference remains 80 mm. Thickness scale is separate. Geometry-detail approximation may alter the resulting outline, so check the built dimensions. Color and material affect the approximate preview and saved plan; they do not simulate strength or select a filament spool.

Printer fit compares actual part bounds with the chosen usable volume, including a possible 90° XY rotation. It does not generate toolpaths or account for supports, adhesion, machine clearances, or material behavior. Review exported parts in your slicer. See [print planning](docs/print-planning.md).

The bundled searchable [printer catalog](docs/printer-catalog.md) covers 429 model groups across 70 manufacturer/profile families, with nozzle-specific source profiles and links. It works offline. Hardware capabilities absent from those sources are shown as unknown; custom printer dimensions remain available.

## What you can export

| Format | Use it for | What it preserves |
| --- | --- | --- |
| STEP | Opening solids in CAD software | Solid geometry in assembled positions; not the original feature history |
| STL | Slicing or mesh workflows | Triangle surfaces in assembled positions; millimeter coordinates, no color |
| DXF | A flat profile for a CAD or CAM workflow | The planar boundary and holes |
| Parts ZIP | Importing generated pieces separately | A STEP and STL per piece, plus a manifest |
| Project JSON | Restoring the workbench settings | Version 2 outline, measured inputs, design and print plan; version 1 imports remain supported |

See [export formats and dimensional checks](docs/exports.md) before transferring a part to fabrication software.

## Honest limits

- A single image supplies a 2D outline. Thickness is entered by the user; recesses, sloped walls, threads, and hidden features are not reconstructed.
- One reference width sets uniform scale. It does not correct perspective, lens distortion, or an out-of-plane part.
- Tracing approximates pixel boundaries. Smooth-looking geometry is not evidence of manufacturing accuracy.
- Relative detail can simplify the CAD outline; it does not recover missing image detail or establish a minimum printable wall thickness.
- Split exports use straight cuts without joinery, kerf, or assembly tolerances. Combined STEP/STL exports show the assembled geometry, not separated parts arranged on a print bed.
- The browser sends images to the app's backend. On a cloud host, that means uploading to that host; processing is not browser-only.
- This release is a single-user workbench, not a hosted account or collaboration service.

## Documentation

- [Capture and calibration guide](docs/capture-guide.md)
- [Export formats](docs/exports.md)
- [Print planning, materials, and split parts](docs/print-planning.md)
- [Printer catalog, provenance, and updates](docs/printer-catalog.md)
- [Development and setup](docs/development.md)
- [Optional local AI: setup and controls](docs/ollama.md)
- [Local model choices and comparison](docs/ollama-models.md)
- [Architecture and API](docs/architecture.md)
- [Data handling and security boundaries](docs/privacy-security.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Research and design decisions](docs/research.md)
- [Scope and roadmap](docs/roadmap.md)
- [Validation results](docs/validation.md)
- [Visual QA report](design-qa.md)

## Reference library

[`reference-library/`](reference-library/README.md) is the companion reference for work beyond one flat part. Open `reference-library/index.html` in a browser; it works offline. It covers:

- **Handbook:** 23 chapters on capture, scale and calibration, reconstruction workflows, CAD drawings, print design, and validation
- **Source catalog:** 86 annotated sources, each labeled with its depth of review
- **Toolkit:** 14 calculators and a route finder, with the same arithmetic available as `python3 -m cadkit`
- **Worksheets and examples:** project worksheets and an OpenSCAD example pipeline

It has its own build and tests (`cd reference-library && make test`) and its own [CI workflow](.github/workflows/reference-library.yml). See [its README](reference-library/README.md) and [verification record](reference-library/VERIFICATION.md).

## Checks

From the repository root:

```bash
./scripts/test.sh
```

This runs backend tests, the frontend type check and build, and browser tests. The validation report records which checks were actually run and their results. A successful synthetic fixture does not establish dimensional accuracy for an arbitrary real-world photograph.

A [GitHub Actions workflow](.github/workflows/ci.yml) is included for pushes and pull requests. Its presence is not evidence of a successful remote CI run; see the validation report for recorded execution evidence.

## License

[MIT](LICENSE). Dependencies retain their own licenses. Bundled printer-profile data has its own [source attribution and license record](data/PRINTER_SOURCES.md). The demonstration photograph is generated example content, not a certified reference object.
