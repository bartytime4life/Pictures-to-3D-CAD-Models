# Synthetic calculation and CAD examples

These examples teach the workflow. They do not reconstruct a supplied photograph, establish a real part's dimensions, or qualify a print.

## Files

- `two-hole-plate.scad`: editable OpenSCAD source for the handbook's 60 × 30 × 4 mm plate with two 5 mm holes spaced 40 mm apart. Its values are defaults that `build_plate.py` overrides from the parameter register.
- `plate-parameters.csv`: the plate's design-parameter register, in the `templates/design-parameters.csv` format. This is the single parameter source. The values are labelled `synthetic` or `proposed`, so they count as inferred evidence, not measurements.
- `build_plate.py`: reads the register, renders the plate with `openscad -D` overrides to a binary STL in `output/`, analyzes the mesh with `cadkit`, applies consistency and design-rule checks, and writes `output/validation-results.csv` in the `templates/validation-results.csv` columns. It exits with status 1 if any check fails.
- `clearance-coupon.scad`: a parameterized strip of through-holes for testing diametral clearance (hole minus pin). The defaults are a 5 mm pin and clearances of 0.10 to 0.50 mm in 0.10 mm steps. Labels can be off, engraved, or embossed. A corner notch marks the smallest-clearance end. These are example test settings, not recommended fits.
- `two-hole-plate.svg`: dimensioned schematic of the same teaching values. It is a diagram, not an inspected manufacturing drawing.
- `calculate.py`: reproduces the handbook's worked numbers using `cadkit.calc`. These cover planar scale, first-order uncertainty, chordal tessellation, and the gear example, plus the Revision 2 examples: a calibration proportion check, off-plane depth correction, camera distance from a 35 mm-equivalent focal length, label rounding uncertainty, and coating loss in a slot. The output is `calculation-results.json`.

## Run

From the `reference-library` directory:

```bash
python3 examples/calculate.py            # rewrite calculation-results.json
python3 examples/calculate.py --check    # confirm the committed JSON is current
python3 examples/build_plate.py          # render and check the plate (needs OpenSCAD)
openscad -o coupon.stl examples/clearance-coupon.scad
openscad -o coupon.stl -D pin_diameter=3 -D 'label_mode="engrave"' examples/clearance-coupon.scad
```

`build_plate.py` prints a skip message and exits 0 when OpenSCAD is not installed. Pass `--require-openscad` to make a missing OpenSCAD an error. `output/` contains generated build products and can be deleted.

## What was rendered and checked

The following was run with OpenSCAD 2021.01 on November 8, 2026. The checks read the generated STL files.

**Two-hole plate** (`build_plate.py`, default register). The render has 220 triangles and 108 welded vertices, and forms one closed, consistently oriented component of genus 2, one handle per through-hole. Its extents are exactly 60 × 30 × 4 mm. Each hole is a 25-segment polygon with its vertices on the 2.5 mm radius at x = ±20 mm, within 2 × 10⁻⁶ mm. The volume is 7044.569 mm³. That matches the inscribed-polygon expectation of 7044.569 mm³ to better than 10⁻⁵ relative error, and is 1.65 mm³ more than ideal circular holes would leave. Design rules with a 2 mm minimum wall pass: end walls 7.5 mm, side walls 12.505 mm, and a 35.020 mm web between holes. The side wall and web are measured at polygon vertices, which is why they differ from the 12.5 and 35 mm values for true circles.

**Clearance coupon** (defaults). The render has 560 triangles and forms one closed, consistently oriented component of genus 5, one per hole. Its extents are 41.687 × 9.537 × 4 mm, and its volume is 1138.68 mm³. The hole polygons use 26 or 27 segments. Polygon compensation is on by default: it places each polygon's flats, rather than its vertices, on the hole diameter, so a pin of the hole diameter passes. The tests confirm the vertex radius `r / cos(180° / n)` to within 2 × 10⁻⁵ mm. Engraved and embossed label variants also render as single closed components of genus 5.

These are geometry checks of the CAD output. Slicing, printing, and measurement of a physical part were not performed. A clearance that suits one printer, material, orientation, and finish does not transfer to another.

## Polygon holes and fit

OpenSCAD places polygon vertices on the circle, so a hole of diameter `d` drawn with `n` segments only passes a pin of `d cos(180°/n)`. For a 5 mm hole with 25 segments, that is 4.9606 mm, a loss of about 0.04 mm. That is close to the size of a whole clearance step, so the coupon compensates by default (`compensate_polygon = true`). The plate does not, to stay consistent with the handbook's tessellation example. A real fit-critical hole should either compensate in this way or use the CAD package's chordal export settings (handbook section 12).

For a real reconstruction, replace assumptions with measured values. Define tolerances from function and from demonstrated process capability.
