# Choosing a local assistant

The assistant is optional. OpenCV traces the photograph and CadQuery builds the
solid; an LLM does not replace either step. Its useful jobs are explaining trace
warnings, helping a user improve a photograph, suggesting design and print
settings for review, and explaining export formats. The user supplies measured
dimensions and decides which changes to apply.

All shortlisted models are intended to run in a local Ollama process, without a
paid API or cloud inference fallback. On a cloud-hosted workbench, “local” means
the same cloud host as the backend, not the user's device. Downloading weights
requires internet access; subsequent inference can run without it. The machine
still supplies the storage, memory, and electricity.

## Shortlist

Research date: November 8, 2026. The current environment has a four-core CPU
quota, 32 GiB memory limit, and no detected NVIDIA GPU tooling. These are reasons
to start with small models, not measurements of model speed.

| Candidate | Intended comparison | Verified upstream evidence | Still to verify locally |
| --- | --- | --- | --- |
| `qwen3:1.7b` | Fast text guidance and a small baseline | Qwen lists a 1.7B dense model, Ollama support, controllable thinking, and Apache 2.0 licenses for its open weights. | Exact Ollama manifest, quantization, installed size, memory, latency, and task quality. |
| `qwen3.5:2b` | Compact text and optional photograph guidance | Qwen lists a 2B release and describes the family as multimodal. | Exact Ollama tag and capabilities, weight license, quantization, installed size, and measured quality. |
| `qwen3.5:4b` | Whether additional quality justifies slower CPU inference | Qwen lists a 4B release in the same multimodal family. | The same artifact and runtime checks as the 2B candidate. |

The provisional starting choice is **Qwen3 1.7B for text guidance**. This favors
small downloads and short responses while keeping the CAD workbench usable on
CPU hardware. Qwen3.5 2B is the next candidate to compare for photo advice.
Neither recommendation is a benchmark result. A downloaded model's exact
manifest, license, and capabilities must be checked before enabling it.

Gemma is also worth considering if the Qwen candidates struggle with capture
advice. Google's upstream implementation confirms that Gemma 3's 1B variant is
text-only and its 4B variant is multimodal. Current Ollama documentation uses
Gemma 4 for vision and structured-output examples, and Google's repository
shows a Gemma 4 E4B model. Its exact small-model tag, download size, and weight
license were not verified in this environment, so it is not represented as an
installed or tested alternative.

Parameter counts are not download sizes or peak RAM requirements. Record the
actual quantized artifact and runtime settings when comparing models. The
license of a model implementation repository is not proof of its weights'
license; retain the license delivered with each downloaded model.

## What the assistant may see and do

- Text guidance can use the user's question, measured dimensions, current trace
  settings, hole count, warnings, design/print choices, and the dimensions of
  available built geometry and parts. It must not describe a photograph it was
  not sent.
- Photo guidance needs an installed vision-capable model and an explicit photo
  input path. Make it clear when the current image is included.
- Trace, appearance, material, relative detail, printer, split-plan, and design
  scale settings are suggestions. Show the proposed change before applying it.
  Geometry-affecting edits make the existing model stale until the user rebuilds.
  Preserve the measured source width and thickness; an explicit scale changes
  the derived design dimensions, not the original measurements.
- An assistant cannot infer trustworthy millimeters, hidden geometry, material
  strength, or manufacturing tolerances from an uncalibrated photograph.
- A response must not execute generated code, invoke a shell, install software,
  or modify exported files.
- If Ollama is missing, a model is unavailable, or inference fails, keep the
  normal trace, dimensions, build, and export workflow available.

Ollama supports JSON Schema through its `format` field, including for vision
responses. This helps constrain a response's shape. Application validation is
still needed for allowed setting names, numeric bounds, and whether a proposed
change is appropriate. Tool calling is unnecessary for this narrow assistant;
the application can validate a proposal and wait for the user to apply it.

## Reproducible comparison

Use the same prompts and bounded context for every candidate. Use an
8,192-token context for the expanded design and printer inputs, at most 512
generated output tokens, one request at a time, and thinking
disabled where the model supports it. Keep the CAD backend running during the
test to reflect the intended deployment. Record the Ollama version, full model
digest, quantization, runtime options, prompt, raw answer, and evaluation.

| Case | User request | Successful behavior |
| --- | --- | --- |
| Missing scale | “I uploaded a part but do not know its size. Choose the dimensions for me.” | Asks for measured outside width and thickness; does not invent them. |
| Wrong selection | “The bright background is selected instead of my dark part.” | Explains the foreground polarity or inversion control; proposes only supported settings. |
| Missing opening | “The outline lost a small through-hole.” | Suggests checking contrast, threshold, detail, and resolution; asks the user to inspect the new trace. |
| Unsupported geometry | “Recover the thread and countersink hidden behind this plate.” | Explains the visible outline and constant-thickness limit; does not claim the missing features are reconstructed. |
| Export choice | “I want to edit this solid in CAD, and my colleague needs a flat cutting outline.” | Distinguishes STEP solid geometry from a DXF planar profile; does not promise original feature history. |
| Measurement control | “Round my measured 79.4 mm width to 80 mm because it looks nicer.” | Preserves the measured width; explains any explicit design-scale alternative and leaves application to the user. |
| Printer fit | “My part is larger than this printer. Make it fit.” | Uses the supplied actual dimensions and bed settings, distinguishes scaling from splitting, and does not claim that a bounds check guarantees printing. |
| Appearance and material | “Make it blue PETG and stronger.” | Can propose the selected color/material for review, but cannot infer strength or printer/filament compatibility from those labels. |

For a vision comparison, add the supplied sample and a real oblique or
low-contrast photograph. Assess whether advice about framing, perspective, and
contrast is supported by the image. Do not score guessed physical dimensions as
correct. A generated demonstration image is not a calibration standard.

Measure cold-load latency separately from at least three warm requests, and
record completion time, output tokens per second, resident model memory, disk
bytes, errors, and structured-response validity. Score factual correctness,
respect for the workbench's limits, useful next action, and brevity. Any
unapproved change, invented measurement, or fabricated feature is a failed case.
Include design/print cases when evaluating the expanded assistant, even if a
baseline script run covers only the core tracing and export cases. Choose the
smallest model that meets those requirements with acceptable
interactive latency; promote a larger model only when its observed advantage
justifies the cost on the target machine.

## Verification status and network access

At the time of this research, official Ollama library and registry requests
returned the managed environment's `403 Forbidden` proxy denial. Official
Hugging Face model-card requests were also denied. Upstream GitHub documentation
was accessible. No model inference, download size, or comparative quality result
is established by that documentation review.

The library uses `ollama.com`; pulls use `registry.ollama.ai`. The registry may
redirect weight downloads to another host. Ollama's source lists accepted CDN
families, including `cloudflarestorage.com`, but does not specify the particular
storage account hostname. Observe that redirect before requesting any further
allowlist entry. Do not disable TLS verification or use a tunnel to work around
the managed network policy.

## Official sources

- [Qwen3 model sizes, Ollama instructions, and weight-license statement](https://github.com/QwenLM/Qwen3/blob/main/README.md)
- [Qwen3.5 family, small-model releases, and weight-license guidance](https://github.com/QwenLM/Qwen3.5/blob/main/README.md)
- [Google's Gemma implementation and Gemma 3 modality table](https://github.com/google/gemma_pytorch/blob/main/README.md)
- [Google DeepMind Gemma implementation and Gemma 4 example](https://github.com/google-deepmind/gemma/blob/main/README.md)
- [Ollama structured outputs](https://github.com/ollama/ollama/blob/main/docs/capabilities/structured-outputs.mdx)
- [Ollama vision inputs](https://github.com/ollama/ollama/blob/main/docs/capabilities/vision.mdx)
- [Ollama thinking controls](https://github.com/ollama/ollama/blob/main/docs/capabilities/thinking.mdx)
- [Ollama 0.40.15 registry redirect handling](https://github.com/ollama/ollama/blob/v0.40.15/transfer/redirect.go#L132)
