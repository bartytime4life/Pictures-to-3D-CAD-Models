<p align="center">
  <img src="assets/figures/banner.svg" alt="From pictures to printable CAD: a photograph becomes a dimensioned CAD drawing and then a layered print" width="100%">
</p>

<p align="center">
  <img alt="Works offline" src="https://img.shields.io/badge/works-offline-174d68">
  <img alt="Python 3.10+ standard library" src="https://img.shields.io/badge/python-3.10%2B%20stdlib-2f7d79">
  <img alt="Node 20+" src="https://img.shields.io/badge/node-20%2B-2f7d79">
  <img alt="OpenSCAD optional" src="https://img.shields.io/badge/OpenSCAD-optional-c77a1f">
</p>

# Pictures to printable CAD: reference library

This folder is the reference companion to the [photo-to-CAD workbench](../README.md) in this repository. The workbench traces one flat part; the library covers the wider route from photographs to printable CAD.

A practical, source-backed library for turning photographs into printable CAD: recover shape, establish dimensions, rebuild editable geometry, and check the part you print. **Revision 4, November 8, 2026.**

It contains a 23-chapter handbook, 86 annotated sources (including 21 GitHub repository records), research notes, reusable worksheets, 10 explanatory figures, 14 calculators with a route finder, a local photo workspace, a Python command-line toolkit, and synthetic worked examples that are rendered and checked automatically.

## Start here

| If you want to… | Open |
| --- | --- |
| Read and search everything in a browser, offline | [`index.html`](index.html) |
| Read a printable copy | [the PDF handbook](output/pdf/pictures-to-printable-cad.pdf) |
| Find the right workflow and check the arithmetic | the **Toolkit** tab of `index.html`, or `python3 -m cadkit` |
| Collect reference photos, check view coverage, and estimate a flat dimension | the **Photos** tab of `index.html` |
| Edit the text | [`HANDBOOK.md`](HANDBOOK.md) and the [worksheets](templates/) |
| Rebuild, test, or package the library | [`BUILD.md`](BUILD.md) |

The easiest first project is a measured flat part. Import and scale a reference image, draw a constrained sketch, extrude it to the measured thickness, document the critical dimensions, and print an interface coupon before the full part.

![Capture, measure, reconstruct, model and draw, print and check](assets/figures/process-flow.svg)

## What is inside

| Material | Files | Notes |
| --- | --- | --- |
| Handbook | [`HANDBOOK.md`](HANDBOOK.md) | Governing decisions, capture, provenance, scale and single-view calibration, workflows A–E, held-object design, geometry, drawings, process selection, scripted pipelines, validation, troubleshooting, and a learning plan |
| Source directory | [`REFERENCES.md`](REFERENCES.md), [`sources.csv`](sources.csv), [`sources.json`](sources.json) | 86 annotated sources, each with a use, a limitation, and its depth of review. `sources.json` is the authoritative record |
| GitHub directory | [`GITHUB.md`](GITHUB.md) | 21 GitHub repository records: purpose, caution, and a metadata snapshot |
| Research notes | [`RESEARCH-NOTES.md`](RESEARCH-NOTES.md) | Search scope, evidence depth, exclusions, and a paper-evaluation worksheet |
| Worksheets | [`templates/`](templates/) | Project brief, capture checklist, print acceptance, and measurement, assumption, validation, and design-parameter registers |
| Toolkit | [`cadkit/`](cadkit/README.md), [`assets/js/cadcalc.js`](assets/js/cadcalc.js) | 14 calculators, a route finder, an STL checker, a parameter-register loader, and a project scaffolder |
| Photo workspace | [`assets/photo-workspace.html`](assets/photo-workspace.html), [`assets/js/photos.js`](assets/js/photos.js), [`assets/js/photo-workspace.js`](assets/js/photo-workspace.js) | Add photos in batches, label viewpoints, record notes, and estimate a flat feature from a known reference length; stored in this browser |
| Examples | [`examples/`](examples/README.md) | Synthetic plate driven by one parameter register and checked after an OpenSCAD render; a printable clearance coupon; reproducible calculations |
| Records | [`VERIFICATION.md`](VERIFICATION.md), [`CHANGELOG.md`](CHANGELOG.md), [`CONTRIBUTING.md`](CONTRIBUTING.md) | What was checked, what was not, and what changed |

![86 sources by topic and review depth](assets/figures/catalog-composition.svg)

## The toolkit

In the browser, the **Toolkit** tab answers "which route fits my project?" and runs 14 calculators: planar scale, scale uncertainty, calibration self-check, homography fit, off-plane depth correction, camera distance, label rounding, circle tessellation, clearance coupons, coating allowance, spur gears, import-unit diagnosis, evidence-class propagation, and wind power. Each calculator links to its handbook section and warns about the conditions the handbook flags.

The same arithmetic runs from a terminal. From this folder:

```bash
python3 -m cadkit route --input photo-set --goal editable
```

```bash
python3 -m cadkit depth --z 500 --delta 60 --size 40
```

```bash
python3 -m cadkit meshcheck examples/output/two-hole-plate.stl --expect-mm 60
```

The last command checks the STL that `make plate` renders with OpenSCAD: extents, volume, closure, vertex manifoldness, orientation, and genus, which for a plate equals the number of through-holes. It works on any ASCII or binary STL, including the workbench's exports, and the [workbench tests](../tests/test_mesh_interop.py) run it on combined and split-part exports. The library's test suite checks that the browser and Python calculators return the same results and the same route recommendations.

![Route map from available input to a starting workflow](assets/figures/route-map.svg)

## Your reference photos

Open **Photos** to add JPEG, PNG, or WebP images, either with the file picker or by dropping them onto the page. There is no photo-count cap: add more in later batches as needed, subject to available browser and device storage. Each image is limited to 50 MiB and 60 megapixels so a single large file cannot consume excessive decoding memory. Imports run one photo at a time and can be stopped after the current file.

Label each image's viewpoint and record notes about its features or uncertainties. The coverage summary reflects those labels; it does not evaluate whether the pictures are sharp, overlapping, or suitable for reconstruction. Search and viewpoint filters help find the reference you need as the collection grows.

For a front-on view of a flat surface, mark two endpoints on a known reference and two on the feature of interest, then enter the reference length in millimeters. You can select points on the image or enter full-size pixel coordinates. The resulting dimension is a scale estimate that assumes both lengths lie in the same plane. It does not correct perspective, recover hidden geometry, generate CAD, or establish 3D accuracy. Confirm critical dimensions with physical measurements and use the Toolkit to choose a reconstruction workflow.

Photos and their details are saved only in this browser's local storage; they are never uploaded. Clearing browser data, using another browser or origin, or losing the device can make the collection unavailable. Keep your original image files. **Export photo manifest** saves the notes and measurements, not the image files, and is not a backup of the photo library. **Download original** retrieves an individual stored photo. The feature needs a browser with IndexedDB and image decoding support; storage restrictions and private browsing can prevent saving.

The Photos tab is separate from the [workbench](../README.md)'s photo upload, which traces one flat part on its own backend. Photos saved here stay in this page's browser storage and are not shared with the workbench.

## How the pieces fit together

Every count, chart, and worked number is derived from one source of truth, and the tests fail when a generated file or a document drifts from it.

```mermaid
flowchart LR
  subgraph Sources of truth
    S[sources.json]:::src
    H[HANDBOOK.md + notes]:::src
    D[assets/data/*.json]:::src
    P[examples/plate-parameters.csv]:::src
  end
  S --> B[build-library.mjs]
  H --> B
  D --> B
  S --> F[make-figures.py]
  D --> F
  F --> B
  B --> I[index.html + CSV + REFERENCES.md + GITHUB.md]
  B --> PDF[make-pdf.py → PDF]
  F --> PDF
  P --> O[OpenSCAD render] --> M[cadkit meshcheck → validation CSV]
  I --> T{{tests: Python · Node · browser}}
  PDF --> T
  M --> T
  T --> V[verification.json] --> Z[make-dist.py → SHA256SUMS + ZIP]
  classDef src fill:#edf3f6,stroke:#174d68,color:#172b37
```

## Folder layout

```text
reference-library/
├── index.html                 offline library (generated)
├── README.md, CHANGELOG.md, CONTRIBUTING.md, BUILD.md, VERIFICATION.md
├── HANDBOOK.md, RESEARCH-NOTES.md
├── sources.json               authoritative catalog → sources.csv, REFERENCES.md, GITHUB.md
├── library.json               revision, date, archive name
├── assets/                    photo-workspace.html, css, js, data (routes, calculators), figures (SVG)
├── cadkit/                    Python toolkit: python3 -m cadkit
├── examples/                  synthetic plate, clearance coupon, calculations
├── templates/                 worksheets and registers
├── scripts/                   build, figures, PDF, checks, link check, GitHub refresh, dist
├── tests/                     python/ (unittest) and node/ (node --test)
└── output/pdf/                the PDF handbook (generated)
```

## Build and test

Reading needs nothing but a browser. To rebuild or test, install Node 20+ and Python 3.10+, then run from this folder:

```bash
make test
```

```bash
make release
```

`make release` rebuilds the calculations, figures, HTML, and PDF, renders the OpenSCAD plate, and runs the Python, Node, and browser tests. It then records [`verification.json`](verification.json) and writes a checksum manifest and ZIP archive to `dist/`. [`BUILD.md`](BUILD.md) lists the dependencies, every target, and the environment variables. The GitHub Actions workflow `reference-library.yml` runs the tests and the browser check on every change to this folder. It also fails when a generated file is out of date.

## What this library does and does not establish

The handbook combines official documentation, research leads, and original engineering synthesis. Every catalog entry records how deeply it was reviewed, and recent research is labeled by review depth. The worked examples are synthetic and are reproduced by code. OpenSCAD renders of the two example parts are checked for extents, closure, orientation, connectivity, and minimum walls.

No real photographs were reconstructed. No part was sliced or printed, and no printer, material, or reconstruction package was qualified or benchmarked. Repository metadata is a snapshot, not a quality score. Read [`VERIFICATION.md`](VERIFICATION.md) before relying on any result.

## Revision history

See [`CHANGELOG.md`](CHANGELOG.md). Revision 4 adds a local photo workspace with repeatable multi-photo intake, viewpoint coverage, and traceable image measurements. Revision 3, the first revision kept in this repository, added the figures, toolkit, Python package, example pipeline, automated tests, a reproducible PDF and archive, and a refreshed metadata snapshot. Revision 2 added governing decisions, single-view calibration checks, Workflow E, held-object design, and seven sources. Revision 1 was the initial library with 79 resources.
