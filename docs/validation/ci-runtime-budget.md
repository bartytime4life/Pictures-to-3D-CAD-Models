# Hosted verification runtime budget — November 12, 2026

PR #62 is based on warp-chain head
`8523862145ef264d265d84b9443b779ea09db072`
([draft PR #61](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/61)).
That PR changes only the workbench job's overall time budget from 30 to 45 minutes,
plus this documentation. The installed setup, source, tests, serial browser
worker, 90-second scenario timeout and 15-second default expectation timeout are
retained, including existing per-assertion 30- and 60-second overrides.

## Recorded failure and budget choice

The [PR #59 workbench run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43214844810)
at `6d2672710e54e9117048613dec6ef3ea448062b7` started job `131171327007` at
12:06:05 UTC. Its log records **1,178 Python tests passed in 527.19 seconds**,
then starts 74 serial browser tests at 12:15:56. The 58th scenario passed at
12:36:07, followed by cancellation at 12:36:18 near the configured 30-minute
job limit. The [job annotation](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43214844810/job/131171327007)
explicitly reports that the maximum execution time of 30 minutes was exceeded.
No failed scenario is recorded before that cancellation. This is
incomplete browser evidence, not a completed suite or a reproduced assertion
failure. Setup, formatting and browser installation had already passed.

The observed browser portion consumed about 1,211 seconds for 58 scenarios.
Scaling that partial rate to 74 and adding the observed pre-browser time gives
about **35.6 minutes**. This is a workload extrapolation, not a performance
prediction: scenarios differ and runner speed varies. A 45-minute job provides
about 26 % headroom over that estimate while retaining a finite execution cap.
The [GitHub job-timeout contract](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idtimeout-minutes)
explains automatic cancellation at the job limit.

## Verification scope

The workflow parses successfully. Comparing parsed YAML with its parent leaves
exactly one semantic difference: `jobs.test.timeout-minutes`, from 30 to 45.
Source and test hashes remain identical to PR #61. The complete local Python
and optical-study results remain separately bound to their
[warp-chain record](warp-observations.md); this workflow change is not a new
product or physical-accuracy test.

A fresh hosted run must still demonstrate completion at this candidate's exact
head. Before a terminal result is observed, the repair is a measured-budget
change awaiting hosted confirmation. Existing live runs are left to finish
under their original configuration; changing this file cannot extend their
already-started budgets.

## Later observations during documentation alignment

At **November 12, 12:55 UTC**, the [PR #60 workbench run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43217681248)
had completed successfully at `778c3392c6dfe111d8f422959fbdbc09ad8ba75b`:
**1,225 Python tests** and **74 browser scenarios** passed. This is a separate
head under the original budget; it does not retroactively complete PR #59 or
verify the changed budget at PR #62.

PR #62 was published at `ca321442bd276c177c31f00bcd62fb0ea27b2e0e`.
Its [45-minute workbench run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43221471259)
was still in progress at that observation. The [PR #61 workbench run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43220874898)
was also in progress; its separate [library run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43220874912)
had passed. Follow [project status](../project-status.md#evidence-by-scope) and
these exact run links for subsequent observations.

## Terminal follow-up — November 12, 13:20 UTC

The [PR #62 workbench run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43221471259)
completed successfully at exact head `ca321442bd276c177c31f00bcd62fb0ea27b2e0e`.
Its log records **1,249 Python tests passed in 394.53 seconds**, followed by
**74 browser scenarios passed in 19.2 minutes**. The workflow completed at
13:16:44 UTC. This verifies complete execution at the changed head; it does not
establish that every runner needs 45 minutes. The earlier partial-rate estimate
remains an extrapolation and runner performance varies.

PR #61's separate workbench run completed cancelled. It retains its original
configuration and outcome. The new raw-source fitter has separate local and
future exact-head evidence; these parent runs do not validate that new code.
