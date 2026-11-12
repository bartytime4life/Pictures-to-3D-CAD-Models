# Scientific model and documentation review — November 11, 2026

Reviewed baseline: `main` at
`5588a523c70e1797341329e54d056c161d0361ad`, after PR #39. This change updates
documentation only. The findings below remain unresolved at that revision.
Existing source worktrees, previews and private inputs were preserved.

## Evidence classes

| Finding | Evidence obtained | What it does not establish |
| --- | --- | --- |
| Whole-circle extrapolation | Actual fitter and profile resampling, with independently specified closed geometry | A photo that segmentation turns into that contour, or a physical failure rate |
| Directional blur | Modified synthetic renderer followed by the unchanged production `trace_image` pipeline | Real-phone accuracy, a complete PSF model or a verified correction |
| Greedy correspondence | Actual benchmark matcher with a hand-checkable assignment | Physical identity of equal-size features |
| Incomplete dimension denominators | Actual benchmark aggregation with explicit successful/failed photo fixtures | A measured-photo benchmark result |
| Zero-blur fallback | Existing targeted regression passes | Full-suite, browser or physical low-contrast performance |

The earlier [documentation refresh](documentation-refresh.md) remains a dated
record. The [current validation overview](../validation.md) separates it from
these new checks and from historical software suites.

## Whole-circle extrapolation

`fit_ring` can accept a whole circle from a thin closed circular segment even
though the fitted center lies outside the source contour. Its radius-relative
residual allowance and circle-versus-pieces comparison do not require full
angular support. `undetermined_radii` skips this circle, so it gives no radius
warning in this case.

Run from the repository root in the workbench Python environment:

```python
import math
import numpy as np
from backend import fitting

ppm, sigma = 4.0, 2.0
a = np.linspace(-math.radians(10), math.radians(10), 100)
arc = 100 * np.column_stack([np.cos(a), np.sin(a)])
points = np.vstack([arc, np.linspace(arc[-1], arc[0], 100)[1:-1]])
tol = max(0.03, 0.15 * sigma / ppm) * ppm
min_line = min(max(0.025 * np.ptp(points, axis=0).max() / ppm, 1), 3) * ppm
prims = fitting.fit_ring(points, tol, min_line)
print(np.ptp(points, axis=0) / ppm)
print([p.kind for p in prims], prims[0].data["r"] / ppm)
print(fitting.undetermined_radii([prims], sigma, 1 / ppm))
```

Observed: source bounds **0.37977 × 8.68241 mm**; one fitted circle with radius
**49.61052 mm**, diameter **99.22104 mm**; RMS residual **0.13866 mm**; radius
notes `[]`. The source has 100 arc points and 98 points closing its chord.
Resampling that accepted circle gives approximately 99.21 mm bounds; the small
sampling difference does not explain the extrapolation.

This is a fitting-stage counterexample, not a reproduced photo-upload case.
The reference pipeline subsequently replaces its original contour with fitted
samples. Validating the resulting fitted profile or solid cannot recover the
discarded source agreement.

**Proposed work:** require whole-circle support, for example a center enclosed
by the original contour, before accepting a circle; retain the existing
piece/polyline path otherwise. Test circular segments, full circles, opposite
windings, rigid transforms, noise and retained dimensions/area. A separate
bidirectional boundary-distance check would test extrapolation directly.
No such guard is added here. Improving a circle optimizer's numerical
convergence alone would not supply the missing geometric support.

## Directional blur

The current estimator reports one median Gaussian-equivalent spread. Gaussian
curvature, wall and corner calculations use this scalar assumption. It cannot
describe a blur that differs by direction or position. A projective warp can
also turn isotropic camera blur into locally anisotropic blur.

The experiment replaced only the renderer's final sensor blur, in memory:

```python
from pathlib import Path
import types
from tests import synthetic as S
from backend.tracing import trace_image

source = Path(S.__file__).read_text()
old = "image = cv2.GaussianBlur(image, (0, 0), blur)"
assert source.count(old) == 1
alternate = types.ModuleType("anisotropic_render")
exec(compile(source.replace(old,
    "image = cv2.GaussianBlur(image, (0, 0), 1.0, sigmaY=3.0)"),
    S.__file__, "exec"), alternate.__dict__)
for render, tilt in [(S.render, (0, 0, 4)),
                     (alternate.render, (0, 0, 4)),
                     (alternate.render, (22, -9, 4))]:
    photo, _ = render(tilt=tilt, k1=0, thickness=0, shadow=0,
                      gradient=0, noise=0, quality=100, seed=7)
    profile = trace_image(photo, reference="a4", snap=True)["profile"]
    print(S.feature_errors(profile))
```

Production source and stored fixture images are unchanged. Other renderer
stages, including its pre-existing plane blur and surface texture, remain.
The sensor-noise setting is zero; JPEG quality is 100. Each result contains
the expected fitted circles and slot.

| Synthetic case | Maximum Ø6 error (mm) | Slot-size error (mm) | Outer-size error (mm) |
| --- | ---: | ---: | ---: |
| Overhead, final sensor σx = σy = 1 px | 0.00257 | 0.00245 | 0.00465 |
| Overhead, final sensor σx = 1, σy = 3 px | 0.06820 | 0.08911 | 0.03837 |
| 22° tilt, final sensor σx = 1, σy = 3 px | 0.08061 | 0.10688 | 0.06395 |

Some values exceed the existing 0.03/0.06/0.05 mm regression guards for these
features. Those guards were not accuracy guarantees, and the original
isotropic-render tables are not replaced by this exploratory experiment.
There is currently no dedicated anisotropy warning.

**Proposed work:** first test directional edge-spread diagnostics and whether
the available edge orientations identify a covariance. Account for the local
homography and validate any proposed correction with independent Gaussian
integration, covariance-orientation sweeps, subpixel phases and end-to-end
dimensions. A normal-direction blur width alone is not a complete curvature
model. Spatial variation, sharpening, non-Gaussian blur and real captures need
separate evaluation. No diagnostic or correction is implemented here.

## Benchmark correspondence and coverage

The [benchmark guide](../photo-benchmark.md#coverage-and-matching-limits) includes
the runnable greedy-assignment counterexample. Expected diameters `[6, 7]`
and candidates `[6.4, 5]` return `[0, None]`, although 6 → 5 and 7 → 6.4 are
both admissible. The sorted-pair greedy algorithm does not maximize match count
or minimize total error over complete assignments.

An aggregation fixture used two requested diameters in each of two photos,
one successful and one explicitly failed. The successful photo used the
matcher above. Actual `run`/`rows_of` output was `photos: 2, traced: 1,
samples: 1, missing: 1`; median, p95 and worst were each 0.4 mm. Four
dimensions were requested, but the two unavailable in the failed photo do not
enter the dimension counts. This used stubbed tracing to isolate aggregation;
no real photograph was read.

**Proposed work:** maximize admitted match count, then minimize total admitted
cost, with deterministic ties and explicit work limits. Test against an
independent exhaustive partial-assignment oracle on small cases, including
permutations, duplicate features, missing/extra candidates and gate boundaries.
Report requested, compared, unmatched and unavailable dimensions explicitly,
and verify their conservation. Preserve the correspondence gates as heuristics;
neither optimal size assignment nor a deterministic tie proves physical identity.

The guide also corrects interpretation of pooled spread, the caliper display
threshold and in-sample scale/edge residuals. The runner's generated wording
and algorithms are unchanged by this documentation update.

## Research basis and next experiments

| Primary source | Review and application |
| --- | --- |
| [Al-Sharadqah and Chernov, circle-fit error analysis (2009)](https://arxiv.org/abs/0907.0421) | Abstract and method overview: geometric/algebraic fits have statistical assumptions. This is background, not proof of this repository's extrapolation bug or a decision to adopt a different estimator. |
| [Wirgin, The inverse crime (2004)](https://arxiv.org/abs/math-ph/0401050) | Author abstract defines the shared-model problem. Source inspection confirms the renderer calls production `undistort_radius`; independent forward rendering and a separate inverse remain needed. |
| [Lin, Gu, Yamazaki and Shum, radiometric calibration (2004)](https://www.gujinwei.org/research/radiocalib/index.html), [author paper](https://www.gujinwei.org/pdfs/calib_cvpr04.pdf) | Author project requirements and model: RGB-edge distributions and a response prior; enough intensity coverage is required. Automatic calibration of an arbitrary two-color part scene is not established. |
| [NIST, one-variable-at-a-time experiments](https://www.itl.nist.gov/div898/handbook/pri/section2/pri212.htm) | Crossed factors are needed to expose interactions. The capture-study proposal in the benchmark guide is future work. |
| [NIST TN 1297 terminology](https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-appendix-d1-terminology) | Accuracy, uncertainty and repeatability are distinct. A numeric display threshold or pooled sample SD is not a propagated uncertainty statement. |

Prioritize source-support and benchmark-integrity fixes, then independent lens
oracles and blur-model diagnostics. A reserved set of real captures and
functional dimensions is still required. If a reserved check guides a model
change, retain that result and obtain a fresh check for the revised model.

## Documentation coverage and completed checks

All tracked Markdown documents are included in the inventory, local-link,
heading-anchor and Markdown-table review. Current guides changed where this
review affected their claims: root/index navigation, capture, tracing,
troubleshooting, engineering, benchmark, research, roadmap, contributing,
change log and validation. Historical reports, the source catalog and generated
library releases retain their original dates and observations.

The existing `test_a_zero_blur_estimate_keeps_the_median_level_search` passed
at the baseline: **1 passed, 63 deselected**. The fitting, matching, aggregation
and three directional-blur reproductions above ran against that source using
the existing locked workbench environment. No full software/browser suite,
live model inference, installed CAD/slicer review, physical measurements or
print qualification was performed for this documentation change.

Completed documentation checks:

- **48 Markdown documents** parse with the locked library `marked` version;
  **70 tables** have consistent column counts.
- **410 local links**, including **30 fragment links**, resolve. This checks
  local navigation; it is not a refresh of the external source catalog.
- Library regeneration passed, followed by the existing documentation-accuracy
  suite: **19 tests passed**. All tracked library outputs, including its HTML,
  PDF, figures and generated catalog, are byte-identical to the baseline.
- `git diff --check` passed. The change contains only Markdown; runtime source,
  tests, lockfiles and release records are unchanged.

The library build and documentation tests reused the prior documentation
worktree's Python environment; the locked Node dependencies were installed in
this isolated worktree. Local receipts and reproduction JSON remain in its
ignored `.local/verification/` directory. Hosted CI, merging, deployment and
physical acceptance are separate from these completed local checks.
