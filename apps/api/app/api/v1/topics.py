from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.course import Course
from app.models.study_topic import StudyTopic
from app.schemas.topic import TopicCreate, TopicRead, TopicUpdate
from app.services.progression import topic_unlock_map

router = APIRouter(prefix="/topics", tags=["topics"])


def _to_read(topic: StudyTopic, is_unlocked: bool) -> TopicRead:
    return TopicRead.model_validate(topic).model_copy(update={"is_unlocked": is_unlocked})


@router.get("", response_model=list[TopicRead])
def list_topics(
    course_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[TopicRead]:
    stmt = select(StudyTopic).order_by(StudyTopic.sort_order, StudyTopic.name)
    if course_id:
        stmt = stmt.where(StudyTopic.course_id == course_id)
    topics = list(db.scalars(stmt).all())

    unlock_by_course: dict[UUID, dict[UUID, bool]] = {}
    result: list[TopicRead] = []
    for topic in topics:
        if topic.course_id not in unlock_by_course:
            unlock_by_course[topic.course_id] = topic_unlock_map(db, topic.course_id)
        result.append(_to_read(topic, unlock_by_course[topic.course_id].get(topic.id, True)))
    return result


@router.post("", response_model=TopicRead, status_code=status.HTTP_201_CREATED)
def create_topic(payload: TopicCreate, db: Session = Depends(get_db)) -> TopicRead:
    if not db.get(Course, payload.course_id):
        raise HTTPException(status_code=404, detail="Curso não encontrado")
    topic = StudyTopic(**payload.model_dump())
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return _to_read(topic, True)


@router.get("/{topic_id}", response_model=TopicRead)
def get_topic(topic_id: UUID, db: Session = Depends(get_db)) -> TopicRead:
    topic = db.get(StudyTopic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Tópico não encontrado")
    unlocked = topic_unlock_map(db, topic.course_id).get(topic.id, True)
    return _to_read(topic, unlocked)


@router.patch("/{topic_id}", response_model=TopicRead)
def update_topic(topic_id: UUID, payload: TopicUpdate, db: Session = Depends(get_db)) -> TopicRead:
    topic = db.get(StudyTopic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Tópico não encontrado")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(topic, key, value)
    db.commit()
    db.refresh(topic)
    unlocked = topic_unlock_map(db, topic.course_id).get(topic.id, True)
    return _to_read(topic, unlocked)


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_topic(topic_id: UUID, db: Session = Depends(get_db)) -> None:
    topic = db.get(StudyTopic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Tópico não encontrado")
    db.delete(topic)
    db.commit()
