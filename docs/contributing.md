# Contributing

Use the [documentation index](README.md) to find the user guide, implementation
contract and validation record for the behavior you want to change.
The [source-scope guide](project-status.md) distinguishes the current main source
from research PRs targeting another branch. Record the actual base and executable
revision; a higher PR number or test count does not imply integration into main.

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

Choose checks by what the documentation exercises:

| Documentation change | Verification |
| --- | --- |
| New page, heading or navigation | Parse Markdown; check relative files, image paths, heading fragments, code fences and table columns across the full inventory |
| Setup, environment variable or CLI example | Compare with the actual Makefile, script or parser; use read-only help only where implemented, and identify output/overwrite behavior |
| Numerical Python example | Execute in the pinned environment with runtime warnings treated as errors; bind to source hashes and record whether it invokes preparation, a forward operator or an optimizer |
| Archived evidence instructions | Verify compressed and decoded hashes; use a fresh scratch destination and saved-data auditing before considering an expensive replay |
| Current source or CI statement | Read back the exact branch/head, dependency base and run conclusion; timestamp the snapshot and link the older immutable record |
| Proposed research | Label it prospective; separate derivations, preflight contracts, numerical replay, independent audit and physical qualification |

Run the companion library's documentation-accuracy tests from the repository
root without rebuilding or rewriting its verification record:

```bash
python3 -m unittest discover -s reference-library/tests/python -p test_docs.py
```

These tests check documented counts, local links and worked examples using the
standard library. They do not exercise the workbench, browser or native CAD tools.
A handbook text change also needs its generated HTML and PDF rebuilt; follow the
[library generation map](../reference-library/BUILD.md#what-is-generated-from-what).

For a documentation-only pass, compare every tracked non-document blob with
the declared base before and after verification. Preserve accurate historical
reports. Keep generated library outputs unchanged unless their source changed;
then regenerate them and list those outputs explicitly in the review. Library source edits still follow its
generation rules; a workbench-only navigation change needs no library rebuild.
The [current documentation review](validation/documentation-coupled-state.md)
separates this documentation-only main update from the
[local acquisition-recovery snapshot](finite-acquisition-recovery.md).
The [earlier main documentation review](validation/documentation-main109-state.md)
retains its original source and verification scope.

## Keep documentation and evidence aligned

- Update the relevant guide, [architecture](architecture.md) or API contract
  when behavior changes. Add navigation to the [index](README.md) for a new
  guide and a concise entry in [change log](changelog.md).
- Edit source Markdown or data rather than generated HTML, catalog directories,
  figures or PDFs. The library's [generation map](../reference-library/BUILD.md#what-is-generated-from-what)
  identifies each source and command.
- Preserve historical validation dates, revisions, counts and limitations. Add a
  separately scoped result for new work rather than rewriting a prior run.
- Distinguish implemented research on a local candidate from runtime included in
  main. Retain complete failed protocols beside partial target passes and focused
  tests. If saved arrays cannot reconstruct a reported quantity, record that audit
  gap; do not turn a failed audit into a pass or rerun a model as part of a
  documentation-only update.
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

Explain the concrete trigger, changed behavior and relevant validation. Link the
guide or evidence record and include screenshots for visible interface changes.
Identify untested boundaries that materially affect the result. A pull request
is a review artifact; merging, deployment and physical acceptance are separate
actions.
