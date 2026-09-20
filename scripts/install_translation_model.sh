#!/usr/bin/env bash
#
# Télécharge et installe le modèle de traduction français -> anglais
# (Argos Translate) utilisé pour le texte libre (voir
# backend/app/services/translation.py). À exécuter une seule fois — le
# modèle est ensuite mis en cache localement (~/.local/share/argos-translate)
# et la traduction fonctionne hors ligne.
#
#   chmod +x scripts/install_translation_model.sh
#   ./scripts/install_translation_model.sh

set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/backend"

if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
  echo "Environnement virtuel backend introuvable ($BACKEND_DIR/.venv)." >&2
  echo "Installez d'abord le backend (voir README.md, section Installation)." >&2
  exit 1
fi

source "$BACKEND_DIR/.venv/bin/activate"

echo "Installation des dépendances backend (argostranslate inclus)…"
pip install -r "$BACKEND_DIR/requirements.txt"

echo "Téléchargement du modèle de traduction français -> anglais…"
# SSL_CERT_FILE : les builds Python python.org n'embarquent pas toujours un
# magasin de certificats racine par défaut (macOS) ; on réutilise celui de
# certifi (déjà une dépendance de httpx) pour éviter un échec SSL ici.
SSL_CERT_FILE="$(python3 -c 'import certifi; print(certifi.where())')"
export SSL_CERT_FILE
python3 - <<'PYEOF'
import argostranslate.package

argostranslate.package.update_package_index()
available = argostranslate.package.get_available_packages()
package = next(p for p in available if p.from_code == "fr" and p.to_code == "en")
path = package.download()
argostranslate.package.install_from_path(path)
print("Modèle fr -> en installé.")
PYEOF

cat <<EOF

Installation terminée. Le texte libre saisi dans l'app sera désormais
traduit en anglais avant l'envoi à ComfyUI (voir backend/app/services/translation.py).
Si ce script n'a jamais été exécuté, l'app continue de fonctionner : le texte
libre est envoyé tel quel (non traduit), avec un avertissement dans les logs
backend.

EOF
