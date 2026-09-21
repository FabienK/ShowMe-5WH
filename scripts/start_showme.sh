#!/usr/bin/env bash
# Démarre ShowMe-5WH (ComfyUI + backend, et le frontend avec --with-frontend)
# de façon idempotente, depuis n'importe quel dossier :
#   - service déjà lancé et identifié → on passe ;
#   - port occupé par AUTRE CHOSE → message clair et sortie en erreur (on ne
#     démarre jamais par-dessus, et on n'attend pas dans le vide) ;
#   - sinon lancement détaché (nohup, aucun shell résiduel) + attente que le
#     service réponde.
#
# ComfyUI est un service partagé entre projets (ShowMe, Blog…) : il peut avoir
# été lancé d'ailleurs, ou avant un déplacement de dossier — il répond alors
# sur le port mais ses chemins de modèles sont périmés (nœuds de chargement en
# erreur). Le script ne se contente donc pas de « le port répond » : il vérifie
# que le processus tourne depuis $ROOT/ComfyUI et que CheckpointLoaderSimple
# voit bien le checkpoint de référence. Sinon, si aucune génération n'est en
# cours, il le remplace ; s'il est occupé, il refuse et le dit.
#
# Ports : ComfyUI 8188, backend 8540 (port dédié — 8000 est le défaut de
# `python -m http.server` et d'autres projets, source de collisions),
# frontend 5173.
#
# Usage : scripts/start_showme.sh [--with-frontend] [--restart-comfyui]
#   --restart-comfyui : arrête et relance ComfyUI même s'il paraît sain
#                       (refusé si une génération est en cours).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
COMFY_PORT=8188
BACKEND_PORT=8540
FRONTEND_PORT=5173
COMFY_DIR="$ROOT/ComfyUI"
COMFY_REF_CKPT="sd_xl_base_1.0.safetensors"   # checkpoint du preset sdxl_default (backend/presets/presets.json)
WITH_FRONTEND=0
RESTART_COMFY=0
for arg in "$@"; do
  case "$arg" in
    --with-frontend)   WITH_FRONTEND=1 ;;
    --restart-comfyui) RESTART_COMFY=1 ;;
    *) printf 'ERREUR : option inconnue %s\n' "$arg" >&2; exit 2 ;;
  esac
done

log()  { printf '%s\n' "$*"; }
fail() { printf 'ERREUR : %s\n' "$*" >&2; exit 1; }

port_listener() {   # pid du processus qui écoute sur le port, vide sinon
  lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | head -n1 || true
}

describe_port() {   # "pid commande" pour un message d'erreur lisible
  local pid; pid="$(port_listener "$1")"
  [[ -n "$pid" ]] && ps -p "$pid" -o pid=,command= | sed 's/^ *//'
}

proc_cwd() {        # dossier de travail d'un pid (chemin actuel, même si le dossier a été déplacé)
  lsof -p "$1" -a -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n1
}

# --- Identification de chaque service (le port répond ET c'est le bon) ---
comfy_ok()       { curl -sf -m 3 "http://127.0.0.1:$COMFY_PORT/system_stats" >/dev/null 2>&1; }
comfy_nodes_ok() {  # les nœuds de chargement fonctionnent et voient les modèles de ShowMe
  curl -sf -m 15 "http://127.0.0.1:$COMFY_PORT/object_info/CheckpointLoaderSimple" 2>/dev/null \
    | grep -q "\"$COMFY_REF_CKPT\""
}
comfy_healthy()  { comfy_ok && comfy_nodes_ok; }
backend_ok()     { curl -sf -m 3 "http://127.0.0.1:$BACKEND_PORT/api/health" 2>/dev/null | grep -q '"app":"ShowMe-5WH"'; }
frontend_ok()    { curl -sf -m 3 "http://127.0.0.1:$FRONTEND_PORT/" 2>/dev/null | grep -qi 'showme'; }

comfy_diagnose() {  # affiche pourquoi le ComfyUI (pid $1) est inutilisable ; rien s'il est sain
  local pid="$1" cwd
  cwd="$(proc_cwd "$pid")"
  if [[ "$cwd" != "$COMFY_DIR" ]]; then
    printf 'lancé depuis %s (attendu : %s)\n' "${cwd:-?}" "$COMFY_DIR"
  fi
  if ! comfy_nodes_ok; then
    printf 'CheckpointLoaderSimple en erreur ou %s invisible (chemins de modèles périmés ?)\n' "$COMFY_REF_CKPT"
  fi
}

comfy_busy() {      # une génération est en cours, tous appelants confondus (ShowMe, Blog…)
  curl -sf -m 3 "http://127.0.0.1:$BACKEND_PORT/api/status" 2>/dev/null | grep -q '"busy":true' && return 0
  curl -sf -m 3 "http://127.0.0.1:$COMFY_PORT/prompt" 2>/dev/null | grep -qv '"queue_remaining": 0'
}

stop_pid() {        # stop_pid <pid> <nom> : SIGTERM, puis SIGKILL après 5 s
  local pid="$1" name="$2" i=0
  kill "$pid" 2>/dev/null || true
  while kill -0 "$pid" 2>/dev/null && (( i < 5 )); do sleep 1; i=$((i+1)); done
  kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
  i=0
  while kill -0 "$pid" 2>/dev/null && (( i < 5 )); do sleep 1; i=$((i+1)); done
  kill -0 "$pid" 2>/dev/null && fail "$name (pid $pid) ne s'arrête pas."
  log "✓ $name arrêté (pid $pid)."
}

wait_for() {        # wait_for <fonction_test> <nom> <timeout_s>
  local fn="$1" name="$2" timeout="${3:-60}" i=0
  while (( i < timeout )); do
    "$fn" && return 0
    sleep 1; i=$((i+1))
  done
  fail "$name ne répond pas après ${timeout}s (voir le log indiqué ci-dessus)."
}

launch() {          # launch <nom> <port> <fonction_test> <timeout_s> <dir> <log> <commande...>
  local name="$1" port="$2" fn="$3" timeout="$4" dir="$5" logfile="$6"; shift 6
  log "… démarrage de $name (port $port), log : $logfile"
  # exec : le sous-shell devient le service (aucun bash résiduel), stdin/stdout/stderr
  # détachés du script → le processus est rattaché à launchd à la fin du script.
  ( cd "$dir" && exec nohup "$@" </dev/null >>"$logfile" 2>&1 ) &
  disown
  wait_for "$fn" "$name" "$timeout"
  log "✓ $name prêt (port $port)."
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
  launch "$name" "$port" "$fn" 60 "$dir" "$logfile" "$@"
}

ensure_comfyui() {  # ComfyUI : sain → on garde ; périmé ou --restart-comfyui → remplacé si libre
  local pid reason
  pid="$(port_listener "$COMFY_PORT")"
  if [[ -n "$pid" ]]; then
    comfy_ok || fail "le port $COMFY_PORT est occupé par un autre processus, pas par ComfyUI :
  $(describe_port "$COMFY_PORT")
  → arrêter ce processus, ou le déplacer sur un autre port, puis relancer."
    if (( RESTART_COMFY )); then
      reason="relance demandée (--restart-comfyui)"
    else
      reason="$(comfy_diagnose "$pid")"
    fi
    if [[ -z "$reason" ]]; then
      log "✓ ComfyUI déjà lancé (port $COMFY_PORT, pid $pid, modèles visibles)."
      return 0
    fi
    log "ComfyUI à remplacer (pid $pid, lancé le $(ps -o lstart= -p "$pid" | sed 's/^ *//; s/ *$//')) :"
    printf '%s\n' "$reason" | sed 's/^/  - /'
    comfy_busy && fail "une génération est en cours sur ce ComfyUI — relancer quand elle sera finie (curl http://127.0.0.1:$BACKEND_PORT/api/status)."
    stop_pid "$pid" "ComfyUI"
  fi
  launch "ComfyUI" "$COMFY_PORT" comfy_healthy 120 "$COMFY_DIR" "$COMFY_DIR/comfyui_run.log" \
    "$COMFY_DIR/.venv/bin/python" main.py --listen 127.0.0.1 --port "$COMFY_PORT"
}

# 1. ComfyUI
[[ -x "$COMFY_DIR/.venv/bin/python" ]] || fail "ComfyUI/.venv introuvable — voir scripts/install_comfyui.sh"
ensure_comfyui

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
