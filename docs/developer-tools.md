# Developer commands in this checkout

[Source scope](project-status.md) · [Setup](development.md) · [Architecture/API](architecture.md)

Run these from the repository root after setup. `make` prints the supported
targets. These are the tools present in the reviewed main-based source; research
scripts from a separate branch are not implied by this list.

For the source-cell APIs included in this main-based source, start with the
[small acquisition example](finite-acquisition-mean.md#small-executable-example)
and [input/result/resource contract](finite-acquisition-mean.md#refusals-provenance-and-work).
This is an explicit Python call, not a command that traces a photograph or
fits geometry. For saved-only review, the 182-artifact workflow in the table
verifies the independent mean without running a model.

For five unrounded area columns and signed propagation, read the
[cell-sensitivity contract](finite-cell-sensitivity.md) and its
[14-artifact saved-only workflow](../studies/fixtures/finite-cell-sensitivity-v1/README.md).
There is no acquisition-aware five-parameter fit command or HTTP mode in this
main checkout. The [separately frozen recovery candidate](finite-acquisition-recovery.md)
at `e6e2c2` includes local fitting and smooth-proposal/literal-objective study
runners, but their modules and entry points are absent here. Its 459 passing
focused tests are separate from both failed numerical protocols: 4/12 matched
targets in the first and 9/12 in the continuation, each with all 24 matched/adverse
rows retained and exit 1. The first saved-data audit has 14 unverifiable pre-cast
order-delta comparisons; do not treat it as an independent success. Follow the
candidate's source-specific guide rather than borrowing an unavailable command
or treating a documentation check as a new fit, audit pass or app regression.

The later [coupled search](finite-acquisition-coupled.md) reaches **11/12**
matched target passes; the [source-event continuation](finite-acquisition-events.md)
stays at **11/12**. Both complete 24-case protocols still exit 1. Their first
focused suites pass 548 tests/nine subtests and 653 tests/21 subtests, respectively.
The [completed results](validation/finite-acquisition-continuations.md) and
[saved-only audits](finite-acquisition-saved-audit.md) retain the remaining PNG
miss, first failures and 28 historical precision unknowns. Candidate code and
complete local ZIPs remain separate from this main runtime and workbench UI.

The [acquisition evidence workflow](../studies/fixtures/finite-acquisition-operator-v1/README.md)
verifies 123 stored artifacts, extracts the complete saved run and checks the
87-file recorded source snapshot as data. Use that workflow on current main:
the study's older source is not the current shadow-lighting pipeline. Its
artifact auditor deliberately exits 1 after passing 1,294 artifact checks,
because the archived raw report has 320 scalar-serialization failures. The
separate normalizer retains those failures and performs no scientific calls.

The [residual-information diagnostic](finite-residual-information.md) has a
complete retained failed replay and separate saved-only audit. Its [portable
instructions](../studies/fixtures/finite-residual-information-v1/README.md) distinguish
contracts, actual forward/derivative/trial calls and post-hoc saved arithmetic;
none runs a new inverse optimizer or changes automatic tracing.

For lightweight checks of the finite-material documentation, use the
[supplied-model example](finite-shape-inverse.md#coordinate-example),
[archived preparation example](finite-shape-inverse.md#replay-preparation-without-fitting)
and the listed runners' `--help` modes. The no-fit contract runner additionally
evaluates preparation and forward probabilities; it runs no inverse optimizer.
Full replay and continuation commands below perform real fitting and are
separate, slower scientific checks. Follow each receipt's source hashes when
reproducing an archived result; a later backend can invalidate that binding.

The photo-v2 first-fit-failure continuation specifically requires its recorded
source closure for equality with the old canonical report. Current main's
`backend/fitting.py` and `backend/sheet.py` differ from those recorded hashes.
The harness is designed to run nine later optimizers before checking source
equality; that comparison cannot pass against the old canonical report on
current main. Use the [saved continuation receipts](../studies/fixtures/finite-photo-intensity-v2/README.md)
to review that historical result. A new replay on current source is a new
experiment and needs its own source binding and comparison criteria.

| Tool | Entry point | Execution and output |
| --- | --- | --- |
| Unrounded cell sensitivities and fixed linear acquisition | `backend.finite_aperture_sensitivity.segment_cell_sensitivity`, `backend.finite_acquisition_linear.acquisition_linear` | Five geometry columns, signed fields and computed constant response; explicit unknowns and resource contracts; [method](finite-cell-sensitivity.md) |
| Cell-sensitivity saved-data audit | `python3 studies/verification/finite-cell-sensitivity-artifact-audit-v1.py --help` | Saved JSON/source-ZIP arithmetic only; [portable workflow](../studies/fixtures/finite-cell-sensitivity-v1/README.md); no model, derivative or optimizer evaluation |
| Source-cell acquisition mean | `backend.finite_aperture.segment_cell_coverage`, `backend.finite_acquisition.acquisition_mean` | Experimental Python operators with explicit grid/kernels/map/levels, immutable stages and bounded work; no trace, optimizer or HTTP integration; [contract and limits](finite-acquisition-mean.md) |
| Source-cell saved-data artifact audit | `.venv/bin/python studies/verification/finite-acquisition-mean-artifact-audit-v1.py --help` | NumPy archive reading and strict JSON/hash arithmetic only; uses the recorded source ZIP as data; [complete 182-artifact workflow](../studies/fixtures/finite-acquisition-mean-v1/README.md#verify-saved-data-without-a-model-call) |
| Acquisition saved-data artifact audit | `.venv/bin/python studies/verification/finite-acquisition-artifact-audit-v1.py --help` | Standard-library NPY parsing and Pillow PNG decoding; no backend, generator or model imports; use the extracted recorded-source root and saved run in the [complete workflow](../studies/fixtures/finite-acquisition-operator-v1/README.md#verify-and-reconstruct-saved-data) |
| Acquisition native-scalar derivation | `python3 studies/verification/finite-acquisition-normalize-v1.py --help` | Standard-library-only, exact raw-report hash and whitelisted 320 fields; fresh output; no new scientific qualification |
| Workbench setup/start/development | `make setup-app`, `make start`, `make dev` | Setup installs locked dependencies and builds; start/dev launch services |
| Component verification | `make test-app`, `make lint` | Python, frontend build and browser workflow; lint checks Python and frontend/browser-source formatting |
| Both components | `make setup`, `make build`, `make test` | Also operates on the separately declared reference-library environment and generated outputs |
| Running-service smoke check | `make smoke` | Traces the sample, builds CAD, downloads STEP and deletes its own model; needs a server and has no argparse help mode |
| Slicer discovery | `.venv/bin/python scripts/slicer_status.py --json` | Reports fixed-program discovery without starting a slicer; does not verify installed versions |
| Measured-photo benchmark | `.venv/bin/python scripts/photo_benchmark.py --help` | `FOLDER` reads the photo/measurement manifest; `--example FOLDER` writes synthetic examples; `--json FILE` and `--markdown FILE` write reports |
| Independent covariance-corner study | `.venv/bin/python studies/verification/corner-anisotropy-v1.py --model both --output NEW.json` | All 16 fixed cases retained; requires a fresh JSON file in an existing directory; [evidence and limits](validation/anisotropic-corners.md) |
| Independent blur-frame study | `.venv/bin/python studies/verification/curve-blur-frames-v1.py --output NEW.json` | All 46 fixed rows retained, including mixed/no-half-level controls; fresh JSON destination in an existing directory; [evidence and limits](validation/curve-blur-frames.md) |
| Canonical join oracle | `.venv/bin/python studies/verification/canonical-arcs-oracle-v1.py --output NEW.json` | All 132 fixed geometry/search/finite-Gaussian rows retained; refuses existing destinations and creates missing parent directories; [scope](validation/directional-free-arcs.md) |
| Actual arc/chord fit comparison | `.venv/bin/python studies/verification/canonical-arcs-fit-v1.py --output NEW.json` | Six fixed cases; optional `--source-root PATH` selects an explicit local backend; deliberately mismatched nonzero blur checks representation, not optical recovery; creates missing parents |
| Directional free-arc comparison | `.venv/bin/python studies/verification/directional-free-arcs-v1.py --output NEW.json` | Sixteen fixed conditional cases; supplied truth-derived local domains, fixed covariance/half-level and study-only finite-disk model; fresh JSON destination in an existing directory |
| Finite-material centre/radius inverse | `.venv/bin/python studies/verification/finite-free-centre-v1.py --output NEW.json` | Twenty-four fixed supplied-optics cases, observation-derived domains and independent positive-area means; all outcomes retained; fresh JSON destination in an existing directory; [model](finite-shape-inverse.md) |
| Supplemental same-pixel aperture audit | `.venv/bin/python studies/verification/finite-free-centre-aperture-audit-v1.py --output NEW.json` | Rechecks the saved 56 aperture observations at 8×8 and 16×16 order without refitting; fresh JSON destination in an existing directory; preserves the original failed 4×4/8×8 comparison |
| Image-moment proposal replay | `.venv/bin/python studies/verification/finite-moment-photo-v1.py --output NEW.json` | Archived synthetic measurement fields, all 76 numerical/ineligible outcomes and background/crop sensitivity; fresh JSON destination; [limits](validation/finite-moment-photo.md) |
| Paired measured-ring intensity replay | `.venv/bin/python studies/verification/finite-photo-intensity-v2.py --output NEW.json` | Twelve fixed case/lane records from preserved measurement fields; one shared crop/seed/40+16 samples per case, supplied covariance hypotheses and unchanged targets; fresh JSON destination in an existing directory; [scope and results](validation/finite-photo-intensity-v2.md) |
| Measured-ring no-fit contracts | `.venv/bin/python studies/verification/finite-photo-intensity-v2-contracts-v1.py --output NEW.json` | Actual preparation/forward controls and explicitly labeled parser/routing sentinels; no inverse optimizer; fresh JSON destination in an existing directory |
| Affine numerical controls without inverse fits | `.venv/bin/python studies/verification/finite-affine-batch-v1.py --no-timing --output NEW.json` | Sixteen operator, six resource and six derivative controls; no inverse optimizer or benchmark timing; [protocol and archive](validation/finite-affine-batch.md) |
| Affine complete fit and performance comparison | `.venv/bin/python studies/verification/finite-affine-batch-v1.py --complete --quiet-interval --output NEW.json` | All 36 archived rows, 32 accuracy-fit entries and 24 whole-fit warm/timed entries; also retains all 192 kernel samples; requires the declared quiet interval for timing |
| Affine complete accuracy replay without timing | `.venv/bin/python studies/verification/finite-affine-batch-v1.py --complete --no-timing --output NEW.json` | Same archived accuracy population; no benchmark repeats or timing qualification |
| Affine actual first-fit failure continuation | `.venv/bin/python studies/verification/finite-affine-batch-v1.py --complete --no-timing --inject-first-fit-failure --canonical CANONICAL.json --output NEW.json --audit NEW_AUDIT.json` | Injects the first accuracy-fit entry failure, runs 31 later real accuracy fits and compares all 35 later records; decompress the full canonical archive first; [instructions](../studies/fixtures/finite-affine-batch-v1/README.md) |
| Saved affine report integrity audit | `python3 studies/verification/finite-affine-report-audit-v1.py --help` | Standard-library-only arithmetic, timing-accounting and source checks; no fitter imports or reruns; [full invocation](../studies/fixtures/finite-affine-batch-v1/README.md#verify-the-saved-report-without-fitting) |
| Residual-information safe contracts | `.venv/bin/python studies/verification/finite-residual-information-v1.py --contracts-only --output NEW.json` | Six invented algebra and ten parser/status controls; NumPy, no backend import or archived model calls |
| Residual-information actual diagnostic | `.venv/bin/python studies/verification/finite-residual-information-v1.py --output NEW.json` | The 12-row source-bound replay performs means, derivatives and eligible single steps without an inverse optimizer; [original exit 1 and retained unknowns](validation/finite-residual-information.md) |
| Residual saved-data audit | `python3 studies/verification/finite-residual-report-audit-v1.py --help` | Standard-library Jacobi SVD, QR and arithmetic on the complete decoded report; [exact hash-bound invocation](../studies/fixtures/finite-residual-information-v1/README.md#verify-and-audit-without-model-calls) |
| Post-hoc saved rotation identity | `python3 studies/verification/finite-normal-rotation-saved-v1.py --help` | Combines saved arrays only; no new forward evaluation, independent optical validation or replacement of unknown normal columns |
| Actual first-fit failure continuation | `.venv/bin/python studies/verification/finite-photo-intensity-v2-continuation-v1.py --canonical studies/results/finite-photo-intensity-v2.json --output NEW.json --audit NEW_AUDIT.json` | Injects the first fit-entry failure and runs nine later optimizers; the archived equality contract requires its original source closure (see warning above); writes full result and separate comparison audit to fresh paths; [portable evidence and scopes](../studies/fixtures/finite-photo-intensity-v2/README.md) |
| Corner sweep | `.venv/bin/python scripts/corner_sweep.py --help` | Synthetic fitting cases, optional `--quick`, `--backend PATH` and `--json FILE`; not a real-camera test |
| Native FreeCAD import check | `make freecad` | Requires `FREECADCMD`; builds synthetic fixtures and launches FreeCAD. `freecad_check.py` and its `freecad_import.py` helper have no argparse help mode |
| Printer-data import | `.venv/bin/python scripts/import_printers.py --help` | Reads the supplied pinned-source checkout and writes catalog JSON; [procedure](printer-catalog.md) |
| Local-model comparison | `.venv/bin/python scripts/benchmark_ollama.py --help` | Actual execution calls already installed Ollama models and writes JSON plus a Markdown summary; [limits](ollama-models.md) |
| Optional runtime helper | `./scripts/ollama.sh` | Prints usage. Its explicit actions are `install`, `serve`, `pull`, `list`, `ps` and `rm`; benchmarking uses the separate Python script above; [setup](ollama.md) |

## Historical source checks in saved-data audits

A saved-only audit can still require the source files in its checkout to match
the original report. The normal-derivative and residual-information auditors
compare every recorded source hash with the current repository files. Current
main differs from both recorded closures, so those checks report a source
mismatch here even though they run no model or optimizer.

Use the exact recorded source and hashes when reproducing a source-binding audit.
The matching recorded revisions are:

| Source-binding audit | Matching checkout |
| --- | --- |
| Normal derivative, 33 recorded source pins | [`d40502fed3de93989c73d4c8cf614f6f6b6d7e45`](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/commit/d40502fed3de93989c73d4c8cf614f6f6b6d7e45) |
| Residual information, 38 recorded source pins | [`1f51bae35eb862dca4a259016cc31bf1504207f9`](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/commit/1f51bae35eb862dca4a259016cc31bf1504207f9) |

Both revisions contain their public auditors. These two fixture archives do not
include complete source ZIPs, so recover the matching source separately and then
follow its recorded README with fresh destinations. The table is verified by
comparing recorded pins with Git blobs; no audit or numerical replay is rerun.

Review manifests, reports and saved audit receipts directly when examining the
historical result from current main. Keep the guards intact: a source mismatch
is an unresolved provenance check, not evidence that a new numerical experiment
failed. The newer acquisition artifact auditors explicitly support recorded
source snapshots as data; follow each tool's own contract.

The separate [exact active-face follow-up](finite-acquisition-protected-active.md)
retains its [first expectation failure](validation/finite-acquisition-protected-active.md).
Its separately frozen corrected selection passes 821 tests and 33 subtests,
then the original complete 24-case study exits 1 at 11/12 matched passes.
The later [saved-data physical-rounding diagnostic](finite-acquisition-physical-rounding.md)
passes 49 controls but finds no accepted point among 128 adjacent physical
corners. It makes no fitter, QP-solver, forward-model or literal PNG call.
See [commands as provenance and exact source bindings](validation/finite-acquisition-physical-rounding.md).
The later [inward-margin diagnostic](finite-acquisition-inward-margin.md)
passes 103 selected controls and all five gates at all 128 new corners, with
an independent 8,030-check saved-only audit. It also makes zero forward-model
or literal PNG calls. Its [source-bound result](validation/finite-acquisition-inward-margin.md)
does not add an executable command, fitter or UI control to main.
A separately frozen 112-input [paired literal runner](finite-acquisition-inward-literal.md)
passes 162 selected controls, replays the baseline exactly and rejects the
predetermined candidate on higher actual training cost. Its [recorded commands
and first terminal outcomes](validation/finite-acquisition-inward-literal.md#recorded-commands-and-terminal-results)
are provenance for that research checkout. Those runtime, test and runner
files remain absent here; they are not main-branch commands.

## Output and side effects

Use a new scratch destination for generated benchmark/example reports. The
photo-benchmark script can overwrite report paths; `--example` creates the
destination and its parents but refuses a nonempty folder. The original
`scripts/corner_sweep.py --json PATH` overwrites PATH and requires its parent
to exist. The independent corner, frame, directional, finite-centre,
moment and supplemental-aperture runners refuse an existing destination,
including a dangling symbolic link, and require its parent directory to exist.
The canonical join runners
also refuse existing destinations, but can create their output parent directories;
the directional free-arc runner requires its parent to exist. The Ollama
benchmark creates its output parent and overwrites both the JSON destination
and its `.md` sibling if they already exist. Choose a fresh report basename to
preserve earlier results.
Printer import defaults to the tracked `data/printers.json`. Review a generated
diff before replacing committed data.

The affine runner also requires fresh `.json` destinations in existing
directories, with distinct output/audit paths. Timing requires
`--quiet-interval`; `--no-timing` removes that requirement. `--complete` is the
only mode that starts inverse fits. Help and parser refusal run before expensive
numerical imports. Exit **0** means the requested preservation/control protocol
passes, including retained target misses; it does not mean every case meets its
scientific target. Exit **1** can mean a requested protocol check fails or an
uncaught input-loading error. Exit **2** covers explicit argparse/CLI and
destination checks. A missing or malformed canonical/source JSON can exit 1
before fitting and without a new report. The continuation's expected first
failure is a retained failed row, not a successful geometry result.
The recorded affine continuation exits **1** because its frozen built-in
comparator mixes tuples and JSON lists. Keep that failed audit; the separate
[saved-report audit](../studies/fixtures/finite-affine-batch-v1/README.md#retained-continuation-comparator-failure)
checks both parsed artifacts and passes all 35 later rows without rerunning fits.

The frozen 24-case finite-centre study exits **1** because its planned 4×4/8×8
aperture-order comparison misses the unchanged tolerance, even though all 12
matched recovery targets pass. Keep its full report. A separate supplemental
8×8/16×16 pass does not replace that failure. Exit **2** reports parser/input or
output-path refusal; see the [complete study record](validation/finite-free-centre.md).
The paired measured-ring replay also retains all upstream refusals. Its exit
**1** means the full declared population does not meet every target or a control
fails; do not drop the two upstream rows to turn that into an all-case pass.
The moment replay's exit **0** means exact reproduction of its retained rows,
including failed targets and refused proposals; it is not an all-target pass.

The captured-field intensity diagnostic under
[`studies/fixtures/finite-photo-intensity-v1/`](../studies/fixtures/finite-photo-intensity-v1/README.md)
contains a `.py.txt` provenance archive and a complete result. It is not a
standalone replay CLI. Its original absolute input aliases are documented and
hash-bound; renaming that archive to `.py` does not make a portable experiment.

`--help` is a read-only parser check only for the listed Python scripts
with an argparse help mode. The listed study runners also provide `--help`. Do not append it to smoke or FreeCAD helpers and
assume that work will be suppressed. Help output does not execute a study,
validate an installed model, exercise the network or qualify an export.

The reference library has its own [build and generation map](../reference-library/BUILD.md).
Reading its committed HTML/PDF differs from rebuilding it, checking a browser,
running native OpenSCAD or refreshing external links.

The acquisition capture/continuation scripts and frozen plans are provenance
entry points, not saved-only audits. Explicit capture execution generates
synthetic scenes and calls forward models. The main-based publication does not
qualify fresh execution against its changed backend; a new experiment must bind
its own source and environment. Do not import the recorded source merely to
inspect the archive. The documented portable workflow reads its bytes only.

The source-cell mean study's explicit runner,
`studies/verification/finite-acquisition-mean-v1.py --output-dir NEW_DIRECTORY`,
performs new acquisition-mean evaluations against saved captures and requires
its runtime/input source files committed in the current HEAD. Its help mode
does not evaluate a mean. A new execution has its own source binding; the saved
record at `521c318` is not silently relabeled after the workspace-metadata repair.
Use the saved-data workflow for ordinary review.

The [finite-chord normal derivative](finite-normal-derivative.md) is now an
experimental Python operator. Its [complete qualification](validation/finite-normal-derivative.md)
retains one panel-budget unknown and a compressed-map error-estimation limitation.
It has no HTTP mode or fitter integration. The saved rotation command above
remains saved-array arithmetic; it does not validate this new operator.

For the new study, `studies/verification/finite-normal-derivative-v1.py --help`
and `studies/verification/finite-normal-report-audit-v1.py --help` are read-only.
The first script's explicit `--output NEW.json` performs the complete 337-scene
numerical qualification; the second reads an already decoded report with
`--report FILE --output NEW.json` and makes no model calls. Both refuse an
existing destination and require its parent. The original study exits 1;
successful saved-data auditing does not change that result. Follow the
[hash-verified archive instructions](../studies/fixtures/finite-normal-derivative-v1/README.md).
