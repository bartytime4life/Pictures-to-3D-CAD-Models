# Contributing

Use the [documentation index](README.md) to find the user guide, implementation
contract and validation record for the behavior you want to change.

## Prepare a change

1. Check your branch, remote and local changes before updating or installing.
   Preserve unfinished work; use a separate branch or worktree when appropriate.
2. Follow [development and setup](development.md). The workbench uses Python
   3.12 and its root lockfiles. The [companion library](../reference-library/BUILD.md)
   has its own environment and Node lockfile.
3. Reproduce the issue with synthetic or explicitly authorized inputs. Keep
   personal photographs, native builds, model weights, environments and private
   reports out of source control.
4. Make a focused change. Keep source measurements separate from design resizing,
   optional checks separate from geometry, and every asynchronous result bound
   to the current project revision.

## Validate the affected behavior

For a workbench change, run:

```bash
npm run build
make test-app
make lint
```

Build before the test target so frontend-serving Python checks inspect current
assets. The test target itself runs Python tests, builds the frontend, then runs browser tests.
Confirm that port 8000 belongs to this checkout before allowing a local test to
reuse it; see [test-server selection](development.md#validate-changes).

For library changes, run `make test-library` from the repository root. If you
change generated-reader inputs, run `make build-library` first and review the
generated changes. Native OpenSCAD skips remain skips. Follow the library's
[contribution guide](../reference-library/CONTRIBUTING.md) for required generated
outputs and both browser transports.

For documentation-only changes, check relative file links and heading anchors,
compare commands and schemas with their implementations, and run the library's
existing documentation-accuracy tests when editing its guides. Rebuild generated
outputs when their source text changes. Record the checks actually run; an old
test count is not a fresh result.

## Keep documentation and evidence aligned

- Update the relevant guide, [architecture](architecture.md) or API contract
  when behavior changes. Add navigation to the [index](README.md) for a new
  guide and a concise entry in [change log](changelog.md).
- Edit source Markdown or data rather than generated HTML, catalog directories,
  figures or PDFs. The library's [generation map](../reference-library/BUILD.md#what-is-generated-from-what)
  identifies each source and command.
- Preserve historical validation dates, revisions, counts and limitations. Add a
  separately scoped result for new work rather than rewriting a prior run.
- Separate source tests, browser behavior, hosted CI, installed-tool imports and
  physical measurements. AI fixture tests establish integration behavior rather
  than model quality. A valid CAD solid or bed footprint does not qualify a print.
- For scientific changes, identify any shared production code or assumptions in
  the synthetic generator. Reserve independent geometry, dimensions and capture
  conditions for evaluation; retain failed traces and unmatched features beside
  conditional error statistics. The [scientific review](validation/scientific-model-review.md)
  records the original findings at `5588a52`; follow the [fit-support record](validation/fit-support.md)
  and current [benchmark guide](photo-benchmark.md) for later changes and remaining limits.

## Submit a reviewable result

Use [project status](project-status.md) to identify open changes and avoid
describing an unmerged algorithm as installed or deployed.

Explain the concrete trigger, changed behavior and relevant validation. Link the
guide or evidence record and include screenshots for visible interface changes.
Identify untested boundaries that materially affect the result. A pull request
is a review artifact; merging, deployment and physical acceptance are separate
actions.

## Documentation maintenance

1. Identify the source revision with `git rev-parse HEAD` and record local
   changes. Update the guide for that implementation; distinguish open review
   branches from `main` in [project status](project-status.md).
2. Check commands against the root and library Makefiles, setup scripts and
   lockfiles. Check API fields/defaults against `backend/app.py`,
   `backend/models.py`, and `/openapi.json`; exercise changed examples against a
   deliberately selected local server.
3. Review source Markdown, relative targets, heading fragments and table
   columns across the repository. Generated library `REFERENCES.md`,
   `GITHUB.md`, HTML, figures and PDF come from the
   [generation map](../reference-library/BUILD.md#what-is-generated-from-what);
   do not hand-edit them or refresh dated external metadata merely to change
   a documentation date.
4. Run the existing documentation-accuracy tests from `reference-library/`:

   ```bash
   .venv/bin/python -m unittest discover -s tests/python -p test_docs.py -v
   ```

   These tests cover library claims and local files; they are not a complete
   root-guide or external-URL audit. Check the rest separately. Rebuild with
   `make build-library` when generated-reader inputs change, then inspect the
   resulting diff. Guide-only edits do not create a new library release.
5. Keep old results in their dated records. Add a separately scoped evidence
   entry for the current checks, identify any executable changes, and choose
   tests for the affected behavior. Documentation parsing does not establish
   a fresh Python/browser regression suite. Update navigation and the change log.

Use the [current coverage and inventory](validation/documentation-pr70.md#coverage-inventory)
and [earlier inventory](validation/documentation-response-state.md#coverage-inventory)
to include guides, worksheets and generated/historical records in a review.
The [developer-tool catalog](developer-tools.md) centralizes numerical commands
and output rules. Preserve report files explicitly: some analysis tools refuse
existing paths, while photo and Ollama benchmarks replace their report files.
