# Creative tools and local AI

The **Creative tools** studio (`#creative`) is a place to explore an idea before modeling it. It uses the existing visual system and keeps drafts and generated notes when you switch studios.

1. Choose **Explore directions**, **Refine an idea**, or **Plan the making**.
2. Describe what you want to make and add any constraints. Use actual measurements when you have them; otherwise say what is still unknown.
3. Choose an installed local chat model and select **Generate creative notes**.
4. Review the directions and next steps. **Save notes** downloads JSON containing the submitted brief, constraints, tool ID, model, result, warnings and elapsed time.
5. Use **Your creative toolkit** to search and filter workspaces, then open the appropriate making tool.

The notes are conceptual text. They do not generate images, meshes, toolpaths or verified dimensions. Editing a brief marks earlier notes as belonging to the previous input; exporting those notes retains the original input. Drafts are retained in memory during navigation, not across reloads. Save notes before closing the page. The export is currently a portable record, not an importable CAD recipe.

**Stop waiting** cancels the browser request. Inference may continue on the server until its bounded deadline. All creative tools and the flat-part assistant share one inference slot; a busy response asks you to wait before trying again. Leaving the studio preserves the pending request and draft, and its result does not move focus out of another studio.

## Which AI runs where?

| Capability | Runtime | Requirements |
| --- | --- | --- |
| Creative directions, critique and making plans | Ollama, local text generation | An installed model reporting `completion` capability |
| Flat-part settings advice | Same Ollama connection and inference slot | Same chat models; settings proposals still require review and Apply |
| Estimated photo depth | Dedicated depth worker | Separately installed, hash-verified depth weights; see [Relief](relief.md#ai-depth-from-an-ordinary-photo) |
| Photo similarity and subject features | Dedicated DINOv3 worker | Separately obtained vision weights; see [Photo library](photo-library.md#optional-vision-model) |
| Tracing, measured CAD, basic relief, Knowledge and Science | Existing local code | No language model required |

A vision-capable Ollama model can be used for text, but this studio sends no image input. Embedding-only models are excluded from the chat picker. Ollama is not a replacement for the specialized depth or DINOv3 workers.

## Connection and verification

The app connects from its backend to `http://127.0.0.1:11434` by default. `PICTURES_CAD_OLLAMA_URL` accepts only HTTP loopback addresses. `PICTURES_CAD_OLLAMA_MODEL` sets the preferred installed chat model; the default remains the small `qwen3:1.7b` baseline. You can select another model in the interface.

```bash
./scripts/ollama.sh list
./scripts/ollama.sh check
# Optional: four synthetic requests, using production validation, no downloads.
./scripts/ollama.sh check --probe --model qwen3:8b --output .local/verification/ai.json
```

The helper uses the system Ollama CLI first and falls back to a repository install. Set `PICAD_OLLAMA_BIN` to an executable path to choose explicitly. Repository installs retain their `.local/ollama-models` directory; system installs retain their configured store. Do not start another server if one is already running. See [Ollama setup](ollama.md) for installation and local-only server settings.

`check` performs metadata requests, not inference. `--probe` runs the assistant and each registered creative tool with synthetic text and validates their responses. Its exit status is 0 for readiness (or completed probes when requested), 1 for unavailable models or failed inference. The receipt distinguishes readiness from inference verification and records the check time, Ollama version and installed model metadata/digests. Valid output shape is not a design-quality or manufacturing-accuracy verdict. Run probes when the application is idle: CLI probes do not acquire the web server's in-process lock.

## Adding a workspace

`frontend/src/studioCatalog.ts` owns route IDs, labels, titles, descriptions, keywords, categories and AI requirements. The header, command launcher, document titles and toolkit search all use it. Register the component in the typed `studios` map in `main.tsx` and its icon in `AppHeader.tsx`; TypeScript checks that each catalog ID has a component and icon. Keep the mounted route and `StudioActivity` pattern so navigation preserves unfinished work and hidden studios do not capture focus.

## Adding a creative text tool

Add a definition to `backend/creative.py`'s `TOOLS` registry, including an ID, label, description, example and application-owned instruction. The interface discovers definitions through `GET /api/creative/tools`. Each uses `POST /api/creative/run` with `model`, `tool`, `brief` (up to 2,400 characters), and optional `constraints` (up to 1,600). Unknown tool IDs and extra request fields are refused.

When a brief supplies no dimensional values, the runner rejects generated notes containing numerical dimensions in the supported mm/cm/inch unit forms. This catches a common invented-size failure; it is not a general semantic or engineering validator. Its prompt names the actual Shape designer operations and directs through-hole work to cutouts rather than Relief.

The common runner verifies installed local weights and completion capability immediately before inference, sends JSON-constrained text, validates the result with Pydantic, and refuses tool calls, truncated output and malformed notes. It retains the existing 120-second inference deadline, an 8,192-token context and a 1,200-token creative output cap. The browser has a 135-second deadline. New tool types that need images, embeddings, geometry mutation or executable code require a separate reviewed input/output contract; do not put executable plugins or arbitrary endpoints into this registry.

Official references: [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs) and [local operation, context and GPU checks](https://docs.ollama.com/faq).
