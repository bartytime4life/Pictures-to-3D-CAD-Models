# Benchmark correspondence and coverage repair

Current integration baseline: `6fbff38f23c044f32649c77dddf7eb284c0b4451`,
freshly verified as `origin/main` on November 11, 2026, after the documentation
review in PR #40. Implementation and focused checks began at source baseline
`5588a523c70e1797341329e54d056c161d0361ad`. The subsequent fast-forward changed
documentation only; both candidate Python files retained their exact hashes. This record concerns the local
benchmark implementation in `scripts/photo_benchmark.py`, not the tracing
algorithm, browser interface, or real-photo accuracy. No dependency changes,
private inputs, server starts or deployments were needed.

## Problem and resulting behavior

The earlier size matcher sorted candidate pairs and greedily accepted unused
pairs. For expected diameters `[6, 7]` and detected diameters `[6.4, 5]`, it
matched 6 to 6.4 and left 7 unmatched. The alternative 6 to 5 and 7 to 6.4
satisfies the same correspondence gates and matches both. For `[100, 101]`
against `[100.4, 99]`, greedy matched both but had 2.4 mm total error instead
of 1.6 mm.

The repaired matcher first maximizes the number of admitted matches, then
minimizes their total absolute size error. It uses unit-capacity minimum-cost
flow with shortest augmenting paths and reduced-cost potentials. Float costs
are represented by integers at their exact common binary denominator; no
epsilon tie penalty or cost rounding changes the secondary objective. Values
are visited in canonical order, with stable graph traversal for equal optima.
This follows the weighted assignment formulation described by
[Kuhn (1955)](https://doi.org/10.1002/nav.3800020109), with cardinality treated
as a separate first objective.

Each scalar still uses `max(1 mm, 0.15 × expected)` as its correspondence
gate. Both sides of a paired outline/opening must satisfy their gates, and the
pair's cost is the sum of the two absolute differences. These gates are
heuristics for size correspondence, not measurement tolerances. Optimal
assignment and deterministic ties do not identify which physical feature was
measured, especially for repeated equal-size holes or radii.

Work is bounded to 128 expected features per kind, 2048 candidates and 131072
pair evaluations per matching call. An oversized request is refused with an
actionable error before pair costs are evaluated; candidates are not silently
discarded. Manifest measurement lists above 128 features per kind are also
refused. Within these bounds the graph work is `O(K E log V)`, where `K` is at
most the smaller feature count. Split a large measurement list into separately
named part entries when needed.

## Coverage and interpretation

Each photo and part now carries `coverage`, and the summary carries the same
four counters:

```text
requested = compared + unmatched + unavailable
```

`unmatched` counts requested scalar dimensions without an admitted match in a
successful trace. `unavailable` counts all requested dimensions in completely
failed traces. An outline or non-circular opening contributes two requested
scalars; each diameter, radius or center distance contributes one. Counts use
the resolved, deduplicated photo list for each manifest part. The legacy
summary fields `samples` and `missing` remain aliases for `compared` and
`unmatched` respectively.

The printed report shows requested and compared dimensions, both failure
classes, and explicitly limits median/p95/worst errors to matched dimensions.
The retained `caliper_uncertainty_mm` field controls only display emphasis.
Generated wording now calls it a comparison threshold rather than a resolved
uncertainty or acceptance rule. The report also distinguishes pooled sample
spread from independent captures and labels scale/edge fitting residuals as
in-sample diagnostics without causal or held-out claims.

## Completed local checks

The existing locked Python environment from `picad-guided` was used against
this worktree's source. Its `uv.lock` and `pyproject.toml` hashes match this
baseline. No package installation was performed. The existing focused test result
remains applicable after the documentation-only fast-forward; Python files did
not change. The current [benchmark guide](../photo-benchmark.md) documents the
new behavior, while the earlier [scientific review](scientific-model-review.md#benchmark-correspondence-and-coverage)
retains its original baseline and findings.

- `python -m pytest -q tests/test_photo_benchmark.py`: **91 passed** in
  4.67 seconds, without warnings.
- An independent oracle enumerates all partial injections for 432 seeded cost
  matrices of sizes 0 through 5 per side, comparing match count and exact total
  cost. It does not reuse a graph solver.
- Specific regressions cover both greedy failures, 144 input permutations
  with an extra candidate, paired dimensions, missing and duplicate features,
  zero costs, deterministic equal optima, tiny real cost differences, gate
  boundaries, invalid costs and work-limit refusal.
- Coverage fixtures use multiple parts, missing features and a failed photo,
  verifying conservation at photo, part and summary levels. The existing
  rendered end-to-end example records 32 compared, 2 unmatched and 17
  unavailable dimensions out of 51 requested opportunities; its geometric
  regression limits still pass.
- A separate dense 128 by 1024 all-zero-cost call exercises the maximum pair
  budget. It matched all 128 expected features in deterministic order in
  3.59 seconds; observed process maximum RSS was 100936 KiB. These are local
  observations, not performance guarantees.
- After the documentation-only fast-forward, the three-photo rendered CLI
  example was generated again. All 48 of 48 requested scalars matched, with
  0 unmatched/unavailable; median/p95/worst absolute errors were
  0.005/0.043/0.104 mm. The guide's sample tables match this output. This is
  synthetic regression evidence, not a real-photo measurement study.
- Ruff checks and `git diff --check` pass for this candidate.
- The two changed documentation files pass six local link/heading-anchor
  checks, JSON-example parsing and Markdown-table width checks.

The change was prepared on an isolated local branch for review. No full-repository
suite, browser review, remote CI, native CAD/slicer import, real-photo study,
measurement uncertainty evaluation or physical manufacturing qualification is
claimed. The same-model synthetic lens inversion and feature-identity limits
are separate scientific issues; this repair does not resolve them.
