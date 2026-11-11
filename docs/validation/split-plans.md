# Suggested split plans — November 11, 2026

Candidate branch `codex/minimum-fit-splits`, based on `main` at `48e17d2`.
Work used an isolated checkout at
`/home/bartytime/.codex/worktrees/picad-split-plans`. The original checkout
and the previously running merged-workbench preview were preserved.

## What was checked

- A 250 × 80 mm polygon on a 140 × 100 mm usable bed receives a 2 × 1
  proposal with two pieces. A 250 × 10 mm strip on a 100 × 100 mm usable
  bed also receives two pieces, each fitting after a 45° turn.
- A 100 × 100 mm L-shaped polygon with 10 mm arms on a 50 × 50 mm usable
  bed receives a 2 × 2 grid with three actual pieces, excluding the empty cell.
- Every proposed piece is independently rotated with Shapely and compared
  with the usable envelope. The clipped pieces retain source area and union.
  The source polygon and measured design settings remain unchanged.
- A successful two-build API check preserves original dimensions and volume,
  retains the through-hole, and matches generated piece dimensions and fit
  witnesses to the proposal. A 200 mm reference at 125% design scale retains
  its reference and percentage while producing the same 250 mm design before
  and after splitting. STEP re-import confirms two solids and one top-face
  inner wire. Before application, the recipe and slicer bundle
  still describe one unsplit part; no proposed pieces are exported as actual
  geometry.
- Excessive thickness, exhausted margins, the eight-piece limit, shaped or
  excluded beds, already-fitting diagonal parts and fitted single-piece curves
  retain conservative results. Injected numerical intersection failures do
  not discard the intact build, and partial searches are explicitly qualified.
- Desktop and 390 px mobile browser scenarios confirm explicit application,
  unchanged width and thickness, export invalidation, no automatic build on
  application, actual generated pieces after rebuild, keyboard access,
  automated axe checks and no page-wide horizontal overflow. Editing the bed
  invalidates an old proposal.

The accepted [desktop](../images/split-plan-desktop.png) and
[mobile](../images/split-plan-mobile.png) screenshots were visually inspected.

## Local results

- Python suite: **470 passed**.
- The API/export case was rerun with additional STEP-topology and measured
  reference/design-scale assertions after the full run.
- Chromium suite: **51 passed** across two batches: the two new split-plan
  scenarios, followed by all 49 existing browser regression scenarios.
- Production TypeScript/Vite build, `make lint` and `git diff --check`: passed.
- All 88 local documentation links checked in the changed guides resolve.
- One synthetic 2000-vertex, 140 mm diameter polygon on a 100 × 100 mm usable
  bed received four pieces in a 2 × 2 grid in 0.140 seconds locally. This is one
  timing sample rather than a latency or throughput guarantee.

This verifies bounded grid search and local software behavior. It does not
qualify arbitrary cut paths, joinery, structural performance, kerf, several
pieces arranged together, native slicer acceptance, physical fit or printing.
Each proposed piece still requires a successful CAD build and slicer review.
Hosted CI and merge state are separate from these local results.
