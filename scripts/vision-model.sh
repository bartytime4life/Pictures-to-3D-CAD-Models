#!/usr/bin/env bash
# Optional DINOv3 vision model for the photo library. Nothing here is part of setup.
#
# DINOv3's code and weights are released under Meta's DINOv3 License, and the weights
# are only handed out after a request form. This script never downloads weights. It
#   1. builds a separate Python environment (.local/vision-env) with PyTorch and the
#      DINOv3 code at one pinned commit, and
#   2. links weight files YOU obtained from Meta into .local/vision-model, after
#      checking each against the SHA-256 pinned here and in backend/vision.py.
# The workbench checks every file again before each load.
set -euo pipefail
PICAD_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PICAD_ROOT"
PICAD_DINOV3_COMMIT=6876159a11b4df116f30f667f8c9888617df0751
PICAD_VISION_ENV="$PICAD_ROOT/.local/vision-env"
PICAD_VISION_DIR="${PICAD_VISION_WEIGHTS:-$PICAD_ROOT/.local/vision-model}"
PICAD_REQUEST_URL='https://ai.meta.com/resources/models-and-libraries/dinov3-downloads/'
# file name, SHA-256, short name. The same table as MODELS in backend/vision.py.
PICAD_WEIGHTS=(
  'dinov3_vitb16_pretrain_lvd1689m-73cec8be.pth 73cec8be7427c8655ceced13ce62f6e20a1fa90d1b4d4a550df17a1144081a7c ViT-B/16'
  'dinov3_vitl16_pretrain_lvd1689m-8aa4cbdd.pth 8aa4cbddda325040fc78db2c272754af6ebe8ff2c55f6ec4f1964d8890f66035 ViT-L/16'
  'dinov3_vits16plus_pretrain_lvd1689m-4057cbaa.pth 4057cbaaad8c16657adb09d6815f28d4164eeba30532fde23f0d17313124caea ViT-S+/16'
  'dinov3_vits16_pretrain_lvd1689m-08c60483.pth 08c60483bc63c04f533611e34bf70b120eedb7240f469bc16e9e20bf344b941d ViT-S/16'
)

verified() { [[ -f "$1" ]] && printf '%s  %s\n' "$2" "$1" | sha256sum --check --status; }

installed_count() {
  local count=0 entry file sha name
  for entry in "${PICAD_WEIGHTS[@]}"; do
    read -r file sha name <<<"$entry"
    if verified "$PICAD_VISION_DIR/$file" "$sha"; then count=$((count + 1)); fi
  done
  echo "$count"
}

link_weights() {
  local source="$1" linked=0 entry file sha name
  [[ -d "$source" ]] || { echo "Not a folder: $source" >&2; exit 1; }
  source="$(cd -- "$source" && pwd)"
  mkdir -p "$PICAD_VISION_DIR"
  for entry in "${PICAD_WEIGHTS[@]}"; do
    read -r file sha name <<<"$entry"
    [[ -f "$source/$file" ]] || continue
    echo "Checking DINOv3 $name ..."
    if verified "$source/$file" "$sha"; then
      if [[ "$source" != "$(cd -- "$PICAD_VISION_DIR" && pwd)" ]]; then ln -sfn -- "$source/$file" "$PICAD_VISION_DIR/$file"; fi
      echo "  verified and linked."
      linked=$((linked + 1))
    else
      echo "  NOT linked: $file does not match its SHA-256 (damaged or a different file)." >&2
    fi
  done
  if [[ "$linked" -eq 0 ]]; then
    echo "No DINOv3 ViT weight file (LVD-1689M: ViT-S, S+, B or L) was found in $source." >&2
    exit 1
  fi
}

find_uv() {
  if command -v uv >/dev/null; then command -v uv
  elif [[ -x "$PICAD_ROOT/.local/uv-bootstrap/bin/uv" ]]; then echo "$PICAD_ROOT/.local/uv-bootstrap/bin/uv"
  else echo 'Run ./scripts/setup.sh first: it provides uv.' >&2; exit 1
  fi
}

case "${1:-help}" in
  install)
    shift
    PICAD_SOURCE=''
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --weights) PICAD_SOURCE="${2:?--weights needs a folder}"; shift 2 ;;
        --weights=*) PICAD_SOURCE="${1#--weights=}"; shift ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
      esac
    done
    command -v git >/dev/null || { echo 'Install git first (the DINOv3 code is installed from its repository).' >&2; exit 1; }
    PICAD_UV="$(find_uv)"
    export UV_CACHE_DIR="$PICAD_ROOT/.cache/uv"
    export UV_SYSTEM_CERTS=true
    cat <<NOTICE
DINOv3 is released by Meta under the DINOv3 License, which is not an open-source licence:
  https://github.com/facebookresearch/dinov3/blob/main/LICENSE.md
Installing it means you accept that licence. Nothing is downloaded from Meta's weight
servers; PyTorch (several GB) and the DINOv3 code (commit ${PICAD_DINOV3_COMMIT:0:12}) are installed
into $PICAD_VISION_ENV.
NOTICE
    if [[ ! -x "$PICAD_VISION_ENV/bin/python" ]]; then
      "$PICAD_UV" venv --python "${PICAD_PYTHON:-3.12}" "$PICAD_VISION_ENV"
    fi
    "$PICAD_UV" pip install --python "$PICAD_VISION_ENV/bin/python" 'torch>=2.7,<3' 'numpy>=1.26,<3' 'pillow>=10,<14'
    "$PICAD_UV" pip install --python "$PICAD_VISION_ENV/bin/python" --no-deps \
      "dinov3 @ git+https://github.com/facebookresearch/dinov3@$PICAD_DINOV3_COMMIT"
    if [[ -n "$PICAD_SOURCE" ]]; then link_weights "$PICAD_SOURCE"; fi
    if [[ "$(installed_count)" -eq 0 ]]; then
      cat <<HELP

The environment is ready, but no weight file is installed yet.
  1. Request the DINOv3 weights from Meta: $PICAD_REQUEST_URL
  2. Download a ViT backbone trained on LVD-1689M. ViT-B/16 (343 MB) is the recommended
     one with a graphics card; ViT-S/16 (87 MB) without.
  3. Run: ./scripts/vision-model.sh install --weights /folder/with/the/pth/files
HELP
      exit 0
    fi
    echo 'Starting the model once to check it ...'
    "$PICAD_ROOT/.venv/bin/python" - <<'CHECK'
from backend import vision
hello = vision.engine.start()
vision.engine.close()
name = vision.MODELS[hello["model"]]["name"]
print(f"Ready: {name} on {hello['device_name']} ({hello['precision']}, {hello['runtime']}).")
CHECK
    echo 'Restart the workbench, open Library, and crunch a folder.'
    ;;
  status)
    if [[ -x "$PICAD_VISION_ENV/bin/python" ]]; then echo "Environment: $PICAD_VISION_ENV"; else echo 'Environment: not installed'; fi
    for entry in "${PICAD_WEIGHTS[@]}"; do
      read -r file sha name <<<"$entry"
      if verified "$PICAD_VISION_DIR/$file" "$sha"; then echo "DINOv3 $name: installed and verified"
      elif [[ -e "$PICAD_VISION_DIR/$file" ]]; then echo "DINOv3 $name: present but NOT verified (wrong or damaged file)"
      else echo "DINOv3 $name: not installed"
      fi
    done
    [[ -x "$PICAD_VISION_ENV/bin/python" && "$(installed_count)" -gt 0 ]] || exit 1
    ;;
  remove)
    rm -rf -- "$PICAD_VISION_ENV"
    # Only this script's links and the worker's log are removed; your downloaded files stay where they are.
    for entry in "${PICAD_WEIGHTS[@]}"; do
      read -r file sha name <<<"$entry"
      if [[ -L "$PICAD_VISION_DIR/$file" ]]; then rm -f -- "$PICAD_VISION_DIR/$file"; fi
    done
    rm -f -- "$PICAD_ROOT/.local/vision-model/worker.log"
    echo 'Vision environment and weight links removed. Weight files you downloaded were not deleted.'
    ;;
  *)
    cat <<HELP
Optional DINOv3 vision model for the photo library (runs on this computer, no account or key):
  ./scripts/vision-model.sh install [--weights FOLDER]   Build the environment; link verified weights from FOLDER
  ./scripts/vision-model.sh status                        Show what is installed and verified
  ./scripts/vision-model.sh remove                        Delete the environment and the weight links

Weights are not downloaded for you: request them from Meta at
  $PICAD_REQUEST_URL
Set PICAD_VISION_WEIGHTS=/folder to read weights from another folder, PICAD_VISION_PYTHON to
use another environment's Python, PICAD_VISION_MODEL to force one model. See docs/photo-library.md.
HELP
    ;;
esac
