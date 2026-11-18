# Agent harness for checking photo-to-CAD work

Use grounded task packets and deterministic checks to improve assistance with
capture, trace, build and export. The optional local AI can explain warnings
or propose supported settings. A user supplies measurements and reviews
proposals, and the tracing and geometry code produce the result.
[Optional local AI](ollama.md) · [Architecture](architecture.md)

## Capture the context of the part

- Start with the intended workflow, source fixture and revision, measured
  reference and units, expected geometry or export, and the target validation
  check. Distinguish source dimensions, user-approved design scaling, build
  dimensions and printer settings. If a measurement is missing, ask for it or
  report the limit. [Reference sheet](reference-sheet.md)
- Prefer the current deterministic next-step guidance, bounded build/status
  fields and validated settings over an open-ended tool loop. Bind suggestions
  to the inputs they describe. Use the existing review, apply and undo
  transitions and check that stale advice stays stale as inputs change.
  [Workflows](workflows.md)
- For continuity, record the fixture identity, approved settings, last valid
  build, current build or export state, failing check and next action. Recheck
  current state after resuming. Use synthetic or explicitly approved samples.
  Keep private photos, library contents and local paths out of shared traces
  and prompts beyond their approved boundary. [Data handling](privacy-security.md)
- Verify post-build geometry and the intended export through the repository's
  existing checks. Have a reviewer compare actual dimensions/units, expected
  topology and any tolerance limits with the independent fixture. Keep printed
  fit as a separate physical outcome. [Exports](exports.md) · [Validation](validation.md)

## First experiment

Pick a measured flat-part fixture plus a failure case where scale is missing
or the settings change while a suggestion is pending. Predeclare the expected
units and tolerance, the intended artifact, and what the interface should do
with incomplete or superseded inputs. Compare current task instructions with
the same instructions plus a compact packet pointing to controlling evidence
and the exact validation path. Use the same source, local model if enabled,
tool set, hardware and measurement budget.

Track correct dimensions within the fixture's tolerance, explicit uncertainty
when justified, export success and readback, stale proposal handling and
operator corrections. Record wall time and attempts, including any rebuild or
failed export. Preserve every accepted baseline case and require a predefined
improvement in review time or rework. Use the photo benchmark or matching
geometry study for each later claim about reconstruction or capture quality.
[Photo benchmark](photo-benchmark.md)

## Reference patterns

- Practice resuming a measured build and independently verifying the result. [Learn Harness Engineering](https://github.com/walkinglabs/learn-harness-engineering)
- Own context, structured settings and recovery transitions in the application. [12-Factor Agents](https://github.com/humanlayer/12-factor-agents)
- Point coding agents to development commands and governing geometry docs. [AGENTS.md](https://agents.md/)
- Specify the fixture, tolerance and observable export before editing. [GitHub Spec Kit](https://github.com/github/spec-kit)
- Study state checkpoint and approval patterns for the existing workbench. [Deep Agents](https://github.com/langchain-ai/deepagents)
- Record a short input, action, result and verification trace. [Mini SWE Agent](https://github.com/SWE-agent/mini-swe-agent)
- Compare other harnesses' context paths and verify significant claims upstream. [Awesome AI Anatomy](https://github.com/NeuZhou/awesome-ai-anatomy)
- Consider isolated benchmarking once the existing geometry and browser runners need shared task packaging. [Harbor](https://github.com/harbor-framework/harbor)

[Original SATNA Project discussion](https://www.reddit.com/r/SATNA_PROJECT/comments/1xyrkvz/your_ai_agent_might_not_need_a_better_model_it/)
