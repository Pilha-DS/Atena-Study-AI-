import logging
import os
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _run_migrations() -> None:
    """Garante schema atualizado mesmo após hot-reload do código."""
    if os.getenv("SKIP_DB_MIGRATIONS") == "1":
        return
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        return
    config = Config("alembic.ini")
    command.upgrade(config, "head")


def _resume_pending_enrichment() -> None:
    """Retoma materiais pendentes após restart/hot-reload.

    As threads de enriquecimento são daemon e morrem com o processo; sem isso,
    um curso interrompido no meio ficaria com conteúdos sem material para sempre.
    """
    if os.getenv("SKIP_DB_MIGRATIONS") == "1" or os.getenv("RESUME_ENRICHMENT") == "0":
        return
    from app.core.db import SessionLocal
    from app.services.background import resume_pending_courses

    db = SessionLocal()
    try:
        resume_pending_courses(db)
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao retomar enriquecimentos pendentes")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _run_migrations()
    _resume_pending_enrichment()
    yield


settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
