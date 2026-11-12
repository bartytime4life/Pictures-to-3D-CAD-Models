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
make test-app
make lint
```

The test target runs Python tests, builds the frontend, then runs browser tests.
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
  gives current counterexamples and proposed acceptance checks.

## Submit a reviewable result

Explain the concrete trigger, changed behavior and relevant validation. Link the
guide or evidence record and include screenshots for visible interface changes.
Identify untested boundaries that materially affect the result. A pull request
is a review artifact; merging, deployment and physical acceptance are separate
actions.
