from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Content, ContentStatus
from app.models.level import LearnLevel, level_index
from app.models.study_topic import StudyTopic
from app.models.subject import Subject


def _pending_contents_by_level(
    rows: list[tuple[LearnLevel, ContentStatus]],
) -> dict[LearnLevel, list[ContentStatus]]:
    grouped: dict[LearnLevel, list[ContentStatus]] = {}
    for level, status in rows:
        grouped.setdefault(level, []).append(status)
    return grouped


def _has_pending_lower_level(
    grouped: dict[LearnLevel, list[ContentStatus]], level: LearnLevel
) -> bool:
    target = level_index(level)
    for candidate, statuses in grouped.items():
        if level_index(candidate) >= target:
            continue
        if any(status != ContentStatus.concluido for status in statuses):
            return True
    return False


def topic_unlock_map(db: Session, course_id: UUID) -> dict[UUID, bool]:
    """Nível N de um tópico só libera com todos os conteúdos dos níveis anteriores concluídos."""
    topics = list(
        db.scalars(select(StudyTopic).where(StudyTopic.course_id == course_id)).all()
    )
    if not topics:
        return {}

    rows = list(
        db.execute(
            select(StudyTopic.id, Subject.level, Content.status)
            .join(Subject, Subject.topic_id == StudyTopic.id)
            .join(Content, Content.subject_id == Subject.id)
            .where(StudyTopic.course_id == course_id)
        ).all()
    )

    result: dict[UUID, bool] = {}
    for topic in topics:
        if topic.unlocked_manual:
            result[topic.id] = True
            continue
        # Conteúdos do próprio tópico não bloqueiam o tópico (senão matérias
        # iniciantes dentro de um tópico intermediário se auto-bloqueariam).
        grouped = _pending_contents_by_level(
            [
                (level, status)
                for owner_topic_id, level, status in rows
                if owner_topic_id != topic.id
            ]
        )
        result[topic.id] = not _has_pending_lower_level(grouped, topic.level)
    return result


def subject_unlock_map(db: Session, topic_id: UUID) -> dict[UUID, bool]:
    """Matéria exige o tópico liberado + níveis anteriores da própria matéria concluídos."""
    topic = db.get(StudyTopic, topic_id)
    if topic is None:
        return {}

    topic_unlocked = topic_unlock_map(db, topic.course_id).get(topic.id, True)
    subjects = list(
        db.scalars(
            select(Subject).where(Subject.topic_id == topic_id).order_by(Subject.sort_order, Subject.name)
        ).all()
    )
    if not subjects:
        return {}

    rows = list(
        db.execute(
            select(Subject.level, Content.status)
            .join(Content, Content.subject_id == Subject.id)
            .where(Subject.topic_id == topic_id)
        ).all()
    )
    grouped = _pending_contents_by_level([(level, status) for level, status in rows])

    result: dict[UUID, bool] = {}
    for subject in subjects:
        unlocked = topic_unlocked and (
            bool(subject.unlocked_manual) or not _has_pending_lower_level(grouped, subject.level)
        )
        result[subject.id] = unlocked
    return result


def topic_unlocked(db: Session, topic: StudyTopic) -> bool:
    return topic_unlock_map(db, topic.course_id).get(topic.id, True)


def subject_unlocked(db: Session, subject: Subject) -> bool:
    return subject_unlock_map(db, subject.topic_id).get(subject.id, True)
