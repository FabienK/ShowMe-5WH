#!/usr/bin/env bash
# Démarre ShowMe-5WH (ComfyUI + backend, et le frontend avec --with-frontend)
# de façon idempotente, depuis n'importe quel dossier :
#   - service déjà lancé et identifié → on passe ;
#   - port occupé par AUTRE CHOSE → message clair et sortie en erreur (on ne
#     démarre jamais par-dessus, et on n'attend pas dans le vide) ;
#   - sinon lancement en arrière-plan (nohup) + attente que le service réponde.
#
# Ports : ComfyUI 8188, backend 8540 (port dédié — 8000 est le défaut de
# `python -m http.server` et d'autres projets, source de collisions),
# frontend 5173.
#
# Usage : scripts/start_showme.sh [--with-frontend]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMFY_PORT=8188
BACKEND_PORT=8540
FRONTEND_PORT=5173
WITH_FRONTEND=0
[[ "${1:-}" == "--with-frontend" ]] && WITH_FRONTEND=1

log()  { printf '%s\n' "$*"; }
fail() { printf 'ERREUR : %s\n' "$*" >&2; exit 1; }

port_listener() {   # pid du processus qui écoute sur le port, vide sinon
  lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | head -n1 || true
}

describe_port() {   # "pid commande" pour un message d'erreur lisible
  local pid; pid="$(port_listener "$1")"
  [[ -n "$pid" ]] && ps -p "$pid" -o pid=,command= | sed 's/^ *//'
}

# --- Identification de chaque service (le port répond ET c'est le bon) ---
comfy_ok()    { curl -sf -m 3 "http://127.0.0.1:$COMFY_PORT/system_stats" >/dev/null 2>&1; }
backend_ok()  { curl -sf -m 3 "http://127.0.0.1:$BACKEND_PORT/api/health" 2>/dev/null | grep -q '"app":"ShowMe-5WH"'; }
frontend_ok() { curl -sf -m 3 "http://127.0.0.1:$FRONTEND_PORT/" 2>/dev/null | grep -qi 'showme'; }

wait_for() {        # wait_for <fonction_test> <nom> <timeout_s>
  local fn="$1" name="$2" timeout="${3:-60}" i=0
  while (( i < timeout )); do
    "$fn" && return 0
    sleep 1; i=$((i+1))
  done
  fail "$name ne répond pas après ${timeout}s (voir le log indiqué ci-dessus)."
}

start_service() {   # start_service <nom> <port> <fonction_test> <dir> <log> <commande...>
  local name="$1" port="$2" fn="$3" dir="$4" logfile="$5"; shift 5
  if "$fn"; then
    log "✓ $name déjà lancé (port $port)."
    return 0
  fi
  if [[ -n "$(port_listener "$port")" ]]; then
    fail "le port $port est occupé par un autre processus, pas par $name :
  $(describe_port "$port")
  → arrêter ce processus, ou le déplacer sur un autre port, puis relancer."
  fi
  log "… démarrage de $name (port $port), log : $logfile"
  ( cd "$dir" && nohup "$@" >>"$logfile" 2>&1 & )
  wait_for "$fn" "$name" 60
  log "✓ $name prêt (port $port)."
}

# 1. ComfyUI
[[ -x "$ROOT/ComfyUI/.venv/bin/python" ]] || fail "ComfyUI/.venv introuvable — voir scripts/install_comfyui.sh"
start_service "ComfyUI" "$COMFY_PORT" comfy_ok "$ROOT/ComfyUI" "$ROOT/ComfyUI/comfyui_run.log" \
  "$ROOT/ComfyUI/.venv/bin/python" main.py --listen 127.0.0.1 --port "$COMFY_PORT"

# 2. Backend FastAPI
[[ -x "$ROOT/backend/.venv/bin/python" ]] || fail "backend/.venv introuvable — voir README.md (Installation > Backend)"
start_service "backend ShowMe" "$BACKEND_PORT" backend_ok "$ROOT/backend" "$ROOT/backend/backend_run.log" \
  "$ROOT/backend/.venv/bin/python" -m uvicorn app.main:app --port "$BACKEND_PORT"

# 3. Frontend (optionnel : inutile pour un usage par API)
if (( WITH_FRONTEND )); then
  start_service "frontend ShowMe" "$FRONTEND_PORT" frontend_ok "$ROOT/frontend" "$ROOT/frontend/frontend_run.log" \
    npm run dev
fi

log ""
log "ShowMe-5WH opérationnel — API : http://127.0.0.1:$BACKEND_PORT/api  (mode d'emploi : $ROOT/AGENT.md)"
