# Conservative curved placement — November 11, 2026

Candidate branch `codex/curved-bed-envelope`, based on `main` at `5cebd27`,
in `/home/bartytime/.codex/worktrees/picad-curve-fit`. Work preserved the original
checkout, the merged preview, and the earlier split-plan candidate.

## Reproduced before the change

A fitted 125 × 20 × 4 mm capsule with 10 mm end radii reported **unknown** on
a 100 × 100 mm usable square because its enclosing rectangle could not fit.
An independent STEP re-import rotated by 45° measured 94.246212 × 94.246212 mm
in XY. The analytic capsule extent is `105/sqrt(2) + 20` mm on each axis.

Screenshot review also exposed per-part dimensions of 125 × 20.01 × 4.01 mm
after meshing a capsule without holes, despite the 125 × 20 × 4 mm CAD design.
The existing bounding operation could use cached export triangulation. Analytic
CAD bounds now supply dimensions, normalization offsets and witness checks.

## Geometry checks

- The capsule now receives a 45° witness from an outer support polygon,
  with an approximately 94.246214 mm conservative XY footprint. A separate CAD
  kernel check confirms the rotated solid against the bed and that footprint.
  STEP stays unrotated, with exact arcs and optional circular through-hole.
- API checks cover the capsule both with and without a hole, source recipe
  preservation, one exported solid, expected analytic volume, STEP re-import,
  original orientation and the matching placement record in a handoff manifest.
- Clockwise and counterclockwise 90°, 180° and 270° arcs at two start phases,
  including wraparound, are enclosed after translation by 100,000 mm. Each
  case is compared with 4,097 independently generated points on its known
  circle, without reusing the support coefficients or arc reconstruction.
- A 24-vertex inscribed sample of a radius-50.01 mm circle can appear to fit
  a 100 mm square. The exact circle cannot; the new outer-bound check reports
  unknown and supplies no placement witness.
- A 2000-segment outline produces at most 256 enclosure vertices. This checks
  the fixed geometry budget, without claiming a runtime guarantee.
- Injected numerical enclosure failure, a wrong placement angle, an understated
  footprint and a CAD-kernel rotation failure all withhold the witness as unknown.
  The kernel failure is logged, and valid STEP geometry remains available.
- Curved-solid measurements stay 125 × 20 × 4 mm after tessellation. Shaped,
  excluded and ambiguous beds retain conservative behavior; excessive thickness
  and exhausted margins retain the existing checks.

## Browser checks

Desktop and 390 px mobile scenarios check the exact displayed part dimensions,
the 45° turn, the conservative-footprint explanation, keyboard disclosure,
automated axe checks and absence of page-wide horizontal overflow. Editing the
bed hides old results; rebuilding on an unsuitable smaller bed reports unknown
while preserving the fitted geometry and measurements. No split is proposed.

The accepted [desktop](../images/curved-placement-desktop.png) and
[mobile](../images/curved-placement-mobile.png) screenshots were visually inspected.

## Local results

- Python suite after the final geometry-bound change: **495 passed**.
- Chromium suite after the final geometry-bound change: **53 passed**.
- Production TypeScript/Vite build, `make lint` and `git diff --check`: passed.
- All 89 local documentation targets checked in the changed guides resolve.

These checks establish software geometry and conservative placement behavior.
They do not establish photographic accuracy, complete curved-containment
decisions, plate packing, native slicer acceptance, physical fit or printing.
Hosted CI, merge state and production deployment remain separate evidence.
