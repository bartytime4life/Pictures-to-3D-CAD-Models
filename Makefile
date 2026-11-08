.DEFAULT_GOAL := help
REFERENCE_PYTHON ?= $(CURDIR)/reference-library/.venv/bin/python

.PHONY: help setup setup-app setup-library start dev build build-app build-library test test-app test-library lint smoke

help:
	@echo "make setup          install app and reference-library dependencies; build the app"
	@echo "make start          start the built CAD workbench"
	@echo "make dev            start the workbench with frontend hot reload"
	@echo "make build          rebuild the app and generated reference-library outputs"
	@echo "make test           run both components' unit and browser checks"
	@echo "make lint           check workbench Python and frontend/browser-source formatting"
	@echo "make smoke          check an already running workbench"
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
