#!/usr/bin/env bash
# Optional AI depth model for the relief studio. The weights stay out of Git.
# Depth Anything V2 Small (Apache-2.0), ONNX export by onnx-community, pinned to one
# revision and checked by SHA-256 both here and every time the workbench loads it.
set -euo pipefail
PICAD_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PICAD_DEPTH_REVISION=4472b7362082ad9968fee890ca0f1e5aca36b93d
PICAD_DEPTH_SHA256=afb6a5c28f3b6bf1618c6e43f02073ef9dfdc70e937502d51603e57b0a1df10c
PICAD_DEPTH_URL="https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/$PICAD_DEPTH_REVISION/onnx/model.onnx"
PICAD_DEPTH_FILE="${PICAD_DEPTH_MODEL:-$PICAD_ROOT/.local/depth-model/depth-anything-v2-small.onnx}"

verified() { [[ -f "$1" ]] && printf '%s  %s\n' "$PICAD_DEPTH_SHA256" "$1" | sha256sum --check --status; }

case "${1:-help}" in
  install)
    command -v curl >/dev/null || { echo 'Install curl first.' >&2; exit 1; }
    if verified "$PICAD_DEPTH_FILE"; then
      echo "The verified depth model is already installed at $PICAD_DEPTH_FILE."
      exit 0
    fi
    mkdir -p "$(dirname -- "$PICAD_DEPTH_FILE")"
    echo 'Downloading Depth Anything V2 Small (99 MB, Apache-2.0) from Hugging Face...'
    curl --fail --location --retry 2 --output "$PICAD_DEPTH_FILE.part" "$PICAD_DEPTH_URL"
    printf '%s  %s\n' "$PICAD_DEPTH_SHA256" "$PICAD_DEPTH_FILE.part" | sha256sum --check
    mv -- "$PICAD_DEPTH_FILE.part" "$PICAD_DEPTH_FILE"
    echo "Verified depth model installed. Restart the workbench, then choose Picture type: AI depth."
    ;;
  status)
    if verified "$PICAD_DEPTH_FILE"; then
      echo "Installed and verified: $PICAD_DEPTH_FILE"
    elif [[ -f "$PICAD_DEPTH_FILE" ]]; then
      echo "Present but NOT verified (wrong file or damaged): $PICAD_DEPTH_FILE" >&2
      exit 1
    else
      echo "Not installed. Run ./scripts/depth-model.sh install"
      exit 1
    fi
    ;;
  remove)
    rm -f -- "$PICAD_DEPTH_FILE" "$PICAD_DEPTH_FILE.part"
    echo 'Depth model removed.'
    ;;
  *)
    cat <<'HELP'
Optional AI depth for the relief studio (runs on this computer's CPU, no account or key):
  ./scripts/depth-model.sh install   Download and verify the 99 MB model
  ./scripts/depth-model.sh status    Check that the installed file is the verified one
  ./scripts/depth-model.sh remove    Delete the model

Set PICAD_DEPTH_MODEL=/path/to/file.onnx to keep it elsewhere. See docs/relief.md.
HELP
    ;;
esac
