.DEFAULT_GOAL := help
REFERENCE_PYTHON ?= $(CURDIR)/reference-library/.venv/bin/python

.PHONY: help setup setup-app setup-library start dev build build-app build-library test test-app test-library lint smoke slicers freecad photo-benchmark corner-sweep material-gradient-study wall-gradient-study wall-localization-study profile-noise-study postblur-operator-study warp-observation-study

help:
	@echo "make setup          install app and reference-library dependencies; build the app"
	@echo "make start          start the built CAD workbench"
	@echo "make dev            start the workbench with frontend hot reload"
	@echo "make build          rebuild the app and generated reference-library outputs"
	@echo "make test           run both components' unit and browser checks"
	@echo "make lint           check workbench Python and frontend/browser-source formatting"
	@echo "make smoke          check an already running workbench"
	@echo "make slicers        inspect local Bambu Studio and PrusaSlicer availability"
	@echo "make freecad        open a fitted build in FreeCAD (set FREECADCMD) and check it"
	@echo "make photo-benchmark PHOTOS=folder   compare traces of your photos with your calipers"
	@echo "make corner-sweep   fit exactly blurred filleted corners (60-150 degrees) and report radius errors"
	@echo "make material-gradient-study OUTPUT=new-folder   run the local-profile development census"
	@echo "make wall-gradient-study OUTPUT=new-folder   examine bounded wall/lighting ambiguity"
	@echo "make wall-localization-study OUTPUT=new-folder   compare wall correction with a pinned baseline"
	@echo "make profile-noise-study OUTPUT=new.json   examine correlated samples and false precision"
	@echo "make postblur-operator-study OUTPUT=new.json   check known Gaussian plus Keys composition"
	@echo "make warp-observation-study OUTPUT=new.json   check the raw-photo to profile operator"
	@echo "Append -app or -library to setup, build, or test to select one component."
	@echo "Library browser checks use local HTTP; its own make check defaults to file URLs."

setup: setup-app setup-library

setup-app:
	./scripts/setup.sh

setup-library:
	./scripts/setup-library.sh

start:
	./scripts/start.sh

dev:
	./scripts/dev.sh

build: build-app build-library

build-app:
	npm run build

build-library:
	$(MAKE) -C reference-library PYTHON="$(REFERENCE_PYTHON)" PDF_PYTHON="$(REFERENCE_PYTHON)" build

test: test-app test-library

test-app:
	./scripts/test.sh

test-library:
	CAD_REFERENCE_PYTHON="$(REFERENCE_PYTHON)" $(MAKE) -C reference-library PYTHON="$(REFERENCE_PYTHON)" test
	CAD_REFERENCE_BROWSER_TRANSPORT=http $(MAKE) -C reference-library check

lint:
	.venv/bin/ruff check backend scripts tests
	npx --no-install prettier --check frontend/src tests/e2e playwright.config.ts

smoke:
	.venv/bin/python scripts/smoke.py

slicers:
	.venv/bin/python scripts/slicer_status.py

freecad:
	.venv/bin/python scripts/freecad_check.py

photo-benchmark:
	@test -n "$(PHOTOS)" || { echo "Usage: make photo-benchmark PHOTOS=folder (see docs/photo-benchmark.md)"; exit 2; }
	.venv/bin/python scripts/photo_benchmark.py "$(PHOTOS)"

corner-sweep:
	.venv/bin/python scripts/corner_sweep.py

material-gradient-study:
	@test -n "$(OUTPUT)" || { echo "Usage: make material-gradient-study OUTPUT=new-folder (see docs/material-gradients.md)"; exit 2; }
	.venv/bin/python scripts/material_gradient_study.py --output "$(OUTPUT)"

wall-gradient-study:
	@test -n "$(OUTPUT)" || { echo "Usage: make wall-gradient-study OUTPUT=new-folder (see docs/wall-gradients.md)"; exit 2; }
	.venv/bin/python scripts/wall_gradient_study.py --output "$(OUTPUT)"

wall-localization-study:
	@test -n "$(OUTPUT)" || { echo "Usage: make wall-localization-study OUTPUT=new-folder (see docs/wall-localization.md)"; exit 2; }
	.venv/bin/python scripts/wall_localization_study.py --output "$(OUTPUT)"

profile-noise-study:
	@test -n "$(OUTPUT)" || { echo "Usage: make profile-noise-study OUTPUT=new.json (see docs/profile-observations.md)"; exit 2; }
	.venv/bin/python scripts/profile_noise_study.py --output "$(OUTPUT)"

postblur-operator-study:
	@test -n "$(OUTPUT)" || { echo "Usage: make postblur-operator-study OUTPUT=new.json (see docs/profile-observations.md)"; exit 2; }
	.venv/bin/python scripts/postblur_operator_study.py --output "$(OUTPUT)"

warp-observation-study:
	@test -n "$(OUTPUT)" || { echo "Usage: make warp-observation-study OUTPUT=new.json (see docs/warp-observations.md)"; exit 2; }
	.venv/bin/python scripts/warp_observation_study.py --output "$(OUTPUT)"
