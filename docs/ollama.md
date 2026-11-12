# Optional local AI

[Documentation index](README.md) · [Model comparison plan](ollama-models.md) · [Data handling](privacy-security.md)

The assistant helps explain the photo-to-CAD process. It can suggest a better capture, explain trace warnings, identify measurements to check, propose design and print-setting changes, or help choose an export. OpenCV still traces the image, and CadQuery still creates the solids. An LLM does not determine the source part's physical dimensions or certify accuracy.

The workbench's **Next step** guide uses the current inputs and build state without an LLM. You can follow its measurement, settings, preview and export actions without installing Ollama. AI adds optional text advice; it does not inspect the photograph.

There is no paid API, subscription, account, or cloud-model fallback in this integration. You supply the computer resources and download the model weights. “Local” means the machine running the CAD backend; in a cloud environment, inference runs on that cloud host.

## Install and start

The normal `scripts/setup.sh` and GitHub CI do not download Ollama or model weights. Local AI is a separate, optional installation.

On **Linux x86_64**, use the pinned runtime helper from the repository root:

```bash
./scripts/ollama.sh install
./scripts/ollama.sh serve
```

The installer downloads Ollama **0.40.15** from its official GitHub release and verifies the pinned SHA-256 before extraction. It requires `curl`, `sha256sum`, `tar`, and `zstd`. The release archive is approximately 1.54 GB; reserve additional space for the extracted runtime and each selected model.

Keep the server terminal running. In a second terminal:

```bash
./scripts/ollama.sh pull qwen3:1.7b
./scripts/ollama.sh list
```

The starting choice, **Qwen3 1.7B**, is a small text model with an upstream Apache 2.0 weight-license statement. It is a provisional CPU baseline; exact installed size, performance, and answer quality must be measured locally. [Model choices](ollama-models.md) records alternatives and the evidence still needed.

The helper binds Ollama to `127.0.0.1:11434` and sets `OLLAMA_NO_CLOUD=1`. It keeps one model loaded at a time, permits one parallel inference request, and uses an 8,192-token context to accommodate the bounded design and printer information. The application caps generated output at 512 tokens. These limits are configuration choices, not measured inference-performance results. Model weights live under `.local/ollama-models`; the runtime lives under `.local/ollama`. These directories are ignored by Git.

Ollama creates its own identity files under `~/.ollama` on first startup. On a normal machine, that directory must be writable by the current user. A managed sandbox may require its supported filesystem-permission flow for this initial write. No Ollama account or sign-in is required for the local models used here.

For macOS, Windows, or another architecture, install the official [Ollama application](https://ollama.com/download), disable its cloud features, start it on the CAD backend's machine, and use `ollama pull qwen3:1.7b`. The repository helper installs only its pinned Linux x86_64 build. An independently installed Ollama service may use a different model directory; the model picker shows the models in the server the backend actually connects to.

## Use the assistant

1. Open **Local AI assistant** below the workbench controls, then use **Refresh connection** if needed.
2. Choose a downloaded **Local model**. The assistant does not silently install models or switch to a hosted service.
3. Ask a question or choose a starter about tracing, design, printing, measurements, or exports.
4. Select **Ask local AI** and read the answer. A settings proposal shows the previous and suggested values before you apply it.
5. Use **Apply suggestion** only for a change you want to try, inspect the resulting settings and outline, then decide whether to rebuild. **Keep current settings** dismisses a proposal. **Undo suggestion** restores its previous settings without asking the model again. If nothing was built from the suggestion, the existing model already matches the restored settings, so it stays current and exportable. After building a suggestion, undo also restores the prior valid mesh for comparison, or clears the new preview if there was no prior current model. Rebuild before exporting the restored settings because previous server files may have been released. A subsequent edit that invalidates the model clears that undo step.

The assistant can propose supported trace controls, explicit XY/thickness design percentages, relative detail, color/material, printer-volume choices, and split-grid settings. It cannot overwrite the measured reference width or thickness, run generated code, build, or export. A design-scale proposal changes the derived dimensions only after you apply it and rebuild. Changing the project inputs while an answer is pending, or after an unapplied answer arrives, marks that answer outdated, including advice without a settings proposal. An outdated proposal cannot be applied; ask again about the current inputs. Applying a suggestion does not label its own answer outdated merely because Apply changed the settings.

Invalid or inconsistent design fields, such as 0% XY scale or a margin that consumes
the bed, have a visible explanation beside the question and prevent sending it.
Valid settings that request geometry beyond the supported size may
still be discussed: for example, an 800 mm source at 300% XY scale can receive a
proposal to return to 100%. Review and apply that change explicitly; the workbench
checks the resulting size before accepting it. A response never starts a build.

An active CAD operation temporarily blocks asking and applying. While the assistant
is answering, you can keep using the workbench; changes may make its answer
outdated. Undo waits for CAD work or an Apply operation to finish, but a requested
geometry-size error alone does not disable it. The [guided-workbench review](validation/guided-workbench.md#arithmetic-and-ai-reliability)
records fixture-based checks of these controls, not a live model-quality result.

When a two-point feature reference is applied, a reviewed retrace retains its measured length and endpoints but recalculates outside width from the new outline bounds. Undo restores the previous outline, width and reference. This does not change the physical reference or infer a new measurement.

The request includes your question, measured width and thickness when present, trace settings, detected hole count, trace and current-build warnings, design and print settings, and whether an image/model is present. When a current build is available, it can also include the resulting overall and per-part dimensions. Bounded facts from the selected printer's source profile, plus explicitly named printer candidates when relevant, help ground printer advice. Unknown capabilities remain unknown. **No photograph, outline vertices, CAD mesh, or exported file is sent to Ollama.** A text-only response cannot establish that a particular feature is visible or correct. Check its advice against the actual source and part.

For example, a suggestion to use 125% XY scale with an 80 mm measured width proposes a 100 mm-wide design; it does not revise the original measurement. A suggestion to split a large part creates no pieces until you rebuild. Generated splits use straight cuts without joints or assembly tolerances, and geometric bed fit is not a printability guarantee. See [print planning](print-planning.md).

## Manage resources

```bash
./scripts/ollama.sh ps
./scripts/ollama.sh list
./scripts/ollama.sh rm qwen3:1.7b
```

`ps` shows loaded models; `list` shows downloaded models; `rm` deletes the named model's local installation. Stop a server you started with **Ctrl+C** in its terminal. Do not stop an unrelated Ollama service to free the port. The CAD workbench remains usable when the assistant is unavailable.

Small models can still be slow on a CPU, particularly on their first response. Use short questions and compare measured latency before selecting a larger model. Model output is untrusted advice, even when its response has a valid JSON shape.

**Stop waiting** dismisses an active browser request and leaves your CAD inputs unchanged. Ollama may still finish computing that answer, so an immediate new question can receive a busy response. Collapsing the assistant panel leaves its request active. The backend limits chat inference to 120 seconds, plus short model checks.

## Compare models

Download candidates explicitly, check their exact artifact and weight license, and run the repository benchmark against the installed models. It uses the production assistant prompt and response validation with fixed synthetic questions; it does not send your photograph or silently download anything. See [comparison criteria](ollama-models.md) for the intended review.

For example, after the starting model has downloaded successfully:

```bash
.venv/bin/python scripts/benchmark_ollama.py qwen3:1.7b --output .local/ollama-benchmark.json
```

Add further installed model tags as positional arguments to compare up to five models. A completed comparison attempts nine bounded inferences per model: a first request after an explicit unload, a warm repeat of that question, and seven other project-specific cases. Missing models are skipped, and a transport/request failure stops the remaining cases for that model. The cases cover source measurements, tracing, exports, rejected unauthorized changes, reviewed design resizing, material limits, and unknown printer capabilities. Run it when the assistant is idle because unloading a model affects that Ollama server. Each inference has a 120-second timeout by default; `--timeout` accepts 10–180 seconds. The benchmark calls Ollama directly, so the app's chat lock does not serialize it with questions from another workbench tab.

After confirming and downloading all shortlist artifacts, the comparison command is:

```bash
.venv/bin/python scripts/benchmark_ollama.py qwen3:1.7b qwen3.5:2b qwen3.5:4b --output .local/ollama-comparison-new.json
```

The JSON report records raw responses, model metadata and digests, prompt/schema hashes, runtime options, host CPU/cgroup limits, Ollama version, durations, output token rate, and human-review criteria. It does not measure resident model memory. An adjacent Markdown summary makes the results easier to inspect. Exit status 0 means usable response schemas, 1 means a missing model or inference/schema failure, and 2 means the service is unavailable. None is a semantic-quality verdict; review the actual answers before recommending a model.

The benchmark replaces the selected JSON file and adjacent Markdown summary if they already exist, including when a service-unavailable preflight is saved. Choose a fresh destination for each run and preserve earlier reports before repeating it. See the [developer-tool catalog](developer-tools.md) for other local checks and their output rules.

A successful software test with a mocked response verifies integration behavior, not the model's reasoning. A useful model comparison records model digests, runtime settings, cold and warm latency, raw answers, and human review. Do not choose a winner from parameter counts alone.

## Recorded cloud preflight — November 8, 2026

On November 8, 2026, the official Ollama 0.40.15 runtime was downloaded, checksum-verified, and started with cloud features disabled. Its version and empty installed-model list were verified through the local API. The `qwen3:1.7b` pull failed because the managed proxy denied access to `registry.ollama.ai` with `403 Forbidden`.

The [committed preflight report](benchmarks/ollama-preflight.json) records Ollama 0.40.15, all three shortlisted models missing, and **zero inference runs**. Its hardware, prompt hashes and model state describe that recorded environment; they do not establish the current state of another checkout, machine or cloud task.

At that time, a network-settings draft was prepared for `ollama.com` and `registry.ollama.ai`, preserving the previously requested `api.github.com` access. A prepared or saved draft is not proof that the policy was applied. Check the active environment's supported settings and retest the denied host before retrying a download. A weight download may reveal an additional redirected storage hostname; request that specific host through the same supported flow if necessary.

No live inference or comparative-quality result is established by that preflight or by the integration fixtures. A new model recommendation needs a fresh report and reviewed answers on the target machine. Keep TLS verification and the environment proxy configuration intact; a network denial is not an instruction to use an unapproved mirror or tunnel.
