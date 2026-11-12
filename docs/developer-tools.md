# Numerical tools and repeatable studies

Run these commands from the repository root after [workbench setup](development.md).
They use the root `.venv` and do not require a running CAD server unless stated.
Record `git rev-parse HEAD` and `git status --short --branch` with each run.
The [status page](project-status.md) identifies the documented implementation;
an experiment in another worktree is a different implementation.

## Choose a tool

| Question | Tool | Interpretation |
| --- | --- | --- |
| Which radii can explain explicitly bounded observations? | `scripts/corner_feasibility.py` | Conditional sets under supplied geometry, optics and observation bounds; no photo ingestion or automatic correction |
| Does the fitting chain retain synthetic rounded corners? | `make corner-sweep` | Matched-model regression, including unresolved numerical searches; no physical radius bound |
| How do illumination and sampling affect local edge measurements? | `make material-gradient-study OUTPUT=NEW_DIRECTORY` | Complete development census through actual profile functions; no complete-camera qualification |
| Can bounded lighting fit competing wall/silhouette interpretations? | `make wall-gradient-study OUTPUT=NEW_DIRECTORY` | Bounded source fits and constructed ambiguity witnesses; no production wall-model replacement |
| Does a wall-fit change improve identical initial traces? | `make wall-localization-study OUTPUT=NEW_DIRECTORY` | Paired development scenes with a pinned baseline; retained unknowns and model failures, not camera qualification |
| Does oversampling create misleading precision? | `make profile-noise-study OUTPUT=NEW_JSON` | Known correlated-noise and local-information controls, with support/rank counterexamples; no camera calibration |
| Does the forward model include the known smoothing filter? | `make postblur-operator-study OUTPUT=NEW_JSON` | Declared finite-filter plus Keys composition on fixed fields; rounding and earlier-chain limits retained |
| Does the known full digital chain match the actual sampler? | `make warp-observation-study OUTPUT=NEW_JSON` | Supplied raw-to-rectified warp, smoothing and profile sampling; stage rounding retained separately |
| Can a declared raw optical mean explain available prewarp samples? | `make raw-source-fit-study OUTPUT=NEW_JSON` | Bounded source-projection offset/brightness fitting with known geometry, PSF and noise; retains weak-mode, source-mismatch and ambiguity controls |
| Can one common monotone response satisfy externally supplied calibration? | `scripts/response_calibration.py INPUT.json --output NEW_JSON` | Exact conditional consistency and tight pointwise bands; no automatic camera calibration or inverse |
| How do my reference-sheet photos compare with reserved measurements? | `make photo-benchmark PHOTOS=FOLDER` | Measured-photo comparison with coverage and failed traces retained; supplied comparison threshold is not an uncertainty budget |
| Does a selected server trace, build and export the sample? | `make smoke` | API exercise against an already running server, including cleanup; not browser or physical acceptance |
| Can an installed CAD application import the synthetic exports? | `make freecad` | Native FreeCAD check requiring `FREECADCMD`; not slicer or print qualification |
| Which local slicer executable can be found? | `make slicers` | Discovery only; no launch, version verification or import acceptance |
| How do installed local assistant models answer the fixed cases? | `scripts/benchmark_ollama.py` | Model answers and latency for human review; separate from integration fixtures |

## Conditional corner-radius inputs

```bash
.venv/bin/python scripts/corner_feasibility.py --demo --output .local/corner-demo-new.json
.venv/bin/python scripts/corner_feasibility.py INPUT.json --output .local/corner-result-new.json
```

Create the parent output directory first if needed. The CLI prints JSON and
optionally saves the same report; it refuses an existing output file. Geometry,
light levels and bounds use decimal strings as specified in each version's guide.

| Input version | Observation model | Guide |
| --- | --- | --- |
| 1 | Point observations with fixed independent axis-aligned Gaussian blur | [Fixed model and demo](corner-feasibility.md) |
| 2 | Point observations with one bounded blur pair shared by every point | [Joint blur domains](corner-feasibility.md#joint-blur-domains-version-2) |
| 3 | Known normalized uniform product-aperture means | [Pixel apertures](pixel-apertures.md) |
| 4 | Declared fixed signed combinations of apertures or point samples | [Signed stencils](signed-stencils.md) |

Accepted and unresolved parameter boxes remain distinct. Work or numerical
exhaustion retains unknown regions. The CLI does not supply an observation-error
budget, identify the camera response or calibrate production Keys resampling.
Reports retain the parsed submitted input and bind the original input bytes by
SHA-256, along with implementation hashes and Git state. Whitespace changes can
therefore change the input hash even when the parsed model is the same.
Read each version's assumptions before interpreting its radius projection.

## Common-response calibration constraints

```bash
.venv/bin/python scripts/response_calibration.py INPUT.json --output .local/response-result-new.json
make response-calibration-study OUTPUT=.local/response-study-new.json
.venv/bin/python studies/verification/response-calibration-oracle-v1.py --output .local/response-oracle-new.json
```

The [response guide](response-calibration.md) defines exact decimal-string inputs,
closed output bands, optional common slope bounds, domain-only query envelopes
and one shared piecewise-linear witness. All commands require fresh output files.
The CLI retains incompatible constraints as exact proofs; invalid/resource
requests are refusals, not mathematical incompatibility. Its reports bind the
submitted bytes, core/CLI sources and Git state.

The separate fixed experiment retains every finite edge-offset/response candidate,
including wrong calibration and unidentifiable alternatives. It does not provide
a continuous offset enclosure, a camera correction or a post-inversion noise model.
Use [the complete controls](validation/response-calibration.md) before interpreting
compatibility. Pointwise query bands cannot be combined as independent responses.
The complete finite-study witnesses and indexed contradictions can be replayed
without calling the production calibrator:

```bash
.venv/bin/python studies/verification/response-calibration-study-audit-v1.py --run studies/results/response-calibration-v1.json --output .local/response-study-audit-new.json
```

The auditor requires a fresh `.json` file, checks every declared candidate and
retains failed checks. It does not rerun the image pipeline.

## Local-profile and wall studies

Choose fresh output paths and preserve earlier reports:

```bash
make material-gradient-study OUTPUT=.local/material-gradients-new
make wall-gradient-study OUTPUT=.local/wall-gradients-new
make wall-localization-study OUTPUT=.local/wall-localization-new
```

These commands require `OUTPUT` and refuse an existing directory. They retain the
executed plan, full CSVs, summaries, runtime versions and source hashes. The
[material-gradient guide](material-gradients.md) distinguishes measurement
rejections, execution failures, production treatment and research ablation.
The [wall guide](wall-gradients.md) distinguishes original observations from
pair-specific constructed midpoints and supplied true wall tone from estimation.
None of these commands identifies a physical error bound from a small residual.

The [wall-localization guide](wall-localization.md#repeat) supplies its complete
paired-CSV audit and the two fixed-population Keys-forward prototype commands.
The comparator's pinned baseline must exist in the local Git object database.
The prototypes change no tracing behavior and refuse existing JSON outputs.
The wall-gradient result schema now distinguishes resolved, unresolved and
execution-failure rows; its auditor also reads the archived version-1 results.

The [fixed-observation and covariance guide](profile-observations.md) supplies
two additional commands. Their `OUTPUT` is a fresh JSON file, rather than a
study directory. They record all density/repetition controls and known-filter
comparisons, including global aliases and omitted-mode counterexamples. Noise,
optical spread and source geometry are supplied experimental conditions. Neither
command changes production tracing or estimates physical confidence.

The [warp-chain guide](warp-observations.md) adds `make warp-observation-study`
with a fresh JSON file and a separately pinned raw-optical-edge runner. The first
keeps all 324 readouts from six reused source arrays; the second distinguishes
affine Gaussian covariance, projective variation and radial curved-edge response.
Known digital weights do not establish an optical source model or calibrate
geometry estimated from the same image.

The [raw-source fitting guide](raw-source-fit.md) adds `make raw-source-fit-study`
with a fresh JSON destination. Both source observations and model use the same
fixed retained source projection. The experiment keeps all matched fields,
wrong-PSF/nonlinear/quantization controls, common-noise draws, global aliases and
unresolved searches. Raw residuals outside the selected source row space remain
visible. This is not all-raw-pixel fitting or a calibrated photo likelihood.
Use the [developer API reference](raw-source-fit.md#developer-api) for pixel order,
units, finite-search budgets and standardized residual fields. To repeat its
independent geometry and bounded-brightness checks without starting a server:

```bash
.venv/bin/python studies/verification/raw-source-fit-oracle-v1.py --output .local/raw-source-oracle-new.json
```

That destination must also be new. A brightness-design rank of two does not
establish a uniquely identified edge; preserve the search flags and candidates.

Audit the wall study's complete row keys and summaries independently of its
summary-writing code:

```bash
.venv/bin/python studies/verification/wall-gradient-audit.py --run .local/wall-gradients-new --output .local/wall-audit-new.json
.venv/bin/python studies/verification/wall-light-identifiability-oracle-v1.py --output .local/wall-source-new.json
.venv/bin/python studies/verification/wall-light-node-review-v1.py --output .local/wall-nodes-new.json
```

The first checks CSV accounting, fitted-node feasibility and summaries; it does
not execute the image pipeline again. The latter two check bounded-source
quadrature and constrained-fit primitives. They refuse existing result files.
The [published wall record](validation/wall-gradients.md) binds the archived
results to exact sources; a run on changed sources needs its own record.

The independent nearest-contact oracle has no argument parser; `--help` also
executes its checks. It writes JSON beside its own script and refuses an existing
sidecar, as well as printing the report. To preserve earlier runs and keep
generated evidence out of the source directory, copy it into a fresh ignored
directory exactly two levels below the repository root:

```bash
mkdir -p .local
mkdir .local/nearest-contact-new
cp studies/verification/nearest-crossing-oracle.py .local/nearest-contact-new/nearest-crossing-oracle.py
.venv/bin/python .local/nearest-contact-new/nearest-crossing-oracle.py
```

The result is `.local/nearest-contact-new/nearest-crossing-oracle.json`. Use a
different new directory for another run. Keeping that directory depth preserves
the oracle's repository-root lookup; redirecting stdout alone does not relocate
its sidecar. The oracle checks finite-data crossing selection, not physical feature identity.
Its [verification record](validation/edge-crossings.md) explains the population.

## Figures

Matplotlib is optional and is not installed by the workbench setup. The published
wall figure used Matplotlib 3.11.2 in its recorded environment. If plotting is
needed, provide it in a separate suitable development environment and preserve
the production lockfiles. Activate that plotting environment before the command
below; `python` must select its interpreter, with Matplotlib and NumPy available.

```bash
python studies/verification/plot-wall-gradients.py --run .local/wall-gradients-new --output .local/wall-figure-new.svg --preview .local/wall-figure-new.png
```

The plotter refuses existing output files. Inspect labels, units, legends and
clipping; a figure is a view of the retained data, not additional validation.

## Measured photos and native imports

Follow the [photo-benchmark guide](photo-benchmark.md) to prepare `benchmark.json`,
reference-sheet photos and reserved measurements. Its `--example FOLDER` creates
synthetic demonstration inputs, not measured-camera evidence. Reports include
filenames and trace notes; review these before sharing. Original photos remain
separate and are not automatically published.

Follow [slicer setup](slicers.md) before enabling explicit local launches.
`make slicers` and `make freecad` have different prerequisites and do not qualify
Bambu Studio or PrusaSlicer imports, printer profiles, layer previews or prints.

The companion library uses its own environment. From `reference-library/`,
`python3 -m cadkit openscad doctor` checks native availability and
`python3 -m cadkit openscad build --model plate --output-dir output/plate-new --preview`
builds synthetic parameter-driven geometry. See [its native workflow](../reference-library/OPENSCAD.md).

## Local assistant comparisons

After explicitly installing and starting Ollama and selecting installed models:

```bash
.venv/bin/python scripts/benchmark_ollama.py MODEL_TAG --output .local/ollama-comparison-new.json
```

This performs actual local inference and writes a JSON report plus a Markdown
summary, replacing either destination if it already exists, even for a saved
service-unavailable preflight. It does not install models. Use fresh output paths and inspect the
answers with the [evaluation rubric](ollama-models.md); integration tests and a
completed timing run do not establish a quality winner. The ordinary CAD flow
works without Ollama.
