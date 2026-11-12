# Constrained fillet sweep preservation

Reviewed November 12, 2026. The reproduction baseline is `2d76aea`; the repair
is candidate `347750e`, verified after normal integration of main `03f71e0` at
`6f7251e`. Main's tracked tree matched the reproduction baseline before that
integration. This is synthetic geometry and export evidence, not a real-photo
or physical-fit qualification.

## Reproduced defect

An independent continuum construction describes a physically sharp 600 × 350
pixel rectangle blurred by a separable Gaussian. At each corner its half-level
contour satisfies

```
Phi(dx / sigma_x) * Phi(dy / sigma_y) = 1/2.
```

The construction uses `statistics.NormalDist` and its inverse, without
production `corner_level` or `tests.synthetic`. With `sigma_x = 3 px`,
`sigma_y = 1.5 px`, a 0.6 px point spacing, and a scalar fitting blur of 1.5 px,
the actual `fit_ring → snap_axes → refit_lines → fit_fillets → correct_blur →
equalise_radii` chain retained four fillets. The scalar blur is deliberately
inadequate for these observations; the fit reports uncertain-radius warnings.

An additional representation defect then changed one quarter-circle into its
270° complement. The resulting polygon was valid and `Profile` accepted it,
so topology validation did not catch the sector change. The sampled boundary's
Hausdorff distance from the true sharp rectangle was about 4.9341 px. The same
failure occurred after rotation, winding reversal and a ring-start change.

`Primitive.data["mid"]` selects which side of an arc's circle is followed.
Fillet refinement changed the circle's centre and radius but left this point
at its original observed world position. `segments` then classified that stale
point relative to the new centre and selected the complementary sector.

## Bounded repair

Before changing the centre, `place_fillets` retains the point's angular
direction about the old centre. It relocates the witness onto the new circle:

```
u = (mid_old - centre_old) / norm(mid_old - centre_old)
centre_new = c0 + radius_new * v
mid_new = centre_new + radius_new * u
```

This moves a representation witness, not a measured pixel or a new fitting
observation. The radius fit, uncertainty calculation and sharp-corner decision
are unchanged. Radius equalisation and blur correction already reuse
`place_fillets`, so subsequent centre moves retain the same angular provenance.
The current pipeline fixes tangent directions before forming these constraints.

The repair does not force constrained arcs to be minor. A genuine tangent-joined
270° arc goes through the fitting chain and remains a major arc, including its
DXF representation and exact CAD extrusion.

## Verification

`tests/test_fillet_sweep.py` contains ten focused cases covering:

- the independently specified blurred-corner reproduction under rotation,
  winding reversal and ring-start changes;
- convex and concave quarter arcs of a rounded L-shaped profile;
- a genuine 270° tangent-joined arc, including CAD and DXF preservation;
- repeated constrained radius changes;
- `Profile` validation, metric CAD extrusion, independent quarter-fillet area
  and volume formulas, STEP re-import, and four 90° DXF arcs.

All ten passed. Substituting only the unchanged `2d76aea` implementation of
`place_fillets` in memory produced six failures and four passing controls.
Twenty selected existing constrained-fillet, sharp-corner and uncertainty tests
also passed.

Full local verification at `6f7251e`, using the matching locked Python
environment, then completed:

- `python -m pytest -q`: **589 passed in 164.51 s**.
- `ruff check backend scripts tests`: passed.
- `git diff --check`: passed.
- Local Markdown targets, heading anchors and cited test names in this record
  and `docs/reference-sheet.md`: passed.

The verified source SHA-256 for `backend/fitting.py` is
`b019cecdd2b5d60ba20b97382eda7ee9c027bfa3449fd27c23edb826c22f3ca7`;
`tests/test_fillet_sweep.py` is
`2f7229b1be1cdb25576cdfdbb5b503e8bd0e773ee74705277d5baa318fa28dda`.
No browser run, CI, publication or physical inspection is claimed here.

## Remaining model limitation

After the representation repair, the same deliberately mismatched anisotropic
case has four quarter arcs and a sampled boundary discrepancy of about
1.2113 px, or 0.2423 mm at 5 px/mm. Its uncertain-radius warnings remain.
The true physical corners are sharp; the scalar Gaussian model still infers
nonzero fillets. This repair establishes consistent sweep assembly, not model
adequacy or a physical radius bound. A future adequacy check needs independent
directional blur evidence and explicit local error assumptions; correlated
profile samples must not be treated as independent trials.
