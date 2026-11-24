from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.models.content import Content
from app.models.exam import (
    Exam,
    ExamAnswer,
    ExamAttempt,
    ExamQuestion,
    ExamQuestionType,
)
from app.schemas.exam import (
    ExamAlternativeRead,
    ExamAnswerRead,
    ExamAttemptCreate,
    ExamAttemptRead,
    ExamCreate,
    ExamQuestionRead,
    ExamRead,
)
from app.services.exam_store import load_exam, persist_exam

router = APIRouter(tags=["exams"])


def _load_exam(db: Session, content_id: UUID) -> Exam | None:
    return load_exam(db, content_id)


def _to_read(exam: Exam, *, hide_answers: bool = True) -> ExamRead:
    questions = []
    for q in sorted(exam.questions, key=lambda item: item.sort_order):
        questions.append(
            ExamQuestionRead(
                id=q.id,
                type=q.type,
                question=q.question,
                sort_order=q.sort_order,
                points=q.points,
                alternatives=[
                    ExamAlternativeRead(
                        id=a.id,
                        text=a.text,
                        is_correct=False if hide_answers else a.is_correct,
                    )
                    for a in q.alternatives
                ],
            )
        )
    return ExamRead(
        id=exam.id,
        created_at=exam.created_at,
        updated_at=exam.updated_at,
        content_id=exam.content_id,
        title=exam.title,
        description=exam.description,
        questions=questions,
    )


@router.get("/contents/{content_id}/exam", response_model=ExamRead | None)
def get_exam(content_id: UUID, db: Session = Depends(get_db)) -> ExamRead | None:
    if not db.get(Content, content_id):
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")
    exam = _load_exam(db, content_id)
    return _to_read(exam) if exam else None


@router.put("/contents/{content_id}/exam", response_model=ExamRead)
def upsert_exam(content_id: UUID, payload: ExamCreate, db: Session = Depends(get_db)) -> ExamRead:
    if not db.get(Content, content_id):
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")

    for q in payload.questions:
        if q.type == ExamQuestionType.objetiva and len(q.alternatives) < 2:
            raise HTTPException(status_code=400, detail="Questão objetiva precisa de alternativas")

    persist_exam(
        db,
        content_id=content_id,
        title=payload.title,
        description=payload.description,
        questions=[
            {
                "type": q.type.value,
                "question": q.question,
                "points": q.points,
                "alternatives": [
                    {"text": alt.text, "is_correct": alt.is_correct}
                    for alt in q.alternatives
                ],
            }
            for q in payload.questions
        ],
    )
    exam = _load_exam(db, content_id)
    assert exam is not None
    return _to_read(exam, hide_answers=False)


@router.delete("/contents/{content_id}/exam", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(content_id: UUID, db: Session = Depends(get_db)) -> None:
    exam = db.scalars(select(Exam).where(Exam.content_id == content_id)).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Prova não encontrada")
    db.delete(exam)
    db.commit()


@router.post(
    "/contents/{content_id}/exam/attempts",
    response_model=ExamAttemptRead,
    status_code=status.HTTP_201_CREATED,
)
def attempt_exam(
    content_id: UUID, payload: ExamAttemptCreate, db: Session = Depends(get_db)
) -> ExamAttemptRead:
    exam = _load_exam(db, content_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Prova não encontrada")

    answers_by_q = {a.question_id: a for a in payload.answers}
    score = 0.0
    max_score = sum(q.points for q in exam.questions)
    pending = False
    answer_rows: list[ExamAnswer] = []

    attempt = ExamAttempt(exam_id=exam.id, score=0, max_score=max_score, status="graded")
    db.add(attempt)
    db.flush()

    for question in exam.questions:
        submitted = answers_by_q.get(question.id)
        if not submitted:
            raise HTTPException(status_code=400, detail=f"Falta resposta para questão {question.id}")

        is_correct: bool | None = None
        points = 0.0
        if question.type == ExamQuestionType.objetiva:
            if not submitted.selected_alternative_id:
                raise HTTPException(status_code=400, detail="Questão objetiva sem alternativa")
            chosen = next(
                (a for a in question.alternatives if a.id == submitted.selected_alternative_id),
                None,
            )
            if not chosen:
                raise HTTPException(status_code=400, detail="Alternativa inválida")
            is_correct = chosen.is_correct
            points = question.points if is_correct else 0.0
            score += points
        else:
            pending = True
            is_correct = None
            points = 0.0

        answer_rows.append(
            ExamAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                answer_text=submitted.answer_text,
                selected_alternative_id=submitted.selected_alternative_id,
                is_correct=is_correct,
                points_awarded=points,
            )
        )

    for row in answer_rows:
        db.add(row)
    attempt.score = score
    attempt.status = "pending_review" if pending else "graded"
    db.commit()
    db.refresh(attempt)

    return ExamAttemptRead(
        id=attempt.id,
        exam_id=attempt.exam_id,
        score=attempt.score,
        max_score=attempt.max_score,
        status=attempt.status,
        created_at=attempt.created_at.isoformat(),
        answers=[
            ExamAnswerRead(
                id=a.id,
                question_id=a.question_id,
                answer_text=a.answer_text,
                selected_alternative_id=a.selected_alternative_id,
                is_correct=a.is_correct,
                points_awarded=a.points_awarded,
            )
            for a in answer_rows
        ],
    )


@router.get("/contents/{content_id}/exam/attempts", response_model=list[ExamAttemptRead])
def list_exam_attempts(content_id: UUID, db: Session = Depends(get_db)) -> list[ExamAttemptRead]:
    exam = db.scalars(select(Exam).where(Exam.content_id == content_id)).first()
    if not exam:
        return []
    rows = db.scalars(
        select(ExamAttempt)
        .where(ExamAttempt.exam_id == exam.id)
        .options(selectinload(ExamAttempt.answers))
        .order_by(ExamAttempt.created_at.desc())
    ).all()
    return [
        ExamAttemptRead(
            id=row.id,
            exam_id=row.exam_id,
            score=row.score,
            max_score=row.max_score,
            status=row.status,
            created_at=row.created_at.isoformat(),
            answers=[
                ExamAnswerRead(
                    id=a.id,
                    question_id=a.question_id,
                    answer_text=a.answer_text,
                    selected_alternative_id=a.selected_alternative_id,
                    is_correct=a.is_correct,
                    points_awarded=a.points_awarded,
                )
                for a in row.answers
            ],
        )
        for row in rows
    ]
