"""Persistance du solde OpenAI estimé — même pattern que batch_store.py
(seul précédent de persistance JSON en lecture/écriture du projet) : écriture
dans un fichier temporaire puis renommage atomique (os.replace), pour ne
jamais laisser un fichier tronqué/corrompu si le process est tué en plein
write().

Contrairement à presets/presets.json (lecture-seule-au-runtime, voir
services/presets.py), ce fichier est réécrit à chaque génération OpenAI
réussie (decrement_balance) et à chaque resynchronisation manuelle
(set_balance, voir routers/openai_settings.py) — d'où son dossier séparé
backend/state/.

Le solde est une estimation locale, jamais interrogée auprès d'OpenAI (voir
openai-fallback-implementation.md) : elle se désynchronise si le compte est
utilisé ou rechargé ailleurs que par cette app."""

import json
import os

from app.config import settings

_DEFAULT_BALANCE_USD = 0.0


def _read_balance() -> float:
    path = settings.openai_state_path
    if not path.exists():
        return _DEFAULT_BALANCE_USD
    return json.loads(path.read_text(encoding="utf-8"))["balance_usd"]


def _write_balance(balance_usd: float) -> None:
    path = settings.openai_state_path
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps({"balance_usd": balance_usd}, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def read_balance() -> float:
    return _read_balance()


def set_balance(balance_usd: float) -> float:
    """Resynchronisation manuelle (l'utilisateur renseigne le solde réel de
    son compte OpenAI après un rechargement)."""
    _write_balance(balance_usd)
    return balance_usd


def decrement_balance(cost_usd: float) -> float:
    """Appelé uniquement après un appel OpenAI réussi (voir
    generation_dispatch.py) — jamais en cas d'erreur."""
    new_balance = _read_balance() - cost_usd
    _write_balance(new_balance)
    return new_balance
