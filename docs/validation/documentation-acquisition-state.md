# Documentation and acquisition-evidence review — November 13, 2026

This review aligns the workbench guides with main
`68a67e766956ac41a3b73ae73d4ac553ef47db26`, including merged PR #103's
soft-shadow model, and adds a complete historical acquisition study. It does
not replace earlier software or scientific receipts with a new all-suite pass.
The primary `codex/slicer-integration` checkout remains separate and unchanged.

## Scope and corrections

| Documentation area | Review and resulting guidance |
| --- | --- |
| Root README and documentation index | Route users to current source status, developer tools, acquisition method and this review; preserve the simple workbench setup/use path |
| Source status, development and contributing | Date earlier PR/test/CI snapshots, identify the current main base and distinguish documentation checks from application or physical acceptance |
| Architecture, engineering model and reference-sheet method | Preserve the current shadow-lighting implementation; describe its normalized excess-error diagnostic without claiming a guaranteed 2 % prediction bound or untouched validation band |
| Capture and benchmark guides | Keep generated-photo results separate from measured photos; retain reported regressions and the model's limits |
| Research and roadmap | Record the controlled Gaussian moment-closure counterexample and require qualified acquisition means and independent recovery checks before automatic fitting |
| Acquisition method, validation and archive guide | Document all 32 rows/128 cells, original bootstrap failure, raw scalar failure, exact-source boundaries and saved-only review |
| Other workbench, export, slicer, printer, assistant and privacy guides | Check navigation and source/command consistency; no new installed-tool, live-model or physical qualification is implied |
| Companion reference library, templates and dated validation records | Check Markdown/navigation and preserve their original source, dates and generated-output scope; no library inputs or generated products change |

Historical records retain their original revisions, counts, unknowns and failed
outcomes. The pinned analytic-normal record is linked to its own source lineage;
its absent main-branch files are not presented as local capabilities. The new
experiment uses flat illumination and recorded source `0714aad`, not the newer
main shadow-lighting pipeline.

## Saved-evidence verification

The [archive workflow](../../studies/fixtures/finite-acquisition-operator-v1/README.md#verify-and-reconstruct-saved-data)
was executed verbatim in a fresh review directory on the declared main base:

- All **123 artifacts** match their stored and decoded byte counts and SHA-256
  hashes. All **87 recorded source/input files** match their source manifest.
- The artifact auditor passes **1,294 binding/integrity checks**, with no
  artifact failures. Its expected exit **1** preserves the raw report's failed
  scalar contract; the workflow asserts both outcomes separately.
- The separate normalizer reconstructs the represented 320 scalar values.
  Its derived report matches SHA-256
  `90a7d6db7f9555c3f06c22b269897e72b50a4f9453eb5f1952acc3e5b9631f6b`.
  The original report is unchanged and receives no new qualification.
- The complete workflow exits **0**, performs **zero scientific calls**, and
  imports no recorded backend, generator or reference model. Pillow decodes the
  PNGs; the normalizer uses only the standard library.

Four acquisition CLI help modes pass without scientific execution. All six
new acquisition Python files compile without execution and pass Ruff lint and
format checks. These are review-tool checks, not a fresh capture, optimizer,
accuracy comparison or performance benchmark. The independent mathematical/UX
audits and original execution receipts remain in the
[complete study record](finite-acquisition-operator.md).

## Documentation checks and boundaries

The final inventory is checked for local file/image links, heading fragments,
code fences and table columns, and parsed with the library's pinned
`marked 17.0.5`. Commands are compared with their actual parsers, scripts and
Makefile targets. The companion library's **19 existing documentation-accuracy
tests pass**, checking its source counts, worked values, catalogued references,
CLI names, local links and recorded PDF-page count. This does not refresh its
release or generated outputs. External URLs were not exhaustively re-fetched.

The inventory contains **90 Markdown documents**: 31 workbench guides,
34 validation records, six study archive guides, 16 companion-library documents
and three root/data documents. The navigation and parser checks report zero
errors across **1,008 local links, 96 heading links and 119 tables**, including
one local HTML link. The Markdown-only whitespace check passes. The complete
publication diff retains two trailing-whitespace diagnostics in the archived
`bootstrap-failure/bootstrap-only.patch` (lines 6 and 37): those are blank
context lines in the original diff artifact. Its hash-bound bytes are preserved;
the full whitespace check is therefore not reported as passing.

All **429 inherited non-Markdown blobs and modes match** the declared main
base. New study files are separately checked against the archive index;
no production code or generated library output changes. The documented saved
workflow reads the recorded source as data and does not install or activate it.

No application build/full Python suite, browser scenario, native slicer import,
camera/caliper benchmark or physical print is rerun for this documentation
refresh. PR #103's successful hosted run belongs to its own head, as recorded
in [source status](../project-status.md). The published candidate needs its own
CI readback; none of these checks establishes deployment or physical accuracy.
