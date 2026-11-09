# Verification record

Checked November 8, 2026 (Revision 4). The machine-readable record is [`verification.json`](verification.json), written by `make verify` (`scripts/record-verification.py`), which refuses to write unless every required check passes.

## What was checked automatically

The checks fall into the three tiers described in handbook section 18. Tiers 1 and 2 ran; tier 3 did not.

### Tier 1: consistency (the package agrees with itself)

- **Catalog:** 86 entries with unique IDs and URLs. Each has a purpose, a limitation, a known review-depth label, an ISO check date, and an https URL without tracking parameters. The 21 GitHub repository entries also carry repository metadata that matches their URLs. The builder refuses to run if any of this fails.
- **Generated files:** `sources.csv`, `REFERENCES.md`, and `GITHUB.md` match `sources.json`. The catalog chart shows the current source count, and every figure is used somewhere.
- **Documentation:**
  - The counts in `README.md` and in this file match the data. The revision label matches `library.json`, the handbook, and the changelog.
  - Every relative link in the Markdown files resolves.
  - Every external link in the handbook and research notes is a catalog entry.
  - Every `cadkit` command is listed in handbook section 23 and in `cadkit/README.md`.
- **Worked numbers:** `examples/calculate.py` reproduces every synthetic number in the handbook, and the tests assert that the handbook text states the same values. The values checked are scale and uncertainty, tessellation, calibration proportions, off-plane depth, camera distance, label rounding, coating loss, and gear relations.
- **Two implementations:** for the handbook's examples and additional inputs, the browser calculators (`assets/js/cadcalc.js`) agree with `cadkit` to a relative difference of at most 1 × 10⁻¹². The homography fits agree in their matrix, residuals, local scale, and warnings. All 35 route-finder input and goal pairs give identical answers in both languages.
- **PDF:** 55 pages, with embedded DejaVu fonts, a contents page and outline, numbered pages, all ten figures, and hyperlinks to all 86 catalog URLs. Rebuilding unchanged sources gives a byte-identical file. For Revision 4, two consecutive PDF builds, two HTML builds, and two runs of `make dist` were each byte-identical. The PDF was also identical whether built with ReportLab 4.4.9 (the Codex runtime) or 4.5.1 (the `reference-library/.venv` that `make setup-library` creates from `requirements.txt`), and the generated HTML, CSV, Markdown, and figures were identical when rebuilt with that environment's Python. Revision 3 also compared HTML built with `marked` from the Codex runtime against `npm install`; that comparison was not repeated.

### Tier 2: design rules (the examples and the interface can work)

- **Synthetic plate:** `examples/build_plate.py` reads `examples/plate-parameters.csv` and renders `two-hole-plate.scad` with OpenSCAD 2021.01. Its STL passed all 16 checks:
  - extents of 60 × 30 × 4 mm
  - one connected component, closed, manifold at every edge and vertex, and consistently oriented
  - genus 2
  - hole positions and radii
  - a volume matching the inscribed-polygon expectation
  - end walls, side walls, and the web between holes at or above the 2 mm minimum wall
- **Clearance coupon:** `clearance-coupon.scad` renders with and without labels. Each render is one closed component with one handle per hole, and its compensated hole polygons have the intended vertex radius. See `examples/README.md` for the numbers.
- **Mesh checker:** synthetic cases with known answers exercise `cadkit meshcheck`: closed and open boxes, two components, flipped faces, degenerate triangles, unit hints, and binary files whose header starts with `solid`. The cases also cover boxes that touch at one vertex or share one edge, near-coincident points that straddle a welding-grid boundary, and translations that must not change the result.
- **Workbench exports:** the workbench's own test suite (`tests/test_mesh_interop.py` in the repository root) runs the same checker on its STL exports. Combined, traced, and split-part meshes are each closed, manifold, and outward-facing, with one genus per traced hole and volumes within 0.01 % of the CAD solid.
- **Browser:** 99 assertions in Chrome through Playwright, loading the page over the `file` transport (`file://`, as a reader opens it). CI repeats the same assertions over a private loopback HTTP server (`CAD_REFERENCE_BROWSER_TRANSPORT=http`).
  - **Navigation:** tabs by mouse and keyboard, deep links to tabs, chapters, and calculators, and a contents list with all 23 chapters.
  - **Toolkit:** all 14 calculators with correct default results, reset, and warnings. Empty, negative, and malformed inputs are reported as errors rather than computed as zero. The route finder's answers and calculator links are checked too.
  - **Catalog:** search, topic, review-depth, and sort filters. The filter state is written to the URL and restored after a reload, including topics containing "&" and searches containing "+".
  - **Files and figures:** 28 local files resolve, every in-page link has a target, and all figures load.
  - **Theme, keyboard, and safety:** the theme persists across reloads, and dark mode applies. `/` focuses the search, while Ctrl+/ does not. Script-like text and malformed escapes in the URL hash are treated as data.
  - **Layout:** no horizontal page overflow at 390 × 844 on any tab, and no JavaScript or console errors at 1440 × 1050.
- **Test suites:** 129 Python tests. OpenSCAD tests are skipped automatically where it is not installed. There are also 22 Node test groups, including 10 for photo validation, preparation, storage errors, and calibrated estimates.
- **Photo workspace:** `scripts/check-photos.mjs` passed 49 assertions in fresh Chrome contexts with generated raster images only, over the `file` transport and again over loopback HTTP. It checks:
  - repeated imports beyond the 24-thumbnail page size, exact-byte duplicates, original-byte preservation, and reload persistence
  - viewpoint and notes editing, text-only rendering of notes containing markup, filtering, and paging
  - a known 5 mm result from pointer-picked and typed endpoints, and rejection of out-of-image coordinates
  - metadata-only manifest export, concurrent duplicate writes, rollback after a simulated quota failure, and feedback for corrupt or unsupported files
  - per-photo removal with confirmation, drag-and-drop cancellation and resume, guidance when storage is blocked, a save or removal finishing after another photo was opened, and desktop, dark, and 390 px layouts
  - no image keeps or receives a revoked blob URL when gallery refreshes overlap (deterministic; it replaces a timing-dependent failure)

  The scope and per-check list are recorded in `verification.json` under `photo_workspace_checks`.
- **Storage boundaries:** images are saved only after a complete IndexedDB transaction. A failed import stops on storage failure while retaining already committed photos. The gallery reads at most 24 thumbnails per page; original blobs are read only for a selected image. There is no hard total-count cap, but device and browser storage, 50 MiB per file, and 60-megapixel image limits still apply. Browser data is not a backup.

### Independent review

A separate code review of the Revision 3 scripts and interface reported 15 correctness issues. All were fixed, and the substantive ones now have regression tests. They included:

- catalog URL state losing topics that contain "&"
- empty calculator fields being computed as zero
- a stale browser record that could be counted as a pass
- small differences between the JavaScript and Python rounding and eigen-solver stopping rules
- two Python inputs that crashed instead of reporting an error
- PDF worksheets that had lost their checkboxes since Revision 1

Revision 4's photo code, tests, and documents were read in full before it was added to this repository. That review missed a timing race in the gallery's blob-URL handling. CI exposed it after the merge, and it is fixed with a regression assertion; see the changelog. The port added the shared loopback transport for the photo check and the archive exclusion fix described in the changelog.

### External links (network, informational)

Revision 3's `make links` requested every catalog URL plus the external links in the Markdown files. Runs reached 84 of 86 catalog URLs. The two Smithsonian pages refused the automated client with HTTP 403. One run timed out on the whole open3d.org site, and a later run reached it again. `verification.json` records the most recent run; external availability was not rechecked for Revision 4. Neither status is evidence that a page is gone; see `RESEARCH-NOTES.md`. A responding URL does not mean its content was re-reviewed.

## Boundaries

Source review depths vary. Some records are official page content, some search-index excerpts, some abstracts, and others repository or bibliographic metadata. Specific retrieval limitations are documented in `RESEARCH-NOTES.md`. The package does not claim that all linked websites were fully reviewed or that every external link will remain available.

The calculators and checks are arithmetic and geometry on stated inputs. Agreement between the JavaScript and Python implementations shows that they compute the same thing, not that the formulas suit a particular camera, part, or printer.

The OpenSCAD checks show that the synthetic CAD sources produce the intended closed solids. They are not slicing, printing, fit, strength, or dimensional-metrology results.

The Photos tab prepares references; it does not reconstruct a mesh, infer camera poses, correct image perspective, or prove improved dimensional accuracy. Viewpoint coverage follows manual labels. Known-length photo measurements are estimates on a shared plane, and their points and reference length are retained for review.

No real photo reconstruction, slicing, printing, load test, dimensional metrology, AI reconstruction run, or comparative software benchmark was performed. The methods are engineering synthesis and have not been validated on a physical object.
