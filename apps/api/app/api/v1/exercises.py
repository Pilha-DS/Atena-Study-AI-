from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.models.content import Content
from app.models.exercise import Exercise, ExerciseAlternative, ExerciseAttempt, ExerciseType
from app.schemas.exercise import (
    AlternativeRead,
    ExerciseAttemptCreate,
    ExerciseAttemptRead,
    ExerciseCreate,
    ExerciseRead,
)

router = APIRouter(tags=["exercises"])


def _to_read(exercise: Exercise, *, hide_answers: bool = False) -> ExerciseRead:
    alts = [
        AlternativeRead(
            id=alt.id,
            text=alt.text,
            is_correct=False if hide_answers else alt.is_correct,
        )
        for alt in exercise.alternatives
    ]
    return ExerciseRead(
        id=exercise.id,
        created_at=exercise.created_at,
        updated_at=exercise.updated_at,
        content_id=exercise.content_id,
        type=exercise.type,
        question=exercise.question,
        explanation=None if hide_answers else exercise.explanation,
        alternatives=alts,
    )


@router.get("/contents/{content_id}/exercises", response_model=list[ExerciseRead])
def list_exercises(content_id: UUID, db: Session = Depends(get_db)) -> list[ExerciseRead]:
    if not db.get(Content, content_id):
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")
    rows = db.scalars(
        select(Exercise)
        .where(Exercise.content_id == content_id)
        .options(selectinload(Exercise.alternatives))
        .order_by(Exercise.created_at)
    ).all()
    return [_to_read(row, hide_answers=True) for row in rows]


@router.post(
    "/contents/{content_id}/exercises",
    response_model=ExerciseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_exercise(
    content_id: UUID, payload: ExerciseCreate, db: Session = Depends(get_db)
) -> ExerciseRead:
    if not db.get(Content, content_id):
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")
    if payload.type == ExerciseType.objetiva and len(payload.alternatives) < 2:
        raise HTTPException(status_code=400, detail="Exercício objetivo precisa de ao menos 2 alternativas")
    if payload.type == ExerciseType.objetiva and not any(a.is_correct for a in payload.alternatives):
        raise HTTPException(status_code=400, detail="Marque ao menos uma alternativa correta")

    exercise = Exercise(
        content_id=content_id,
        type=payload.type,
        question=payload.question,
        explanation=payload.explanation,
    )
    db.add(exercise)
    db.flush()
    for alt in payload.alternatives:
        db.add(
            ExerciseAlternative(
                exercise_id=exercise.id,
                text=alt.text,
                is_correct=alt.is_correct,
            )
        )
    db.commit()
    exercise = db.scalars(
        select(Exercise)
        .where(Exercise.id == exercise.id)
        .options(selectinload(Exercise.alternatives))
    ).one()
    return _to_read(exercise)


@router.delete("/exercises/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(exercise_id: UUID, db: Session = Depends(get_db)) -> None:
    exercise = db.get(Exercise, exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercício não encontrado")
    db.delete(exercise)
    db.commit()


@router.post(
    "/exercises/{exercise_id}/attempts",
    response_model=ExerciseAttemptRead,
    status_code=status.HTTP_201_CREATED,
)
def attempt_exercise(
    exercise_id: UUID, payload: ExerciseAttemptCreate, db: Session = Depends(get_db)
) -> ExerciseAttemptRead:
    exercise = db.scalars(
        select(Exercise)
        .where(Exercise.id == exercise_id)
        .options(selectinload(Exercise.alternatives))
    ).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercício não encontrado")

    is_correct: bool | None = None
    status_value = "graded"
    feedback = exercise.explanation

    if exercise.type == ExerciseType.objetiva:
        if not payload.selected_alternative_id:
            raise HTTPException(status_code=400, detail="Selecione uma alternativa")
        chosen = next(
            (a for a in exercise.alternatives if a.id == payload.selected_alternative_id),
            None,
        )
        if not chosen:
            raise HTTPException(status_code=400, detail="Alternativa inválida")
        is_correct = chosen.is_correct
    else:
        if not (payload.answer_text or "").strip():
            raise HTTPException(status_code=400, detail="Informe a resposta")
        status_value = "pending_review"
        is_correct = None
        feedback = "Resposta discursiva enviada. Revise manualmente depois."

    attempt = ExerciseAttempt(
        exercise_id=exercise.id,
        answer_text=payload.answer_text,
        selected_alternative_id=payload.selected_alternative_id,
        is_correct=is_correct,
        status=status_value,
        feedback=feedback,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return ExerciseAttemptRead(
        id=attempt.id,
        exercise_id=attempt.exercise_id,
        answer_text=attempt.answer_text,
        selected_alternative_id=attempt.selected_alternative_id,
        is_correct=attempt.is_correct,
        status=attempt.status,
        feedback=attempt.feedback,
        created_at=attempt.created_at.isoformat(),
    )


@router.get("/exercises/{exercise_id}/attempts", response_model=list[ExerciseAttemptRead])
def list_attempts(exercise_id: UUID, db: Session = Depends(get_db)) -> list[ExerciseAttemptRead]:
    if not db.get(Exercise, exercise_id):
        raise HTTPException(status_code=404, detail="Exercício não encontrado")
    rows = db.scalars(
        select(ExerciseAttempt)
        .where(ExerciseAttempt.exercise_id == exercise_id)
        .order_by(ExerciseAttempt.created_at.desc())
    ).all()
    return [
        ExerciseAttemptRead(
            id=row.id,
            exercise_id=row.exercise_id,
            answer_text=row.answer_text,
            selected_alternative_id=row.selected_alternative_id,
            is_correct=row.is_correct,
            status=row.status,
            feedback=row.feedback,
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]
