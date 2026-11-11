# Engineering check audit

Scope: the existing independent source-height comparison, November 11, 2026.
Target: help a person decide whether a photo-derived profile agrees with a
reserved physical dimension. Combined UX and observable accessibility review;
not a complete WCAG audit.

| Step | Observed behavior | Health |
| --- | --- | --- |
| 1. Enter an independent height | A labelled numeric field accepts 20.2 mm for a synthetic 20 mm source outline. Keyboard entry works and focus is visible. | Good |
| 2. Interpret the difference | The readout gives −0.200 mm and correctly limits manufacturing claims, but has no user-defined allowable discrepancy or measurement bound. A user cannot distinguish a decisive mismatch from an inconclusive measurement. | Needs work |
| 3. Change design scale | The comparison explicitly concerns the source outline before design scaling, preserving the independent-check purpose. | Good scope; regression verification required |

Fresh baseline evidence: `.local/verification/height-check-before.jpg` in the
isolated engineering worktree, captured from the running curved-placement
preview. The synthetic measurement was cleared afterward. No real photograph
or physical measurement was used. Labels and visible focus were inspected;
native screen-reader behavior, mobile reflow, and automated contrast checks
were not checked in this baseline review.

Recommendation: extend the existing disclosure with optional, blank-by-default
decision inputs. Compare the complete entered measurement interval with the
user's allowed source-height discrepancy. Keep contact with the decision
boundary inconclusive, explain the equation, preserve the inputs in a recipe,
and recompute after source changes. Do not infer a physical accuracy statement,
printer tolerance, or a manufacturing approval from this one comparison.

## Implemented review

| Step | Result after the change | Health |
| --- | --- | --- |
| 1. Enter an independent height | The existing labelled entry and source-height difference remain; additional decision inputs start blank. | Good in tested flow |
| 2. Interpret the difference | A complete entered interval is classified strictly within, strictly outside, or inconclusive; absent/invalid inputs produce no assessment. The user's bound is explicitly conditional. | Good in tested flow |
| 3. Change source, design or units | Source-width edits recompute the check; explicit design scaling leaves this source comparison alone. Unit changes retain boundary contact as inconclusive. Old recipes and a new sample clear earlier inputs. | Good in tested flow |

Fresh [desktop evidence](../images/engineering-height-check.jpg) uses an 80 × 50
mm synthetic source and 50.2 mm independent input, with 0.5 mm allowance and
0.4 mm measurement bound. The displayed interval is −0.6 to 0.2 mm and is
inconclusive. The live browser also verified exact boundary contact before and
after switching mm → inches → mm. A discovered conversion-rounding issue was
corrected: physical check inputs now retain full numeric precision during unit
changes, with a small floating-point guard on the decision limits.

Arithmetic verification includes twelve fixed cases and 451 comparisons with
an independent integer-lattice interval oracle. Repository browser checks use
the real CAD service to verify three decisions, source/design edits, recipe
round trips, partial/invalid input handling, rejected imports without project
replacement, and old-recipe/new-photo clearing. Phone checks cover keyboard
focus order, no horizontal overflow at 390 px and no axe violations under the
WCAG A/AA tags tested. This does not establish native screen-reader behavior or
complete WCAG conformance.

An initial browser assertion compared rendered line breaks with text content;
it was corrected. A later full run was interrupted after 31 passing cases with
process exit 143, without a completed result. Those partial artifacts are kept
in `.local/verification/interrupted-browser-run`; they are not a passing suite.
The completed final run passed all **60 repository browser/decision tests** in
4.9 minutes. The production build, lint, diff whitespace check and 144 local
document links also passed. Its source revision and artifact hashes are
recorded in `.local/verification/engineering-verification.json`. Python backend
code is unchanged in this patch; the full Python suite was not rerun locally.

No real-photo measurement, native slicer inspection, printer calibration,
physical prototype, structural analysis or physical error bound was verified.
