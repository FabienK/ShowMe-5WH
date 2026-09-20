"""Verrou global de génération + état d'activité exposé par GET /api/status.

Pourquoi : ComfyUI ne traite qu'un job à la fois et le backend n'avait aucun
verrou — deux /api/generate concurrents (deux agents, ou un agent + un batch)
partaient tous deux vers ComfyUI, qui les sérialisait, mais le second voyait
son timeout courir pendant qu'il attendait derrière le premier → faux 504
comfyui_timeout alors que l'image sortait plus tard dans le vide.

Ici : une seule génération à la fois (asyncio.Lock), les autres attendent
leur tour, et le timeout ComfyUI ne démarre qu'une fois le verrou acquis. Le
moteur OpenAI (cloud) passe aussi par le verrou pour rester simple : une
génération = une place, quel que soit le moteur.

Le verrou est créé paresseusement (pas à l'import) : un asyncio.Lock se lie
à la boucle qui le fait attendre la première fois, et les tests créent une
boucle par TestClient — voir reset() et la fixture autouse de conftest.py."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator, Literal

from pydantic import BaseModel, ConfigDict

JobSource = Literal["generate", "batch"]


class CurrentJob(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: str
    source: JobSource
    batch_id: str | None = None
    started_at: str


_lock: asyncio.Lock | None = None
_waiting: int = 0
_current: CurrentJob | None = None


def _get_lock() -> asyncio.Lock:
    global _lock
    if _lock is None:
        _lock = asyncio.Lock()
    return _lock


def is_busy() -> bool:
    return _lock is not None and _lock.locked()


def waiting_count() -> int:
    return _waiting


def current_job() -> CurrentJob | None:
    return _current


def reset() -> None:
    """Réservé aux tests (nouvelle boucle asyncio par TestClient)."""
    global _lock, _waiting, _current
    _lock, _waiting, _current = None, 0, None


@asynccontextmanager
async def generation_slot(
    model_id: str, source: JobSource, batch_id: str | None = None
) -> AsyncIterator[None]:
    """À utiliser autour de chaque génération : attend son tour, puis marque
    le job courant le temps de la génération."""
    global _waiting, _current
    lock = _get_lock()
    _waiting += 1
    try:
        await lock.acquire()
    finally:
        # Décrémenté même si l'attente est annulée (client parti avant son tour).
        _waiting -= 1
    try:
        _current = CurrentJob(
            model_id=model_id,
            source=source,
            batch_id=batch_id,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        yield
    finally:
        _current = None
        lock.release()
