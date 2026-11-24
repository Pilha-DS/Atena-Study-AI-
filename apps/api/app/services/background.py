from __future__ import annotations

import logging
import os
import queue
import threading
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.services.structure_generator import enrich_content_by_id, pending_content_ids

logger = logging.getLogger(__name__)

_ENRICH_CONCURRENCY = max(1, int(os.getenv("ENRICH_CONCURRENCY", "5")))
_ENRICH_SYNC = os.getenv("ENRICH_SYNC") == "1"


def _enrich_one(content_id: UUID) -> None:
    db = SessionLocal()
    try:
        enrich_content_by_id(db, content_id)
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao gerar materiais do conteúdo %s", content_id)
        db.rollback()
    finally:
        db.close()


def _enrich_course(course_id: UUID) -> None:
    db = SessionLocal()
    try:
        content_ids = pending_content_ids(db, course_id)
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao listar conteúdos pendentes do curso %s", course_id)
        return
    finally:
        db.close()

    if not content_ids:
        return

    workers = min(_ENRICH_CONCURRENCY, len(content_ids)) if not _ENRICH_SYNC else 1
    logger.info(
        "Enriquecendo curso %s: %s conteúdos (%s workers)",
        course_id,
        len(content_ids),
        workers,
    )

    if workers <= 1:
        for content_id in content_ids:
            _enrich_one(content_id)
        return

    work: queue.Queue[UUID | None] = queue.Queue()
    for content_id in content_ids:
        work.put(content_id)

    def worker() -> None:
        while True:
            item = work.get()
            try:
                if item is None:
                    return
                _enrich_one(item)
            finally:
                work.task_done()

    # Threads daemon: não seguram shutdown/reload do servidor.
    for _ in range(workers):
        threading.Thread(target=worker, daemon=True, name=f"enrich-{course_id}").start()
    work.join()


def run_course_enrichment(course_id: UUID) -> None:
    """Gera materiais dos conteúdos pendentes sem bloquear a resposta HTTP.

    Roda em thread daemon para o usuário receber a trilha na hora e ver os
    materiais chegando conforme a página consulta o status.
    """
    if _ENRICH_SYNC:
        _enrich_course(course_id)
        return

    threading.Thread(
        target=_enrich_course,
        args=(course_id,),
        daemon=True,
        name=f"enrich-course-{course_id}",
    ).start()


def resume_pending_courses(db: Session) -> list[UUID]:
    """Encontra cursos com conteúdos sem material e retoma o enriquecimento."""
    from sqlalchemy import distinct, select

    from app.models.content import Content
    from app.models.course import Course
    from app.models.material import Material, MaterialType
    from app.models.study_topic import StudyTopic
    from app.models.subject import Subject

    enriched = (
        select(Material.content_id)
        .where(Material.type == MaterialType.text)
        .scalar_subquery()
    )
    course_ids = db.scalars(
        select(distinct(Course.id))
        .join(StudyTopic, StudyTopic.course_id == Course.id)
        .join(Subject, Subject.topic_id == StudyTopic.id)
        .join(Content, Content.subject_id == Subject.id)
        .where(Content.id.not_in(enriched))
    ).all()

    for course_id in course_ids:
        run_course_enrichment(course_id)
    return list(course_ids)
