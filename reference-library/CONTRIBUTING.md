# Contributing

This library is useful only if it stays accurate. Each change should keep three promises:

1. **Evidence is labeled.** A claim is either sourced (with a catalog entry and a review depth), derived by code, or stated as engineering synthesis. Never present an inferred value as a measurement.
2. **One source of truth.** Counts, charts, and worked numbers come from data files and scripts, never from retyping. If you change a number in one place, the tests should tell you everywhere else it appears.
3. **Tests pass.** Run `make test`. Before publishing, run `make release`.

All paths below are relative to `reference-library/`. The photo-to-CAD workbench elsewhere in this repository has its own setup and tests; see the repository's top-level README.

## Add or edit a source

1. Edit `sources.json`. Every entry needs `id`, `category`, `title`, `url` (https, without `utm_` parameters), `type`, `level`, `use`, `limit`, `evidence`, and `checked` (YYYY-MM-DD).
2. Choose an `evidence` value that matches what you actually read. The options run from `page` (page content checked) down to `metadata` (bibliographic only); `scripts/lib/runtime.mjs` lists all of them. Do not upgrade an entry's review depth without reading more of the source.
3. GitHub entries also need `repository`, `license_metadata`, `archived`, `last_push`, and `default_branch`. `node scripts/refresh-github.mjs --write` fills them from the API.
4. Run `make build test`. The builder regenerates `sources.csv`, `REFERENCES.md`, `GITHUB.md`, and the catalog chart. It refuses to build if the schema check fails.
5. If the source count changed, update the counts in `README.md` and `VERIFICATION.md`. `tests/python/test_docs.py` will name every place that disagrees.

A link that appears in `HANDBOOK.md` or `RESEARCH-NOTES.md` must also be a catalog entry. The tests enforce this.

## Edit the handbook

- Keep chapter headings in the form `## N. Title`. The table of contents, the PDF outline, the route finder, and the calculators all refer to chapters by number.
- A worked number in the text must equal what `examples/calculate.py` computes. Add the calculation there, run `python3 examples/calculate.py`, and add an assertion to `tests/python/test_docs.py`.
- Add a figure with `![alt text](assets/figures/name.svg "Caption shown under the figure.")`. The HTML and PDF builders both handle it.

## Add a figure

1. Write a builder function in `scripts/figures.py` using the `Figure` primitives (line, rect, circle, ellipse, polygon, polyline, arc, text, arrow, chip). Compute any plotted values from the formula; don't type them in.
2. Register it in `FIGURES`, then run `python3 scripts/make-figures.py`.
3. Reference it in the handbook or README. The tests fail if a figure is never shown.
4. Check the SVG in a browser and the PDF page. The PDF uses DejaVu fonts, which are wider than most browser fonts, so leave room around labels.

## Add a calculator

A calculator lives in four places, and the tests compare them:

1. **Formula:** `cadkit/calc.py`. Raise `ValueError` for invalid input and return warnings in a `warnings` list.
2. **Command:** a subcommand in `cadkit/cli.py` with `--json`, plus a row and a real example in `cadkit/README.md`.
3. **Browser:** the same function in `assets/js/cadcalc.js`, with the same names, thresholds, and rounding.
4. **Interface:** an entry in `assets/data/calculators.json` (inputs, formula, note, handbook section) and a `RUN` function in `assets/js/app.js`.

Then add a cross-language assertion to `tests/node/cadcalc.test.mjs` and unit tests to `tests/python/`. List the command in handbook section 23. The tests check that every CLI command appears there.

## Change the route finder

Edit `assets/data/routes.json`. The JavaScript (`CadCalc.recommendRoute`) and Python (`cadkit.routes.recommend`) implementations share one algorithm, and the Node tests compare all input and goal pairs. The route-map figure is drawn from the same file.

## Release checklist

1. Update `library.json`: `revision`, `date`, `date_label`, and `archive_name`.
2. Add a `## Revision N` entry at the top of `CHANGELOG.md` and a note in handbook section 22.
3. Run `make links` and review any `blocked` or `broken` URLs. Record real changes in `RESEARCH-NOTES.md`.
4. Run `make release`.
5. If verification writes `verification.json` and then stops because the documentation disagrees, update `VERIFICATION.md` from that record. The interrupted `make release` has not reached archive generation. Run `make release` again, or `make verify dist`, and require successful completion before continuing.
6. Run `make dist-check`, then from the repository root `sha256sum -c reference-library/SHA256SUMS`. Check the newly generated archive rather than a retained older one. Attach `dist/*.zip` to a GitHub release if you publish one.

## Style

- Plain, specific sentences. Say what a check establishes and what it does not.
- Use SI units, and millimetres for parts. Use a minus sign (−) in prose formulas and ASCII in code.
- No marketing claims, no unreviewed benchmarks, and no clinical claims.
- Do not commit generated scratch: `tmp/`, `examples/output/`, and `node_modules/` are ignored.
