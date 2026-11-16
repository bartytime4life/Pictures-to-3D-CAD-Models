# Figure and base refinement: measured gains and reusable checks

[Documentation](../README.md) · [Sheet-axis mathematics](sheet-axis-orientation.md) · [Engineering checks](../engineering-model.md)

The November 16, 2026 Wolverine/Omega Red refinement moves existing figure meshes
rigidly and rebuilds their base interfaces. It is a separate character-model
pipeline. The workbench reconstructs flat, constant-thickness parts; its relief
mode and these documented results do not establish arbitrary 3D sculpt recovery.

The selected executed fields are in [summary.json](evidence/photo-model-quality-20261116/summary.json).
They were extracted from the final serialized-file image review, independent
mechanical review, pocket measurements and source-test receipts. The extractor
checks the bound source/delivered figure hashes and all seven mechanical STL
hashes before emitting the summary. Source commit:
`14194570fb5836ddc2aa483a9e81f1554b054d17` in the separate character CAD checkout.
The original review-record hashes are included. Photos, sculpts and local paths
are excluded from this repository evidence extract; the full model package is
required to reproduce the mesh checks. This JSON is a selection of existing run
results, rather than a new execution of that pipeline in the workbench.

## Image-space result on the actual exported figures

At the declared front-camera elevation of 21.2°:

| Omega Red comparison | Before | After |
| --- | ---: | ---: |
| Full-mask silhouette intersection over union (IoU) | 0.4613 | 0.5466 |
| Supported-pixel IoU | 0.5026 | 0.6188 |
| Supported upper-band IoU | 0.4852 | 0.5650 |
| Supported mean symmetric contour distance | 34.30 px | 20.61 px |

The supported mean contour distance falls **39.9%**. Full-mask IoU rises by
**8.53 percentage points**. Full, supported and upper-band IoUs and contour means
improve at all three checked elevations: 19.15°, 21.2° and 22.98°. Those elevations
are sensitivity scenarios, not a confidence interval. The reference is generated
concept art, so these numbers describe conditional image agreement rather than
3D anatomical or physical accuracy.

Wolverine remains byte-identical. Tested alternatives improved aggregate overlap
but worsened the upper head/claw region, so they were rejected. Omega uses a
−10° yaw and recorded translation; the rigid operation preserves distances and
angles. Its 780,474 ordered triangles remain identical after the expected STL
float32 coordinate rounding. Neither figure receives inferred anatomy, smoothing
or local deformation in this refinement.

For rendered silhouette A, reference mask B and fixed supported region Q:

```text
IoU_Q = |A ∩ B ∩ Q| / |(A ∪ B) ∩ Q|
```

Projected mesh triangles must form a union. Filling all triangle contours with
one even/odd polygon operation can cancel overlap and introduce artificial
holes. The corrected renderer fills each triangle into the occupied mask.
Contour distance is evaluated in both directions using the actual boundaries,
then the fixed evidence exclusions are applied. Exclusion rectangle edges do
not become new measured contours. The review also records full-mask scores and
retained contour coverage: Omega's supported rendered-contour coverage drops
from 76.38% to 74.71% at the principal camera, and by up to 3.22 percentage points
across scenarios. Remaining mismatch is substantial; the gain is not a claim of
complete agreement.

Regional comparisons prevent an aggregate score from hiding a worse distinctive
feature. Camera scenarios expose sensitivity to an assumed view. The same
principles apply when evaluating the workbench's traced outline, but this
character-specific mask and camera policy is not an automatic app validator.

## Base, sockets and the complete insertion path

A seated interference check does not establish an insertion path. For lower
figure solid F, upward direction e_z and sufficient travel h, the motion occupies:

```text
S = F ⊕ {t e_z : 0 ≤ t ≤ h}
  = union over t in [0,h] of (F + t e_z)
```

The base is cut against a conservative continuous sweep. An independent verifier
reconstructs that sweep from the serialized final figure and base files, using
a smaller numerical envelope than the construction margin. Both final
figure/base swept intersections are numerically zero, below the 0.00001 mm³
acceptance threshold, through 25.055 mm of Wolverine travel and 43.899 mm of
Omega travel. A positive 1.102 mm X-interval separation between the figure bounds
persists during every vertical motion. These checks do not establish printed
friction or force.

All four nominal 4 mm pegs retain 4.3 mm sockets: 0.30 mm diametral clearance.
Local collars add a nominal 2 mm radial wall. They and the probes use 48-sided
polygonal cylinders, so this is a nominal mesh region rather than an exact
circular minimum-wall guarantee. The final declared wall and floor probes find
zero missing material. The earlier exposed Omega socket's lower-annulus material
coverage improves from 82.21% to 100%; that before/after diagnostic is distinct
from the stronger final full-engagement wall check. Printing strength remains
untested.

The purchased case remains a nominal 72.898 × 130.810 × 9.144 mm design reference
from product labels. The protected pocket retains 73.598 mm width and 9.844 mm
thickness, with the existing provisional 0.35 mm allowance on each side. Selected
opening rays on the assembly base, print-oriented base and fused assembly agree
with design within 0.001 mm (the largest recorded discrepancy is
0.000001846 mm). Whole-solid case, pocket, removal, grip and visibility interiors
have zero intersection after the declared 0.00002 mm planar boundary inset used
to distinguish coordinate-rounding contact. These are digital-geometry results,
not manufacturing tolerances or actual case measurements.

Seven raw serialized STLs pass the topology review: assembled and print-oriented
base/Wolverine/Omega, and the fused option. Each is one positive solid with no
zero-area faces and every exactly welded edge incident to two faces. The rebuilt
base/fused option uses explicitly bounded numerical serialization repair; their
triangles can be retriangulated. The separate figures retain the rigid triangle
correspondence above. All 78 source tests passed in the external CAD checkout;
that count is separate from this app's tests.

## Remaining evidence

Use measured case dimensions, fit coupons and a real assembly trial for fit.
Hidden anatomy, existing generative-shape assumptions, support cleanup, material,
shrinkage, paint, joint strength and physical stability remain unverified. The
uniform-solid stability calculation assumes equal density, excludes the case and
cannot establish the behavior of a printed, infilled assembly.

For the flat-part app, reserve independent dimensions from the scale reference
and use the [measured-photo benchmark](../photo-benchmark.md). Keep image agreement,
calibration support, topology, movement clearance and physical tests as separate
results. The [current validation entry](../validation.md#sheet-axis-calibration-and-visible-scale-evidence--november-16-2026)
records this app's source and browser checks.

To regenerate the selected model summary with the original package available:

```sh
python docs/validation/evidence/photo-model-quality-20261116/extract-summary.py \
  /path/to/figure-base-refinement-20261116-v2 > /tmp/model-quality-summary.json
```

Compare that file with the committed JSON. Changed input hashes require a fresh
review; this extract does not package the original private assets or certify a
later modified model.
