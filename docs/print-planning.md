# Print planning and user control

Printer presets provide a starting point for checking whether a model fits a
build volume. They do not replace a slicer or establish that a particular
material, orientation, or model will print successfully.

## Printer catalog and checked examples

The bundled catalog contains **429 printer model groups, 1,106 nozzle-specific
profiles, and 70 manufacturer or profile families** from OrcaSlicer's
open-source machine profiles. It works offline; see [the catalog guide](printer-catalog.md)
for coverage, provenance, and regeneration. The three examples below were
checked on November 8, 2026, at commit
`f55615d7488fe570942f5e25548b8ab9b30778d0`. X and Y come from the profile's
`printable_area`; Z comes from `printable_height`. Each selected variant specifies
a 0.4 mm nozzle. The physical nozzle installed on the user's machine may differ.

| Starting preset     | X × Y × Z, mm            | Selected nozzle, mm | Profile evidence                                                                                                      |
| ------------------- | ------------------------ | ------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Bambu Lab A1        | 256 × 256 × 256          | 0.4                 | [A1 machine profile][a1] supplies height and nozzle; [inherited common profile][a1-common] supplies the XY rectangle. |
| Prusa MK4S          | 250 × 210 × 220          | 0.4                 | [MK4S variant][mk4s] supplies the selected nozzle; [MK4S common profile][mk4s-common] supplies XY and height.         |
| Creality Ender-3 V2 | 220 × 220 × 250          | 0.4                 | [Ender-3 V2 profile][ender] supplies all four values directly.                                                        |
| Custom              | User-entered X, Y, and Z | User-entered        | Use the actual printer and nozzle configuration.                                                                      |

The catalog retains nozzle-specific dimensions and excluded areas. Its listed
dimensions are slicer-profile bounds, which can differ from advertised machine
dimensions. Enclosure, automatic leveling, material compatibility, and installed
accessories remain unknown unless separately verified; an empty fact is not a
claim that the printer lacks that feature.

A custom usable volume can be smaller than the
nominal machine volume because of clips, excluded areas, or the user's setup.
An application edge margin is a planning allowance, not a manufacturer
specification; display its value and let the user change it.

For this workbench's flat parts, the fit check compares thickness with usable Z
height, subtracts the selected margin from both edges of each bed axis, and
searches every in-plane rotation of each built polygon. It preserves familiar
0° or 90° placements when they work. Otherwise it finds a feasible angle from
the outline's convex hull and analytic trigonometric crossings, including
placements between fixed angular steps. Holes and concavities do not change
the directional extents needed for containment in a clear rectangle.

For example, a 125 × 10 mm bar exceeds a 100 × 100 mm usable square in either
axis orientation, but at 45° its footprint is approximately 95.46 × 95.46 mm.
The old two-orientation check rejected it; the continuous-angle check finds a
placement without scaling or splitting the measured part. The solver finds a
feasible placement; it does not claim a globally optimal clearance or plate packing.

Open the per-piece result to inspect the approximate counterclockwise turn
about model Z and its footprint in millimeters. The full-precision angle,
footprint and geometry basis are preserved in parts and slicer handoff manifests.
These are placement suggestions: exported STEP, STL and 3MF geometry retains
its original orientation. Apply the turn, translate onto the plate, and verify
it in your slicer. Displayed numbers are rounded; close fits need extra care.

Fitted arcs and circles use the exact solid's enclosing rectangle, avoiding
an unsafe fit based on inscribed samples of a curve. A positive rectangle
result contains the actual solid. A failed rectangle result is **unknown**,
because a curved outline could fit where that rectangle does not. Polygon
results use the actual built outline after simplification or splitting. Shaped,
excluded and ambiguous catalog beds remain unverified.

This check does not account for a brim, raft, skirt, supports, purge structures,
toolhead clearance, or a slicer's placement rules. The 0.000001 mm comparison
tolerance accommodates floating-point arithmetic; it is not a physical allowance
or an accuracy estimate. See [algorithm derivation and sources](research.md#continuous-angle-rectangular-placement).

Prefer “Fits these geometric bounds” to “Ready to print.” A model that exceeds a
printer preset can still be valid CAD; choosing another printer or changing the
print plan should not silently rescale the measured part.

## Materials and appearance

Keep material and color as explicit user choices. A color changes the preview
and saved plan; it does not select a physical filament spool or prove that an
export preserves color. STL has no standard material/color representation.
Report exactly what each export includes.

| Planning choice | Useful guidance                                                                                                                 | What it does not establish                                                      |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| PLA             | A reasonable starting choice for a visual prototype; select the printer's appropriate PLA profile in the slicer.                | Heat suitability, structural performance, or compatibility with every printer.  |
| PETG            | An alternative to evaluate with the actual filament's profile, build surface, and adhesion guidance.                            | A universal improvement over PLA or a calibrated dimensional fit.               |
| ABS             | Review the printer and filament maker's required environment, enclosure, ventilation, and warping guidance before selecting it. | That a stock open printer or a generic ABS preset is appropriate for the job.   |
| ASA             | Review the filament and printer's enclosure, ventilation, adhesion, and profile guidance.                                       | A universal replacement for ABS or qualified outdoor performance for this part. |
| TPU             | Check the filament's hardness and the printer's feeder/path requirements, then use an appropriate flexible-filament profile.    | Reliable feeding or a particular flexibility from the material name alone.      |
| Nylon           | Check the exact nylon formulation, drying instructions, build surface, and printer profile.                                     | A single universal nylon temperature or validated mechanical performance.       |

OrcaSlicer has distinct [PLA][pla], [PETG][petg], and [ABS][abs] profiles for the
MK4S, including explicit compatible-printer lists and different print settings.
That is evidence that material settings depend on the printer/profile pairing;
it is not a universal compatibility test. This workbench should not copy
temperatures from one profile into instructions for all machines or infer part
strength from the material label.

## Detail relative to size and nozzle

Four different quantities need different labels:

1. **Trace detail** controls how the image contour is approximated. More vertices
   can preserve visible features or preserve noise. It does not measure wall
   thickness or recover information absent from the photograph.
2. **Nozzle-relative detail mode** simplifies the scaled contour using a distance
   tolerance of 0.5, 0.25, or 0.1 times the nozzle diameter for draft, balanced,
   or fine. With a 0.4 mm nozzle these tolerances are 0.2, 0.1, and 0.04 mm.
   Original mode keeps the input contour unchanged. This geometric tolerance is
   not an estimate of printer accuracy or the minimum printable feature.
3. **Physical feature size** is a distance measured on the scaled CAD geometry.
   Scaling the part changes this size, so it can change which details deserve a
   print review. A spacing between polygon vertices is not automatically a wall
   width or a hole diameter.
4. **Nozzle-relative feature size** is a measured feature size divided by the selected
   nozzle diameter. It is an explanatory ratio, not a slicer simulation: actual
   extrusion widths can differ from the nozzle diameter.

For example, a 0.3 mm measured feature is 0.75 nozzle diameters with a 0.4 mm
nozzle; a 0.8 mm feature is two nozzle diameters. As a conservative review
heuristic, flag sub-nozzle details for slicer inspection and ask the user to
review narrow one-to-two-nozzle features. Do not promise that a feature above
that range will print, or automatically delete a smaller feature. These review
bands are application guidance, not values supplied by the printer profiles.

This implementation does not measure minimum wall or feature thickness. The
feature examples and review bands above explain how to inspect a model in a
slicer; they are not checks that the workbench has performed. A part-width/nozzle
ratio only describes overall scale. An AI suggestion to simplify a trace or
change overall dimensions must identify which setting or geometry will change
and wait for the user's decision.

## One piece and multiple pieces

Start with the intact solid. If it exceeds the chosen geometric bounds, a
reviewable plan can offer another printer, a supported orientation, or a
division into smaller pieces. Scaling is a separate dimensional change, not an
automatic fit fix.

A multi-part implementation based on straight planar cuts needs to show its
cut count, direction, and resulting piece dimensions. Verify every generated
solid and check each piece against the chosen bounds. A split may cross holes
or thin regions; show the result before export. A straight cut does not create
alignment pins, joints, fastening provisions, assembly tolerances, or a tested
way to recover the original part's function.

Distinguish these outcomes:

- A **suggested split plan** describes proposed cuts but has not produced parts.
- **Generated parts** are actual separate geometric solids or meshes available
  for inspection and export.
- A **slicer plate** places parts and contains slicing settings. A geometric
  split alone does not produce one.
- **Machine G-code** is generated and reviewed using the correct slicer,
  printer, nozzle, and material profile. It is outside a geometric fit check.

Until toolpaths, supports, placement, material behavior, and machine settings
are actually evaluated, describe any “optimization” as a specific operation:
for example, choosing between the checked orientations or reducing the number
of straight-cut pieces that fit the selected geometric bounds.

### Suggested split plans

After a built polygon exceeds the selected rectangular bed, **Design & print**
searches the supported straight-cut grids and offers the one with the fewest
fitting pieces. It considers all eleven nontrivial combinations of 1–4 columns
and 1–4 rows with at most 8 cells. It clips the actual outline, counts connected
pieces rather than empty cells, checks area preservation, and tests every piece
with the continuous-angle placement solver. Plans producing more than 8 pieces
are unsupported. Ties prefer fewer cut lines, then fewer rows and columns.

For example, a 250 × 80 mm plate on a 140 × 100 mm usable bed can be cut into
two 125 × 80 mm pieces. An L-shaped 100 × 100 mm outline with 10 mm arms can
produce three pieces from a 2 × 2 grid on a 50 × 50 mm usable bed: the fourth
cell is empty. A long narrow piece may fit its cell only after an XY turn.

The proposal does not generate or export parts. **Use suggested split** sets
Output, Columns and Rows, invalidates the previous fit and exports, and keeps
measured dimensions unchanged. Select **Update model** to generate and inspect
the actual solids, cut locations and exports. The ordinary Output, Columns and
Rows controls remain editable. Changing the source, scale, bed or other build
settings hides an old suggestion until a fresh build. Saved recipes and slicer
manifests describe the built or explicitly selected settings, not unapplied
proposals.

Single-piece fitted curves and unverified shaped, excluded or ambiguous beds
do not receive polygon split suggestions. Splitting cannot correct excessive
thickness or a margin that leaves no usable bed. If no supported grid fits,
the workbench explains that search limit. A numerical failure checking a grid
is reported as an incomplete search, without discarding the original build.

This minimizes piece count within the supported grids. It does not find arbitrary
cut paths, preserve structural strength, add joinery, compensate kerf, or arrange
several pieces on one plate. Each proposed piece still needs a successful CAD
build and review in the slicer. See [the search derivation](research.md#bounded-split-plan-search)
and [validation](validation/split-plans.md).

## Reviewed changes and undo

The assistant should present a concise explanation and a before/after proposal
for geometry, appearance, material, trace detail, printer selection, or a split
plan. A proposal is tied to the project state it analyzed. If the user edits the
project before applying it, require a fresh proposal rather than applying stale
assumptions.

Applying a proposal should be one deliberate action with an undo snapshot of
all settings it changes. Geometry changes invalidate previous builds and
exports until the model is rebuilt. Appearance or planning metadata should not
silently alter dimensions. Undo should restore the prior settings and clearly
indicate whether rebuilding is needed. A failed suggestion must leave the
normal manual controls usable.

[a1]: https://github.com/SoftFever/OrcaSlicer/blob/f55615d7488fe570942f5e25548b8ab9b30778d0/resources/profiles/BBL/machine/Bambu%20Lab%20A1%200.4%20nozzle.json
[a1-common]: https://github.com/SoftFever/OrcaSlicer/blob/f55615d7488fe570942f5e25548b8ab9b30778d0/resources/profiles/BBL/machine/fdm_bbl_3dp_001_common.json
[mk4s]: https://github.com/SoftFever/OrcaSlicer/blob/f55615d7488fe570942f5e25548b8ab9b30778d0/resources/profiles/Prusa/machine/Prusa%20MK4S%200.4%20nozzle.json
[mk4s-common]: https://github.com/SoftFever/OrcaSlicer/blob/f55615d7488fe570942f5e25548b8ab9b30778d0/resources/profiles/Prusa/machine/fdm_machine_common_mk4s.json
[ender]: https://github.com/SoftFever/OrcaSlicer/blob/f55615d7488fe570942f5e25548b8ab9b30778d0/resources/profiles/Creality/machine/Creality%20Ender-3%20V2%200.4%20nozzle.json
[pla]: https://github.com/SoftFever/OrcaSlicer/blob/f55615d7488fe570942f5e25548b8ab9b30778d0/resources/profiles/Prusa/filament/Generic%20PLA%20%40Prusa%20MK4S.json
[petg]: https://github.com/SoftFever/OrcaSlicer/blob/f55615d7488fe570942f5e25548b8ab9b30778d0/resources/profiles/Prusa/filament/Generic%20PETG%20%40Prusa%20MK4S.json
[abs]: https://github.com/SoftFever/OrcaSlicer/blob/f55615d7488fe570942f5e25548b8ab9b30778d0/resources/profiles/Prusa/filament/Generic%20ABS%20%40Prusa%20MK4S.json

## Current interface

[Design and print controls](images/design-print.png) keep source measurements separate from design scales and show the selected printer's limits. The [separated-pieces view](images/separated-pieces.png) displays real exported geometry with inspection-only spacing. [Mobile controls](images/design-print-mobile.png) use the same settings and explicit review flow.

## Continue in Bambu Studio or PrusaSlicer

The export dialog hands the current built geometry and printer/material plan to either slicer through a [3MF handoff package](slicers.md). Split pieces remain separate files for deliberate arrangement. Planning choices from this workbench do not become native printer or filament presets; choose those inside the slicer and verify placement and layer preview there. No toolpaths or print commands are generated by the handoff.
