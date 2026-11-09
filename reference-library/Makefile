# Build, test and package the reference library.   make help
# Paths are relative to this folder; run make here or via the top-level Makefile.
PYTHON ?= python3
NODE ?= node
CODEX_PY := $(HOME)/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12
# The PDF needs reportlab + lxml. Use PYTHON when it has them, else the Codex runtime if present.
PDF_PYTHON ?= $(shell "$(PYTHON)" -c 'import reportlab, lxml' >/dev/null 2>&1 && printf '%s\n' "$(PYTHON)" || (test -x "$(CODEX_PY)" && printf '%s\n' "$(CODEX_PY)") || printf '%s\n' "$(PYTHON)")

.PHONY: help all build calc figures html pdf plate test test-python test-node check links refresh-github verify dist dist-check release clean

help:
	@echo "make build        calculations, figures, HTML, PDF"
	@echo "make test         Python + Node unit tests (incl. JS-vs-Python agreement)"
	@echo "make check        browser end-to-end check of index.html (Playwright + Chrome)"
	@echo "make plate        render the synthetic plate with OpenSCAD and run design-rule checks"
	@echo "make links        network check of every catalog URL (optional)"
	@echo "make verify       run all automated checks and write verification.json"
	@echo "make dist         write SHA256SUMS, the ZIP archive, and the root PDF copy"
	@echo "make release      build + plate + test + check + verify + dist"
	@echo "make all          build + test + check"

all: build test check

build: calc figures html pdf

calc:
	"$(PYTHON)" examples/calculate.py >/dev/null

figures:
	"$(PYTHON)" scripts/make-figures.py

html: figures
	"$(NODE)" scripts/build-library.mjs

pdf: html
	"$(PDF_PYTHON)" scripts/make-pdf.py

plate:
	"$(PYTHON)" examples/build_plate.py

test: test-python test-node

test-python:
	"$(PYTHON)" -m unittest discover -s tests/python

test-node:
	"$(NODE)" --test tests/node/*.test.mjs

check:
	"$(NODE)" scripts/check-library.mjs
	"$(NODE)" scripts/check-photos.mjs
	"$(NODE)" scripts/check-photo-transfer.mjs

links:
	"$(NODE)" scripts/check-links.mjs

refresh-github:
	"$(NODE)" scripts/refresh-github.mjs --write

verify:
	"$(PYTHON)" scripts/record-verification.py

dist:
	"$(PYTHON)" scripts/make-dist.py

dist-check:
	"$(PYTHON)" scripts/make-dist.py --check

release: build plate test check verify dist

clean:
	rm -rf tmp examples/output
