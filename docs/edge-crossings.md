# Choosing an edge-profile crossing

The reference-sheet edge search now ranks candidate crossings by their actual
interpolated distance from the supplied point. Previously it ranked the left
sample index of each bracket. That could select a farther crossing and change
the chosen physical edge when the same normal was reversed.

The [verification record](validation/edge-crossings.md) includes a bounded image
with nearest crossings at `-0.01` and `+0.10` pixels. The old search selected
`+0.10` in one direction and `-0.01` in the other. Both directions now select
`-0.01`. The [symmetric sampling grid](material-gradients.md#symmetric-profile-sampling)
is still required; centering the samples alone did not fix the selection rule.

## The decision being made

For one supplied point and normal, let `t` be distance along that normal and
`f(t)` the sampled intensity minus its local target level. On a segment with
opposite-sign endpoint residuals `f₀`, `f₁`, the linear interpolant crosses at

```text
t_cross = (t₀ f₁ - t₁ f₀) / (f₁ - f₀)
```

The search chooses a uniquely nearest **verified crossing**, subject to the
following contact rules:

| Sampled evidence | Treatment |
| --- | --- |
| Strict opposite-sign endpoints | One verified interpolated crossing |
| One zero sample with opposite-sign neighbours, both connected by searched segments | One verified crossing at that sample, counted once |
| Same-sign zero touch, several consecutive zero samples, or a boundary zero without both searched neighbours | Unresolved contact; no edge position is invented |
| Distinct equally nearest crossings or contacts | Unresolved; no first-index choice or averaging |
| A farther contact beyond a uniquely nearer verified crossing | Does not invalidate that nearer crossing |
| Non-finite residual or coordinate at any searched node | Reject this profile; never interpolate across invalid data |

An unresolved contact blocks a farther crossing only when it is nearest or tied.
This prevents jumping from an unresolved local feature to a different, farther
edge. A plateau is an interval of level solutions, not a location: the search
does not substitute its midpoint or an endpoint. Unsearched segments cannot
join zero runs or confirm the direction of a zero sample.

The existing `keep` mask reports unresolved profiles as missing measurements.
Their input points are left unchanged, and independent resolved points remain
available. The median-level and sloped-level selectors must both resolve in
the sloped path; the later ring smoothing remains unchanged.

## Numerical comparison and interpolation

For several candidates, exact `Fraction` arithmetic compares `abs(t_cross)`
from the original finite binary coordinates and residuals. This avoids an
arbitrary tie tolerance or choosing by rounded interpolated values. One
regression has a strict ordering erased by ordinary floating-point division;
the exact comparison retains the nearer root. Equal minima remain unresolved.

Exact ranking concerns the **represented residual samples**. Their image
sampling and fitted levels already contain floating-point approximations.
Upstream perturbations near a tie can change the ordering; this is not a
physical noise enclosure, calibrated confidence or a proof of the true edge.

The returned position uses ordinary floating-point interpolation in both the
single- and multiple-candidate paths. With

```text
A = abs(f₀) / max(abs(f₀), abs(f₁))
B = abs(f₁) / max(abs(f₀), abs(f₁))
t_cross ≈ [B/(A+B)] t₀ + [A/(A+B)] t₁
```

both nonnegative weights are computed directly. Scaling prevents residual-sum
overflow; computing a small weight as `1 - large_weight` could erase a tiny
near-node root. Returning the same stored interpolation also prevents adding
a farther candidate from changing the rounding of an unchanged winner.

[Shewchuk's robust-predicate work](https://www.cs.cmu.edu/~quake/robust.html)
explains how roundoff near a decision boundary can change geometric decisions
and motivates doing extra arithmetic when a predicate is difficult. This
workbench uses a small application-specific rational distance comparison;
it does not implement or claim the performance of the paper's orientation or
incircle algorithms. Common single-candidate profiles use no rational ranking.

## Scope and remaining limits

The rule still prefers a crossing near the supplied tracing seed. That seed
may be wrong, and under-sampled profiles may hide crossings between samples.
No local selector proves which visible feature belongs to the intended part.
Spatial material gradients, wall structure, tone response, optics, pose and
physical measurements remain separate [model-adequacy work](material-gradients.md).
Ring-smoothed final points are not claimed to lie at each individual raw-profile
crossing. No new UI, API field or accuracy status is introduced.

The [repeatable material-gradient command](material-gradients.md#repeat-the-study)
remains available to check representative single-edge processing stages. Its
prior 576 scenes are reused as preservation regressions here, not relabeled
as a fresh evaluation population. The verification guide retains the new
adversarial profiles and the complete preservation comparison.
