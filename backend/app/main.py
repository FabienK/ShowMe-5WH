from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import batches, generate, openai_settings, questions, script
from app.services import batch_store


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Un batch encore "running" au démarrage = le process précédent a été
    # tué en plein milieu (voir batch_store.py) — jamais de reprise
    # automatique, juste éviter qu'il reste "running" pour toujours.
    batch_store.mark_interrupted_batches_on_startup()
    yield


app = FastAPI(title="4W1H Image Generator", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(questions.router, prefix="/api")
app.include_router(script.router, prefix="/api")
app.include_router(generate.router, prefix="/api")
app.include_router(batches.router, prefix="/api")
app.include_router(openai_settings.router, prefix="/api")

settings.generated_batches_dir.mkdir(parents=True, exist_ok=True)
app.mount("/generated", StaticFiles(directory=settings.generated_batches_dir), name="generated")


@app.get("/api/health")
def health() -> dict[str, str]:
    # "app" permet à un script/agent de vérifier qu'il parle bien à ShowMe et
    # pas à un autre serveur qui occuperait le même port (voir
    # scripts/start_showme.sh et AGENT.md).
    return {"status": "ok", "app": "ShowMe-5WH"}
