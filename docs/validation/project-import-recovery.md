# Project import recovery — November 10, 2026

Import now stages the selected recipe and builds it before committing its inputs to the workbench. A failed build preserves the current project, including unsaved edits and any still-valid exports. A successful retry replaces the project and releases the superseded model.

The two new browser regressions failed on the previous implementation: a forced service failure replaced the user's 6 mm thickness with the imported 3 mm, and a self-intersecting outline removed the current export action. Both pass after the fix. The 13 import, recovery, and calibration-lifecycle browser scenarios passed against an isolated local CAD service. Production typecheck/build, Ruff, Prettier, and whitespace checks passed.

The service failure is injected. Outline validation and successful retry use the real CAD backend and synthetic profiles. These checks do not establish physical accuracy, print fit, or native slicer behavior. Hosted CI is separate evidence for the PR revision.
