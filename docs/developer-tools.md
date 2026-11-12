# Developer commands in this checkout

[Source scope](project-status.md) · [Setup](development.md) · [Architecture/API](architecture.md)

Run these from the repository root after setup. `make` prints the supported
targets. These are the tools present in the reviewed main-based source; research
scripts from a separate branch are not implied by this list.

| Tool | Entry point | Execution and output |
| --- | --- | --- |
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
| Corner sweep | `.venv/bin/python scripts/corner_sweep.py --help` | Synthetic fitting cases, optional `--quick`, `--backend PATH` and `--json FILE`; not a real-camera test |
| Native FreeCAD import check | `make freecad` | Requires `FREECADCMD`; builds synthetic fixtures and launches FreeCAD. `freecad_check.py` and its `freecad_import.py` helper have no argparse help mode |
| Printer-data import | `.venv/bin/python scripts/import_printers.py --help` | Reads the supplied pinned-source checkout and writes catalog JSON; [procedure](printer-catalog.md) |
| Local-model comparison | `.venv/bin/python scripts/benchmark_ollama.py --help` | Actual execution calls already installed Ollama models and writes JSON plus a Markdown summary; [limits](ollama-models.md) |
| Optional runtime helper | `./scripts/ollama.sh` | Prints usage. Its explicit actions are `install`, `serve`, `pull`, `list`, `ps` and `rm`; benchmarking uses the separate Python script above; [setup](ollama.md) |

## Output and side effects

Use a new scratch destination for generated benchmark/example reports. The
photo-benchmark script can overwrite report paths, and `--example` writes into
its chosen folder. Both independent study runners instead refuse an existing
destination, including a dangling symbolic link. The canonical join runners
also refuse existing destinations, but can create their output parent directories;
the directional free-arc runner requires its parent to exist. The Ollama
benchmark creates its output parent and writes both JSON and a `.md` sibling.
Printer import defaults to the tracked `data/printers.json`. Review a generated
diff before replacing committed data.

`--help` is a read-only parser check only for the listed Python scripts
with an argparse help mode. The listed study runners also provide `--help`. Do not append it to smoke or FreeCAD helpers and
assume that work will be suppressed. Help output does not execute a study,
validate an installed model, exercise the network or qualify an export.

The reference library has its own [build and generation map](../reference-library/BUILD.md).
Reading its committed HTML/PDF differs from rebuilding it, checking a browser,
running native OpenSCAD or refreshing external links.
