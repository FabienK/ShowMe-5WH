"""Persistance disque des batches — pas de base de données, un dossier par
batch :

  generated_batches/<batch_id>/manifest.json   (état complet, réécrit après
                                                 chaque item, voir batch_runner.py)
  generated_batches/<batch_id>/<index>.png      (image de l'item, si succès)

Le manifest est réécrit en entier (pas d'append) après chaque item, pour
rester simple, en écrivant d'abord dans un fichier temporaire puis en le
renommant atomiquement (os.replace) — évite un manifest tronqué/corrompu si
le process est tué en plein write().

Un batch encore status="running" au démarrage du process signifie que le
précédent process a été tué en plein milieu (voir
mark_interrupted_batches_on_startup, appelée une fois depuis main.py) : il
est requalifié "interrupted" pour ne jamais rester éternellement "running"
dans l'Historique. Pas de reprise automatique en V1 — scope volontairement
limité, l'app n'a aujourd'hui aucune infra de retry/reprise ailleurs.
"""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.models.schemas import BatchDetailResponse, BatchSummary

MANIFEST_FILENAME = "manifest.json"


def new_batch_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{stamp}_{uuid.uuid4().hex[:8]}"


def batch_dir(batch_id: str) -> Path:
    return settings.generated_batches_dir / batch_id


def _manifest_path(batch_id: str) -> Path:
    return batch_dir(batch_id) / MANIFEST_FILENAME


def image_path(batch_id: str, index: int) -> Path:
    return batch_dir(batch_id) / f"{index}.png"


def write_manifest(batch_id: str, detail: BatchDetailResponse) -> None:
    directory = batch_dir(batch_id)
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = _manifest_path(batch_id)
    tmp_path = manifest_path.with_suffix(".json.tmp")
    tmp_path.write_text(detail.model_dump_json(indent=2), encoding="utf-8")
    os.replace(tmp_path, manifest_path)


def read_manifest(batch_id: str) -> BatchDetailResponse:
    manifest_path = _manifest_path(batch_id)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Batch introuvable : {batch_id}")
    return BatchDetailResponse.model_validate_json(manifest_path.read_text(encoding="utf-8"))


def list_batches() -> list[BatchSummary]:
    root = settings.generated_batches_dir
    if not root.exists():
        return []

    summaries = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        try:
            detail = read_manifest(entry.name)
        except (FileNotFoundError, ValueError):
            continue
        completed_items = sum(1 for item in detail.items if item.status == "success")
        error_items = sum(1 for item in detail.items if item.status == "error")
        summaries.append(
            BatchSummary(
                batch_id=detail.batch_id,
                status=detail.status,
                created_at=detail.created_at,
                total_items=len(detail.items),
                completed_items=completed_items,
                error_items=error_items,
            )
        )
    summaries.sort(key=lambda summary: summary.created_at, reverse=True)
    return summaries


def mark_interrupted_batches_on_startup() -> None:
    root = settings.generated_batches_dir
    if not root.exists():
        return
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        try:
            detail = read_manifest(entry.name)
        except (FileNotFoundError, ValueError):
            continue
        if detail.status == "running":
            detail.status = "interrupted"
            write_manifest(entry.name, detail)
