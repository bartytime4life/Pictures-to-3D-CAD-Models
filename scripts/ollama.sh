#!/usr/bin/env bash
# Optional local AI runtime. Model weights and binaries stay out of Git.
set -euo pipefail
PICAD_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PICAD_OLLAMA_VERSION=0.40.15
PICAD_OLLAMA_SHA256=628c018404a4206493efd38e46251c154ede5141b8b8dc85c659b3b027c47379
PICAD_OLLAMA_DIR="$PICAD_ROOT/.local/ollama"
PICAD_OLLAMA_BIN="$PICAD_OLLAMA_DIR/bin/ollama"
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_MODELS="$PICAD_ROOT/.local/ollama-models"
export OLLAMA_NO_CLOUD=1
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_CONTEXT_LENGTH=8192

case "${1:-help}" in
  install)
    if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
      echo 'This pinned installer supports Linux x86_64. Install Ollama from https://ollama.com/download for your platform.' >&2
      exit 1
    fi
    command -v curl >/dev/null
    command -v zstd >/dev/null || { echo 'Install zstd before extracting Ollama.' >&2; exit 1; }
    PICAD_DOWNLOAD_DIR="$PICAD_ROOT/.local/ollama-download"
    PICAD_ARCHIVE="$PICAD_DOWNLOAD_DIR/ollama-linux-amd64.tar.zst"
    mkdir -p "$PICAD_DOWNLOAD_DIR" "$PICAD_OLLAMA_DIR"
    if [[ ! -f "$PICAD_ARCHIVE" ]] || ! printf '%s  %s\n' "$PICAD_OLLAMA_SHA256" "$PICAD_ARCHIVE" | sha256sum --check --status; then
      curl --fail --location --retry 2 --output "$PICAD_ARCHIVE.part" \
        "https://github.com/ollama/ollama/releases/download/v$PICAD_OLLAMA_VERSION/ollama-linux-amd64.tar.zst"
      printf '%s  %s\n' "$PICAD_OLLAMA_SHA256" "$PICAD_ARCHIVE.part" | sha256sum --check
      mv -- "$PICAD_ARCHIVE.part" "$PICAD_ARCHIVE"
    fi
    tar --zstd -xf "$PICAD_ARCHIVE" -C "$PICAD_OLLAMA_DIR"
    echo "Verified Ollama $PICAD_OLLAMA_VERSION installed. Start it with ./scripts/ollama.sh serve."
    ;;
  serve|list|ps)
    [[ -x "$PICAD_OLLAMA_BIN" ]] || { echo 'Run ./scripts/ollama.sh install first.' >&2; exit 1; }
    exec "$PICAD_OLLAMA_BIN" "$1"
    ;;
  pull|rm)
    [[ -x "$PICAD_OLLAMA_BIN" ]] || { echo 'Run ./scripts/ollama.sh install first.' >&2; exit 1; }
    PICAD_MODEL="${2:-}"
    if [[ ! "$PICAD_MODEL" =~ ^[a-zA-Z0-9][a-zA-Z0-9._:/-]*$ || "${PICAD_MODEL,,}" == *cloud* || "$PICAD_MODEL" == *://* ]]; then
      echo 'Provide a local Ollama model tag, for example qwen3:1.7b. Cloud models are not supported.' >&2
      exit 1
    fi
    exec "$PICAD_OLLAMA_BIN" "$1" "$PICAD_MODEL"
    ;;
  *)
    cat <<'HELP'
Optional local AI (no subscription or API key):
  ./scripts/ollama.sh install          Install the verified Linux x86_64 runtime
  ./scripts/ollama.sh serve            Run locally; cloud features disabled
  ./scripts/ollama.sh pull qwen3:1.7b  Download a model while the server runs
  ./scripts/ollama.sh list             List downloaded models
  ./scripts/ollama.sh ps               Show models loaded into memory
  ./scripts/ollama.sh rm MODEL         Remove a downloaded model

Use Ctrl+C in the serve terminal to stop this server. See docs/ollama.md.
HELP
    ;;
esac
