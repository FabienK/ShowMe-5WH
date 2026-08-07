#!/usr/bin/env bash
#
# Installe ComfyUI sur macOS / Apple Silicon (Mac mini M4) avec support MPS.
# À exécuter sur la machine cible (pas dans un environnement cloud) :
#
#   chmod +x scripts/install_comfyui.sh
#   ./scripts/install_comfyui.sh [chemin_installation]
#
# Par défaut, ComfyUI est cloné dans ./ComfyUI à la racine du dépôt.

set -euo pipefail

INSTALL_DIR="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/ComfyUI}"

if [[ "$(uname)" != "Darwin" ]]; then
  echo "Attention : ce script est prévu pour macOS (Apple Silicon). Poursuite quand même." >&2
fi

if ! command -v git &> /dev/null; then
  echo "git est requis. Installez les Command Line Tools (xcode-select --install) puis relancez." >&2
  exit 1
fi

if ! command -v python3 &> /dev/null; then
  echo "python3 est requis (brew install python@3.11 recommandé)." >&2
  exit 1
fi

if [[ -d "$INSTALL_DIR/.git" ]]; then
  echo "ComfyUI est déjà cloné dans $INSTALL_DIR — mise à jour."
  git -C "$INSTALL_DIR" pull --ff-only
else
  echo "Clonage de ComfyUI dans $INSTALL_DIR…"
  git clone https://github.com/comfyanonymous/ComfyUI.git "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

echo "Création de l'environnement virtuel Python (.venv)…"
python3 -m venv .venv
source .venv/bin/activate

echo "Installation de PyTorch avec support MPS (Apple Silicon)…"
pip install --upgrade pip
pip install torch torchvision torchaudio

echo "Installation des dépendances de ComfyUI…"
pip install -r requirements.txt

mkdir -p models/checkpoints models/loras

cat <<EOF

Installation terminée dans : $INSTALL_DIR

Prochaines étapes :
  1. Téléchargez vos checkpoints Stable Diffusion (.safetensors) dans :
       $INSTALL_DIR/models/checkpoints/
     et vos éventuels LoRA dans :
       $INSTALL_DIR/models/loras/
  2. Démarrez ComfyUI :
       cd "$INSTALL_DIR" && source .venv/bin/activate && python main.py
  3. Vérifiez qu'il répond sur http://127.0.0.1:8188 :
       curl http://127.0.0.1:8188/system_stats
  4. Renseignez backend/presets/presets.json avec les noms exacts de vos
     checkpoints/LoRA une fois vos essais faits dans l'interface ComfyUI.

EOF
