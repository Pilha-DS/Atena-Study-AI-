from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.study_topic import StudyTopic
from app.models.subject import Subject
from app.schemas.subject import SubjectCreate, SubjectRead, SubjectUpdate
from app.services.progression import subject_unlock_map

router = APIRouter(prefix="/subjects", tags=["subjects"])


def _to_read(subject: Subject, is_unlocked: bool) -> SubjectRead:
    return SubjectRead.model_validate(subject).model_copy(
        update={"is_unlocked": is_unlocked}
    )


@router.get("", response_model=list[SubjectRead])
def list_subjects(
    topic_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[SubjectRead]:
    stmt = select(Subject).order_by(Subject.sort_order, Subject.level, Subject.name)
    if topic_id:
        stmt = stmt.where(Subject.topic_id == topic_id)
    subjects = list(db.scalars(stmt).all())

    unlock_by_topic: dict[UUID, dict[UUID, bool]] = {}
    result: list[SubjectRead] = []
    for subject in subjects:
        if subject.topic_id not in unlock_by_topic:
            unlock_by_topic[subject.topic_id] = subject_unlock_map(db, subject.topic_id)
        result.append(
            _to_read(subject, unlock_by_topic[subject.topic_id].get(subject.id, True))
        )
    return result


@router.post("", response_model=SubjectRead, status_code=status.HTTP_201_CREATED)
def create_subject(payload: SubjectCreate, db: Session = Depends(get_db)) -> SubjectRead:
    if not db.get(StudyTopic, payload.topic_id):
        raise HTTPException(status_code=404, detail="Tópico não encontrado")
    subject = Subject(**payload.model_dump())
    db.add(subject)
    db.commit()
    db.refresh(subject)
    unlocked = subject_unlock_map(db, subject.topic_id).get(subject.id, True)
    return _to_read(subject, unlocked)


@router.get("/{subject_id}", response_model=SubjectRead)
def get_subject(subject_id: UUID, db: Session = Depends(get_db)) -> SubjectRead:
    subject = db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Matéria não encontrada")
    unlocked = subject_unlock_map(db, subject.topic_id).get(subject.id, True)
    return _to_read(subject, unlocked)


@router.patch("/{subject_id}", response_model=SubjectRead)
def update_subject(
    subject_id: UUID, payload: SubjectUpdate, db: Session = Depends(get_db)
) -> SubjectRead:
    subject = db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Matéria não encontrada")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(subject, key, value)
    db.commit()
    db.refresh(subject)
    unlocked = subject_unlock_map(db, subject.topic_id).get(subject.id, True)
    return _to_read(subject, unlocked)


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(subject_id: UUID, db: Session = Depends(get_db)) -> None:
    subject = db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Matéria não encontrada")
    db.delete(subject)
    db.commit()
