from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.exam import Exam, ExamAlternative, ExamQuestion, ExamQuestionType


def load_exam(db: Session, content_id: UUID) -> Exam | None:
    return db.scalars(
        select(Exam)
        .where(Exam.content_id == content_id)
        .options(selectinload(Exam.questions).selectinload(ExamQuestion.alternatives))
    ).first()


def persist_exam(
    db: Session,
    *,
    content_id: UUID,
    title: str,
    description: str | None,
    questions: list[dict[str, Any]],
) -> Exam:
    """Cria (ou substitui) a prova do conteúdo a partir do payload da IA."""
    existing = load_exam(db, content_id)
    if existing:
        db.delete(existing)
        db.flush()

    exam = Exam(content_id=content_id, title=title[:255], description=description)
    db.add(exam)
    db.flush()

    for index, question_data in enumerate(questions):
        question_type = ExamQuestionType(str(question_data.get("type") or "objetiva"))
        question = ExamQuestion(
            exam_id=exam.id,
            type=question_type,
            question=str(question_data.get("question") or "").strip(),
            sort_order=index,
            points=float(question_data.get("points") or 1),
        )
        db.add(question)
        db.flush()
        if question_type == ExamQuestionType.objetiva:
            for alt in question_data.get("alternatives", []):
                db.add(
                    ExamAlternative(
                        question_id=question.id,
                        text=str(alt.get("text") or "").strip(),
                        is_correct=bool(alt.get("is_correct")),
                    )
                )

    db.commit()
    exam = load_exam(db, content_id)
    assert exam is not None
    return exam
