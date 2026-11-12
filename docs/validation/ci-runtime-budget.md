# Hosted verification runtime budget — November 12, 2026

This candidate is based on warp-chain head
`8523862145ef264d265d84b9443b779ea09db072`
([draft PR #61](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/61)).
It changes only the workbench job's overall time budget from 30 to 45 minutes,
plus this documentation. The installed setup, source, tests, serial browser
worker, 90-second scenario timeout and 15-second expectation timeout are retained.

## Recorded failure and budget choice

The [PR #59 workbench run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43214844810)
at `6d2672710e54e9117048613dec6ef3ea448062b7` started job `131171327007` at
12:06:05 UTC. Its log records **1,178 Python tests passed in 527.19 seconds**,
then starts 74 serial browser tests at 12:15:56. The 58th scenario passed at
12:36:07, followed by cancellation at 12:36:18 near the configured 30-minute
job limit. No failed scenario is recorded before that cancellation. This is
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
