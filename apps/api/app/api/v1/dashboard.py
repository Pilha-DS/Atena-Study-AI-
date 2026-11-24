from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.content import Content, ContentStatus
from app.models.course import Course
from app.models.study_topic import StudyTopic
from app.models.subject import Subject
from app.schemas.content import ContentRead
from app.schemas.course import DashboardCourse
from app.schemas.dashboard import DashboardResponse, StatusCounts

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

DASHBOARD_COURSES_LIMIT = 6


@router.get("", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    total_courses = db.scalar(select(func.count()).select_from(Course)) or 0
    total_topics = db.scalar(select(func.count()).select_from(StudyTopic)) or 0
    total_subjects = db.scalar(select(func.count()).select_from(Subject)) or 0
    total_contents = db.scalar(select(func.count()).select_from(Content)) or 0

    status_rows = db.execute(select(Content.status, func.count()).group_by(Content.status)).all()
    counts = StatusCounts()
    for status_value, count in status_rows:
        setattr(counts, status_value.value, count)

    high_priority = list(
        db.scalars(
            select(Content)
            .where(Content.priority >= 4)
            .where(Content.status != ContentStatus.concluido)
            .order_by(Content.priority.desc(), Content.updated_at.desc())
            .limit(8)
        ).all()
    )
    recent = list(db.scalars(select(Content).order_by(Content.updated_at.desc()).limit(8)).all())

    # Apenas cursos com progresso (algum conteúdo saiu de "pendente"), agregados no banco.
    started_count = func.sum(
        case((Content.status != ContentStatus.pendente, 1), else_=0)
    )
    concluded_count = func.sum(
        case((Content.status == ContentStatus.concluido, 1), else_=0)
    )
    course_rows = db.execute(
        select(
            Course.id,
            Course.name,
            Course.category,
            Course.description,
            func.count(Content.id).label("total_contents"),
            concluded_count.label("concluded_contents"),
            started_count.label("started_contents"),
            func.max(Content.updated_at).label("last_activity"),
        )
        .join(StudyTopic, StudyTopic.course_id == Course.id)
        .join(Subject, Subject.topic_id == StudyTopic.id)
        .join(Content, Content.subject_id == Subject.id)
        .group_by(Course.id, Course.name, Course.category, Course.description)
        .having(started_count > 0)
        .order_by(func.max(Content.updated_at).desc(), Course.name)
        .limit(DASHBOARD_COURSES_LIMIT)
    ).all()

    active_courses: list[DashboardCourse] = []
    for row in course_rows:
        total = int(row.total_contents or 0)
        concluded = int(row.concluded_contents or 0)
        started = int(row.started_contents or 0)
        active_courses.append(
            DashboardCourse(
                id=row.id,
                name=row.name,
                category=row.category,
                description=row.description,
                total_contents=total,
                concluded_contents=concluded,
                started_contents=started,
                progress_percent=round((concluded / total) * 100) if total else 0,
            )
        )

    return DashboardResponse(
        total_courses=total_courses,
        total_topics=total_topics,
        total_subjects=total_subjects,
        total_contents=total_contents,
        status_counts=counts,
        high_priority=[ContentRead.model_validate(item) for item in high_priority],
        recent_contents=[ContentRead.model_validate(item) for item in recent],
        active_courses=active_courses,
    )
