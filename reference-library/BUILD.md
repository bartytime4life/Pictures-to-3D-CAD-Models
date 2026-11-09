# Building, testing, and packaging the library

Reading the HTML or the PDF needs no tools: open `index.html` in a browser. The handbook, catalog filters, Toolkit calculators, and Photos workspace all work offline. Source links need internet access. Saving photos requires browser support for IndexedDB and image decoding, plus available local storage.

## Requirements

| Task | Needs |
| --- | --- |
| Calculations, figures, `cadkit`, Python tests, archive | Python 3.10+ (standard library only) |
| HTML build and Node tests | Node.js 20+ and the `marked` package |
| Browser check | `playwright` package and Chrome or Chromium |
| PDF | Python with `reportlab` and `lxml` (`requirements.txt`), and DejaVu fonts |
| Plate pipeline and render tests | OpenSCAD (optional; those steps are skipped without it) |
| Link check, GitHub refresh | Network access |

Install the packages once, from `reference-library/`. `package-lock.json` pins the exact versions; use `npm ci` to reproduce them:

```bash
npm ci
```

```bash
python3 -m pip install -r requirements.txt
```

If Chrome is not installed, run `npx playwright install chromium`, or set `CAD_REFERENCE_CHROME` to a browser executable.

The Node scripts look for packages in `reference-library/node_modules`, then `$CAD_REFERENCE_NODE_MODULES`, then the Codex runtime that authored Revisions 1–2 (`~/.cache/codex-runtimes/...`). The Makefile uses that runtime's Python for the PDF when your `python3` lacks ReportLab.

## Everyday commands

Run these from `reference-library/`.

| Command | What it does |
| --- | --- |
| `make build` | `calc` → `figures` → `html` → `pdf` |
| `make test` | Python `unittest` and `node --test` (including JavaScript-vs-Python agreement) |
| `make check` | Browser end-to-end checks of `index.html` (`check-library.mjs`) of the Photos workspace (`check-photos.mjs`), and of portable backup/restore (`check-photo-transfer.mjs`); records and screenshots go to `tmp/qa/` |
| `make plate` | Render the synthetic plate with OpenSCAD and run its design-rule checks |
| `make links` | Request every catalog URL and write `tmp/qa/link-check.json` (network) |
| `make refresh-github` | Update the repository metadata in `sources.json` (network) |
| `make verify` | Run every automated check and write `verification.json` |
| `make dist` | Write `SHA256SUMS` and, in `dist/`, the ZIP named in `library.json` |
| `make dist-check` | Verify `SHA256SUMS` against the files |
| `make release` | `build` → `plate` → `test` → `check` → `verify` → `dist` |
| `make clean` | Remove `tmp/` and `examples/output/` |

`make check` retains the default `file://` test of the offline reader. When a
managed browser blocks local-file navigation, run the same assertions over HTTP:

```bash
CAD_REFERENCE_BROWSER_TRANSPORT=http make check
```

The check starts its own server on an available loopback port and closes it on
success or failure. It serves only the published library page, figures, linked
documents, worksheets, and examples; it does not serve the parent repository,
dependency folders, or environment files. No external service is used. The QA
JSON records `transport`, `page_url`, and the tested scope. An HTTP result does
not establish that `file://` works in that browser. CI checks both transports.

To run a step directly:

- **Calculations:** `python3 examples/calculate.py` rewrites the worked numbers; `--check` only compares them.
- **Figures:** `python3 scripts/make-figures.py` writes `assets/figures/*.svg` and `tmp/figures-inline/`.
- **HTML:** `node scripts/build-library.mjs` writes `index.html`, `sources.csv`, `REFERENCES.md`, `GITHUB.md`, and `tmp/*.html`.
- **PDF:** `python3 scripts/make-pdf.py` writes `output/pdf/pictures-to-printable-cad.pdf`.

## What is generated from what

| Edit this | To change | Regenerate with |
| --- | --- | --- |
| `sources.json` | catalog, CSV, `REFERENCES.md`, `GITHUB.md`, catalog chart, counts | `make build` |
| `HANDBOOK.md`, `RESEARCH-NOTES.md`, `templates/*.md` | HTML and PDF text | `make html pdf` |
| `scripts/figures.py` | all figures (SVG and PDF) | `make figures html pdf` |
| `assets/data/routes.json` | route finder (HTML, CLI) and route map | `make figures html` |
| `assets/data/calculators.json`, `assets/js/*.js`, `assets/css/*.css`, `assets/photo-workspace.html` | Toolkit, Photos workspace, and page interface (inlined into `index.html`) | `make html` |
| `cadkit/*.py` | CLI, examples, Python tests | `make test` |
| `examples/plate-parameters.csv` | plate render and checks | `make plate` |
| `library.json` | revision label, dates, archive name | `make build dist` |

Never edit generated files by hand: `index.html`, `sources.csv`, `REFERENCES.md`, `GITHUB.md`, `assets/figures/*.svg`, the PDF, and `verification.json`. `SHA256SUMS` and `dist/` are also generated and are not committed.

## Photo workspace

The HTML build inlines `assets/photo-workspace.html`, `assets/css/photos.css`, and the scripts `assets/js/photos.js`, `assets/js/photo-transfer.js`, `assets/js/photo-register.js`, and `assets/js/photo-workspace.js`. The core photo module owns storage, validation, and scale calculations; the workspace script connects those operations to the page. The Photos tab follows Toolkit, and Worksheets remains the last tab.

The browser stores original image files and photo details in IndexedDB, separately from repository files and generated artifacts. No photo is included in an HTML rebuild, PDF, or distribution archive. There is no fixed photo-count limit; imports are processed sequentially, and storage availability determines how many photos fit. The per-file limits are 50 MiB and 60 megapixels. Supported input types are JPEG, PNG, and WebP.

Photo measurements are simple pixel-length ratios with a known real length. They assume a front-on view and a shared plane, and do not correct perspective or perform photogrammetry. View coverage is based on user-supplied labels, not an analysis of image quality or reconstruction completeness.

Browser storage can be unavailable, exhausted, cleared, or isolated by browser profile and origin. Keep original images outside the application. The downloadable manifest contains metadata and measurement records only; it cannot restore image files on its own. Folder backup copies originals and the manifest to a new user-selected subfolder. Restore verifies the manifest and image fingerprints before adding photos, preserves existing annotations, and reports partial failure. Manifest parsing is limited to 64 MiB; images are processed sequentially. When testing, use synthetic images in a disposable browser profile and check persistence within the same origin. A normal HTML rebuild does not migrate data between browser profiles or origins.

### Photo transfer verification

`node scripts/check-photo-transfer.mjs` runs in isolated browser contexts with synthetic images. It exercises the browser file APIs with a real origin-private directory handle, then restores the exported files into a different browser context. The native operating-system folder chooser is injected in automation; its interactive permission prompt is not an automated acceptance result. The original photo acceptance suite remains `scripts/check-photos.mjs`; `make check` runs both and the main library checks.

Folder export uses the browser's [directory picker](https://developer.mozilla.org/en-US/docs/Web/API/Window/showDirectoryPicker) and [writable file handles](https://developer.mozilla.org/en-US/docs/Web/API/FileSystemFileHandle/createWritable). It must start from a user click. Unsupported environments show the manifest-plus-originals fallback. Nothing is sent to a remote service.

`photo-register.js` exports the existing measurement-register columns, including image-derived evidence and blank unknown fields. It quotes CSV fields and protects spreadsheet formula prefixes in user text. CSV export is a review handoff and does not modify the design-parameter register.


`scripts/check-photos.mjs` runs in fresh, isolated browser contexts with generated images and writes `tmp/qa/photo-check.json`. It honours `CAD_REFERENCE_BROWSER_TRANSPORT` like the main check, through the same loopback server (`scripts/lib/serve.mjs`). Because browser storage is per origin, a pass over HTTP does not establish that a particular browser saves photos for a `file://` page.

## Reproducibility

- The PDF uses ReportLab's invariant mode, so unchanged sources rebuild byte for byte. The trade-off is that its internal creation date reads 2000-01-01. The date that matters is printed on every page.
- The ZIP sorts its entries and fixes their timestamps and permissions.
- `index.html` and the SVG figures contain no timestamps.
- `SHA256SUMS` paths are relative to the repository root: `cd ..` and run `sha256sum -c reference-library/SHA256SUMS`. The manifest and `dist/` are build products and are not committed.
- In CI, `.github/workflows/reference-library.yml` regenerates the calculations, figures, HTML, CSV, and Markdown directories, then fails if any committed copy differs. The PDF is excluded from that comparison because font builds differ between machines.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `CAD_REFERENCE_NODE_MODULES` | A `node_modules` directory holding `marked` and `playwright` |
| `CAD_REFERENCE_CHROME` | Chrome or Chromium executable for the browser check |
| `CAD_REFERENCE_BROWSER_TRANSPORT` | `file` (default) or `http`; HTTP uses a temporary loopback server |
| `CAD_REFERENCE_FONT_DIR` | Folder containing `DejaVuSans.ttf` and its family |
| `CAD_REFERENCE_PYTHON` | Python used by the Node tests to call `cadkit` (default `python3`) |
| `GITHUB_TOKEN` or `GH_TOKEN` | Raises the API rate limit for `refresh-github` |
| `PYTHON`, `NODE`, `PDF_PYTHON` | Makefile overrides |

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Cannot find the Node package "marked"` | Run `npm ci`, or set `CAD_REFERENCE_NODE_MODULES` |
| Browser check cannot launch a browser | Install Chrome, run `npx playwright install chromium`, or set `CAD_REFERENCE_CHROME` |
| `file://` navigation is blocked by browser policy | Run `CAD_REFERENCE_BROWSER_TRANSPORT=http make check`; do not change the browser policy |
| `DejaVu fonts not found` | Install `fonts-dejavu`, or set `CAD_REFERENCE_FONT_DIR` |
| `Refusing to build` | The catalog or route data failed validation; the message names the entry |
| `test_docs` fails after an edit | A document disagrees with the data; the message names the file and value |
| `make verify` stops after writing | Update `VERIFICATION.md` to match the new `verification.json` (test counts, browser assertions, plate checks, PDF pages), then run `make verify` again. Until then `make test` also fails, because `test_docs` compares the two files |
| Plate tests skipped | OpenSCAD is not on `PATH`. This is expected on machines without it |
| Photos cannot be saved | Check the page's storage message; use a normal browser profile with IndexedDB enabled and free space |
| Previously added photos are missing | Return to the same browser profile and page origin; clearing browser data removes locally stored photos |

## Provenance

Revisions 1 and 2 were authored with a Codex workflow and its bundled runtimes. Revision 3 made the build portable and added the toolkit, figures, and tests; no CAD application other than OpenSCAD and no AI reconstruction package was installed or run. Generated intermediates live in `tmp/`, which is ignored by Git and excluded from the archive.
