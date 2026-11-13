# Verification record

Checked November 9, 2026 (Revision 7). The machine-readable record is [`verification.json`](verification.json), written by `make verify` (`scripts/record-verification.py`). The command checks required inputs before writing, then runs a final documentation-agreement check. That final check can fail after the JSON is written; file existence alone is not a successful verification. See the [build and verification instructions](BUILD.md).

Documentation correction, November 12: the browser file count below now matches
the existing dated receipt. The receipt, check date and release status were not
regenerated for this correction.

Repository documentation update, November 13: the
[current review](../docs/validation/documentation-inward-margin.md) links the
[local acquisition-recovery snapshot](../docs/finite-acquisition-recovery.md).
That separate synthetic research retains 4/12 original matched target passes
and 9/12 continuation passes; both earlier full protocols exited 1. The 459 focused tests
belong to the candidate source, not main or this library. Its first saved-data
audit also exited 1: 14 comparisons require pre-cast area differences that the
rounded capture arrays do not preserve. No other inconsistency was reported by
that audit, within its stated exclusions. These are separate evidence records,
not a refreshed library verification. The dated release counts, catalog,
verification.json, generated reader and PDF remain unchanged by this update.

The later local [coupled search](../docs/finite-acquisition-coupled.md) and
[source-event strategy](../docs/finite-acquisition-events.md) each finish at
11/12 matched passes, with both earlier full protocols failed. Their
[results](../docs/validation/finite-acquisition-continuations.md) and
[saved-only audits](../docs/finite-acquisition-saved-audit.md) retain first
failures and 28 historical precision unknowns. They do not refresh this
library's release verification or add a Photos tool.

The [protected-source-bin design](../docs/finite-acquisition-protected.md)
retains its eight failed first controls. The
[active-face follow-up](../docs/finite-acquisition-protected-active.md) preserves
its first expectation failure, passes a separately frozen selected 821 tests
and 33 subtests, then completes the original 24-case study at 11/12 matched
passes, exit 1. The later [saved-only physical-rounding diagnostic](../docs/finite-acquisition-physical-rounding.md)
accepts none of 128 adjacent physical candidates. These
[source-bound results](../docs/validation/finite-acquisition-physical-rounding.md)
add no library feature, release verification or physical acceptance.

A separately frozen [inward-margin follow-up](../docs/finite-acquisition-inward-margin.md)
passes 103 selected controls and all five gates for 128 new adjacent
corners. Its independent saved-only audit passes 8,030 checks. The earlier
0/128 result is preserved; actual PNG cost and recovery improvement remain
untested. See [the new evidence](../docs/validation/finite-acquisition-inward-margin.md).

## What was checked automatically

The checks fall into the three tiers described in handbook section 18. Tiers 1 and 2 ran; tier 3 did not.

### Tier 1: consistency (the package agrees with itself)

- **Catalog:** 88 entries with unique IDs and URLs. Each has a purpose, a limitation, a known review-depth label, an ISO check date, and an https URL without tracking parameters. The 21 GitHub repository entries also carry repository metadata that matches their URLs. The builder refuses to run if any of this fails.
- **Generated files:** `sources.csv`, `REFERENCES.md`, and `GITHUB.md` match `sources.json`. The catalog chart shows the current source count, and every figure is used somewhere.
- **Documentation:**
  - The counts in `README.md` and in this file match the data. The revision label matches `library.json`, the handbook, and the changelog.
  - Every relative link in the Markdown files resolves.
  - Every external link in the handbook and research notes is a catalog entry.
  - Every `cadkit` command is listed in handbook section 23 and in `cadkit/README.md`.
- **Worked numbers:** `examples/calculate.py` reproduces every synthetic number in the handbook, and the tests assert that the handbook text states the same values. The values checked are scale and uncertainty, tessellation, calibration proportions, off-plane depth, camera distance, label rounding, coating loss, gear relations, and the stated guard-band acceptance example.
- **Two implementations:** for the handbook's examples and additional inputs, the browser calculators (`assets/js/cadcalc.js`) agree with `cadkit` to a relative difference of at most 1 × 10⁻¹². The homography fits agree in their matrix, residuals, local scale, and warnings. All 35 route-finder input and goal pairs give identical answers in both languages.
- **PDF:** 59 pages, with embedded DejaVu fonts, a contents page and outline, numbered pages, all ten figures, and hyperlinks to all 88 catalog URLs. For Revision 4, two consecutive PDF builds, two HTML builds, and two runs of `make dist` were each byte-identical. The PDF was also identical whether built with ReportLab 4.4.9 (the Codex runtime) or 4.5.1 (the `reference-library/.venv` that `make setup-library` creates from `requirements.txt`), and the generated HTML, CSV, Markdown, and figures were identical when rebuilt with that environment's Python. Revision 3 also compared HTML built with `marked` from the Codex runtime against `npm install`; that comparison was not repeated. For the Revision 4 maintenance, the PDF rebuilt with the `.venv` was byte-identical to the committed file, a second HTML and PDF build changed nothing, and two runs of `make dist` gave the same archive. Revision 6 rebuilt the PDF after the library integration. Revision 7 adds the OpenSCAD handoff; no new cross-version reproducibility claim is made.

### Tier 2: design rules (the examples and the interface can work)

- **Synthetic plate:** `examples/build_plate.py` reads `examples/plate-parameters.csv` and renders `two-hole-plate.scad` with OpenSCAD 2021.01. Its STL passed all 16 checks:
  - extents of 60 × 30 × 4 mm
  - one connected component, closed and consistently oriented, with no non-manifold vertices
  - genus 2
  - hole positions and radii
  - a volume matching the inscribed-polygon expectation
  - end walls, side walls, and the web between holes at or above the 2 mm minimum wall
- **Clearance coupon:** `clearance-coupon.scad` renders with and without labels. Each render is one closed component with one handle per hole, and its compensated hole polygons have the intended vertex radius. See `examples/README.md` for the numbers.
- **OpenSCAD workspace:** the browser checks cover the plate and coupon, dimensional sketches, exact numeric SCAD/CSV/SVG downloads, evidence and source fields, persistence, invalid dimensions, unavailable browser storage, and responsive layout. The same assertions run over both `file` and `http`; the selected transport is recorded under `openscad_workspace_checks`.
- **Native handoff:** the actual browser-downloaded SCAD files are rendered with OpenSCAD, and their CSVs independently drive native builds. Both paths check the resulting solids. `make verify` requires a current passing browser result followed by a passing native receipt, or an explicit native skip when OpenSCAD is unavailable. Download hashes must still match the native receipt. Bundled synthetic plate and coupon starters retain their own successful check records and output hashes. Physical printing remains untested.
- **Mesh checker:** synthetic cases with known answers exercise `cadkit meshcheck`: closed and open boxes, separate components, point-only connections, boundary vertex fans, flipped faces, degenerate triangles, invalid numeric geometry, unit hints, and binary files whose header starts with `solid`.
- **Browser:** 112 assertions per run in Chrome through Playwright, tested both as an offline `file` URL and over loopback `http`; the final record uses `http`:
  - **Navigation:** tabs by mouse and keyboard, deep links to tabs, chapters, and calculators, and a contents list with all 23 chapters.
  - **Toolkit:** all 14 calculators with correct default results, reset, and warnings. Empty, negative, and malformed inputs are reported as errors rather than computed as zero. The route finder's answers and calculator links are checked too.
  - **Catalog:** search, topic, review-depth, and sort filters. The filter state is written to the URL and restored after a reload, including topics containing "&" and searches containing "+".
  - **Files and figures:** 33 local files resolve in the recorded browser check, every in-page link has a target, and all figures load.
  - **Theme, keyboard, and safety:** the theme persists across reloads, and dark mode applies. `/` focuses the search, while Ctrl+/ does not. Script-like text and malformed escapes in the URL hash are treated as data.
  - **Layout:** no horizontal page overflow at 390 × 844 on any tab, and no JavaScript or console errors at 1440 × 1050.
- **Test suites:** 180 Python tests. OpenSCAD tests are skipped automatically where it is not installed. 58 Node test groups cover calculator parity, photo validation, portable transfer, and CSV evidence handling. Exact current counts appear in `verification.json`.

- **Photo workspace:** 67 assertions per run in separate isolated Chrome acceptance checks, over both `file` and `http`, use generated raster images only. It checks repeated imports beyond the 24-thumbnail page size, exact-byte duplicates, original-byte preservation, reload persistence, viewpoint/notes editing, unsaved-change status and discard protection, safe text rendering, filtering and paging, a known 5 mm result, invalid measurement rejection, metadata export, concurrent duplicate writes, quota-failure rollback, corrupt/unsupported-file feedback, per-photo removal, drag-and-drop cancellation and resume, blocked-storage guidance, and desktop/dark/mobile layouts. The exact assertion count and scope are recorded in `verification.json` under `photo_workspace_checks`.
- **Storage boundaries:** images are saved only after a complete IndexedDB transaction. A failed import stops on storage failure while retaining already committed photos. The gallery reads at most 24 thumbnails per page; original blobs are read only for a selected image. There is no hard total-count cap, but device/browser storage, 50 MiB per file, and 60-megapixel image limits still apply. Browser data is not a backup.

- **Portable photo transfer:** 49 assertions in isolated browser checks export synthetic original files using real browser file handles and restore that folder into a separate browser context. They verify original fingerprints, labels and measurements, repeat restore behavior, invalid or incomplete inputs, cancellation, and clear support/failure states. The native folder chooser is injected; no real user folder or personal photo collection is used. Exact results appear under `photo_transfer_checks` in `verification.json`.
- **Measurement CSV:** tests compare the header to the project template, verify a known image ratio, retain the image-derived evidence class, keep unknowns blank, and neutralize spreadsheet formula prefixes in user text. CSV output is not an accepted CAD parameter register.

### Independent review

Revision 6 added independent reviews of catalog behavior, photo draft protection, and mesh vertex checks. Outstanding detail writes retain navigation protection after the editor closes; gallery and detail images release their source before preview URLs are revoked. An isolated controller stress run exercised 20 save/close/reopen cycles and 80 refresh triggers. Revisions 4 and 5 received independent reviews of photo intake, editing, and portable transfer. Delayed save/remove operations preserve newly opened drafts, photo opens already in flight cannot reveal editors during transfer, and late gallery renders retain the transfer control locks. Renamed originals with empty or generic MIME types are recovered by their image signatures and fingerprints.

A separate code review of the Revision 3 scripts and interface reported 15 correctness issues. All were fixed, and the substantive ones now have regression tests. They included:

- catalog URL state losing topics that contain "&"
- empty calculator fields being computed as zero
- a stale browser record that could be counted as a pass
- small differences between the JavaScript and Python rounding and eigen-solver stopping rules
- two Python inputs that crashed instead of reporting an error
- PDF worksheets that had lost their checkboxes since Revision 1

### External links (network, informational)

Revision 6’s `make links` requested all 91 unique catalog and Markdown URLs on November 9, 2026: 89 responded successfully, two Smithsonian pages refused the automated client with HTTP 403, and none timed out or were classified broken. A blocked request is not evidence that a page is gone. This is an availability check, not a fresh review of every page's contents; individual review dates and depths remain in `sources.json`.

### Preserved repository maintenance

This integration retains the repository's strict ASCII STL parsing, distance-based vertex welding, finite and overflow checks, CSV byte-order-mark support, homography query validation, Python/browser rounding agreement, and both offline-file and loopback-HTTP browser checks. Browser results record their actual transport.

## Boundaries

Source review depths vary. Some records are official page content, some search-index excerpts, some abstracts, and others repository or bibliographic metadata. Specific retrieval limitations are documented in `RESEARCH-NOTES.md`. The package does not claim that all linked websites were fully reviewed or that every external link will remain available.

The Photos tab prepares references; it does not reconstruct a mesh, infer camera poses, correct image perspective, or prove improved dimensional accuracy. Viewpoint coverage follows manual labels. Known-length photo measurements are estimates on a shared plane, and their points and reference length are retained for review.

The calculators and checks are arithmetic and geometry on stated inputs. Agreement between the JavaScript and Python implementations shows that they compute the same thing, not that the formulas suit a particular camera, part, or printer.

The OpenSCAD checks show that the synthetic CAD sources produce the intended closed solids. They are not slicing, printing, fit, strength, or dimensional-metrology results.

Native builds use only synthetic defaults or explicitly supplied parameter registers. Their output directories are new, completed exports are preserved on render failure, and personal builds are excluded from the portable library archive.

No real photo reconstruction, slicing, printing, load test, dimensional metrology, AI reconstruction run, or comparative software benchmark was performed. The methods are engineering synthesis and have not been validated on a physical object.
