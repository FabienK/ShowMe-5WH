#!/usr/bin/env bash
# Arrête les processus ShowMe-5WH (backend, frontend, et ComfyUI avec --all),
# identifiés par leur ligne de commande — jamais un autre serveur qui
# occuperait le même port.
#
# Usage : scripts/stop_showme.sh [--all]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

kill_matching() {   # kill_matching <nom> <motif pgrep -f>
  local name="$1" pattern="$2" pids
  pids="$(pgrep -f "$pattern" || true)"
  if [[ -z "$pids" ]]; then
    printf '· %s : pas lancé.\n' "$name"
    return 0
  fi
  kill $pids 2>/dev/null || true
  sleep 1
  pgrep -f "$pattern" >/dev/null && kill -9 $pids 2>/dev/null || true
  printf '✓ %s arrêté (pid %s).\n' "$name" "$(echo $pids | tr '\n' ' ')"
}

kill_matching "backend ShowMe"  "uvicorn app\.main:app --port 8540"
kill_matching "frontend ShowMe" "vite.*--port 5173|$ROOT/frontend/node_modules/.bin/vite"
if [[ "${1:-}" == "--all" ]]; then
  kill_matching "ComfyUI" "main\.py --listen 127\.0\.0\.1 --port 8188"
fi
