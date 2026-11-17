# Precision Studio pull-request verification

Prepared November 17, 2026. The application change is commit
`fcf5e938876e275fd98853570131953a80b5ff87`, based on main at
`1c41ac14475347b848c4edc5144edd059e63487a`. A separate, stacked documentation
change contains the project-guide reorganization and this record.

## Source and integration

The application commit contains all runtime code, tests and the guides required
by the embedded Knowledge API. The documentation change contains no additional
application code. Local checks used that exact application source with the
companion documentation present. All ten curated guides are also present in the
application commit on its own.

Integration retained main's relief processing and mathematics audit. In
particular, the moved API reference preserves the 7.6-megapixel reduced-JPEG
threshold, upload limits for every affected route, and the relief export kinds.
The newer five-slicer behavior replaces the older three-slicer wording. The
60-minute CI limit, split-plan tie ordering, geometry-failure distinctions and
photo-library wording remain intact.

## Checks run for this candidate

- `npm run build`: passed, including the TypeScript check.
- `npm run test:unit`: 30 passed.
- Focused backend tests: 239 passed, including the current relief suite.
- Installed-Chrome Playwright rerun: 46 passed; two optional installed-model
  cases skipped because DINOv3 and AI depth were unavailable.
- `make lint`: passed, covering Ruff and frontend/browser-test Prettier checks.
- Authored Markdown formatting and `git diff --check`: passed.
- Independent documentation review: 467 relative links and 43 heading-anchor
  links resolved across 17 changed/new guides and records before this note was
  added. This note's navigation was checked separately.

Backend command:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
  tests/test_documentation.py tests/test_process_planning.py \
  tests/test_slicer_handoff.py tests/test_slicer_bridge.py \
  tests/test_printing.py tests/test_assistant.py tests/test_three_mf.py \
  tests/test_relief.py
```

The browser rerun covered background removal, common references, Knowledge
routing, photo library, print preparation, quick edit, relief, slicer handoffs,
studio accessibility, Knowledge/Science scenarios, workspace navigation and
recovery regressions. It used a separate loopback server for this candidate and
one Chrome worker. Native slicer launches were mocked in the launch tests.

The full Python suite, separate companion-library suite and hosted CI are not
part of these local results. No native slicer import, printer operation or
physical fit was validated.

## Earlier evidence remains historical

The [original interface review](precision-studio.md), its screenshots and its
[manifest](evidence/precision-studio/manifest.json) remain bound to the earlier
`502b2f5` working-tree snapshot. That record includes the original failed runs
and subsequent corrections. Its statement that the work was uncommitted
refers to that review time, before these pull requests were prepared.

The historical manifest is unchanged, with SHA-256
`e4f641a29eac20a543ef0076d91a1d44014d6449b677bf0a071194ed4d5648c6`.
Its file hashes must not be interpreted as hashes of the newer PR head. The
[earlier slicer-workspace review](slicer-workspace.md) likewise retains its
original scope. Current relief screenshots under `docs/images/` were refreshed
by the browser rerun.

The production browser entry assets used for this candidate have these hashes:

| Asset                                 | SHA-256                                                            |
| ------------------------------------- | ------------------------------------------------------------------ |
| `assets/index-Zg6NMUqU.js`            | `e498ea2d54687ce73b803ee2b2eaf16c8f27a79f4b634174a93a3a3ea387d731` |
| `assets/rolldown-runtime-XKyaHtl9.js` | `548d1dbf321e7d2ae804fcc158b588706a7c52f8ca175de1490c6ccb4dbe55b7` |
| `assets/three-baT44-aj.js`            | `be3a364bca9c1fafabcbbc5af3dd5a1e8aa253c63911c202d03f36d1bcf26a7f` |
| `assets/vendor-BdGwEMPB.js`           | `397be9cb47c45d667c3590ae0212dd7c9dab3b88708c1940ccbca242daaaa8a8` |
| `assets/vendor-vwP0uNFC.css`          | `0af1ca445d642daf51014f32013418ca146f58e1fdb4cf3a9f1fcd61f935ab9b` |
| `assets/index-BEHTK2CK.css`           | `cb2389af65cd7760a48ccf10b574e953700cf4d2230a87f5e4d1343a859c4f1e` |
