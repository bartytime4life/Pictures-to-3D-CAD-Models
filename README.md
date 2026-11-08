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

## Try the complete workflow

1. **Start with the sample.** The supplied demonstration image is traced and converted by the same pipeline as an uploaded photograph.
2. **Choose a photo.** Upload a PNG, JPEG, or WebP containing one flat part against a contrasting background.
3. **Review the outline.** Check the boundary and every through-hole. Adjust the tracing controls if the selection is wrong.
4. **Set the dimensions.** Enter the measured width of the entire part along the image's horizontal axis, then enter its measured thickness separately.
5. **Inspect and export.** Rotate the model, compare it with the photograph, rebuild after edits, and choose a format.

The sample's dimensions are demonstration inputs, not measurements recovered from the photograph. Measure your own part before using its output.

## What you can export

| Format | Use it for | What it preserves |
| --- | --- | --- |
| STEP | Opening a solid in CAD software | Solid geometry; not the original feature history |
| STL | Slicing or mesh workflows | A triangle surface; interpret coordinates as millimeters |
| DXF | A flat profile for a CAD or CAM workflow | The planar boundary and holes |
| Project JSON | Restoring the workbench settings | A reproducible outline and dimensional recipe |

See [export formats and dimensional checks](docs/exports.md) before transferring a part to fabrication software.

## Honest limits

- A single image supplies a 2D outline. Thickness is entered by the user; recesses, sloped walls, threads, and hidden features are not reconstructed.
- One reference width sets uniform scale. It does not correct perspective, lens distortion, or an out-of-plane part.
- Tracing approximates pixel boundaries. Smooth-looking geometry is not evidence of manufacturing accuracy.
- The browser sends images to the app's backend. On a cloud host, that means uploading to that host; processing is not browser-only.
- This release is a single-user workbench, not a hosted account or collaboration service.

## Documentation

- [Capture and calibration guide](docs/capture-guide.md)
- [Export formats](docs/exports.md)
- [Development and setup](docs/development.md)
- [Architecture and API](docs/architecture.md)
- [Data handling and security boundaries](docs/privacy-security.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Research and design decisions](docs/research.md)
- [Scope and roadmap](docs/roadmap.md)
- [Validation results](docs/validation.md)
- [Visual QA report](design-qa.md)

## Checks

From the repository root:

```bash
./scripts/test.sh
```

This runs backend tests, the frontend type check and build, and browser tests. The validation report records which checks were actually run and their results. A successful synthetic fixture does not establish dimensional accuracy for an arbitrary real-world photograph.

A [GitHub Actions workflow](.github/workflows/ci.yml) is included for pushes and pull requests. Its presence is not evidence of a successful remote CI run; see the validation report for recorded execution evidence.

## License

[MIT](LICENSE). Dependencies retain their own licenses. The demonstration photograph is generated example content, not a certified reference object.
