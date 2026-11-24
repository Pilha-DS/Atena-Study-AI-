from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.course import Course
from app.schemas.course import CourseCreate, CourseListResponse, CourseRead, CourseUpdate

router = APIRouter(prefix="/courses", tags=["courses"])

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50


@router.get("", response_model=CourseListResponse)
def list_courses(
    category: str | None = Query(default=None),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> CourseListResponse:
    """Lista paginada (padrão 10 por página) — a paginação acontece no banco."""
    base = select(Course)
    if category:
        base = base.where(Course.category == category)

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = list(
        db.scalars(base.order_by(Course.name).limit(limit).offset(offset)).all()
    )
    categories = list(
        db.scalars(select(Course.category).distinct().order_by(Course.category)).all()
    )

    return CourseListResponse(
        items=[CourseRead.model_validate(course) for course in items],
        total=total,
        limit=limit,
        offset=offset,
        categories=categories,
    )


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, db: Session = Depends(get_db)) -> Course:
    course = Course(**payload.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get("/{course_id}", response_model=CourseRead)
def get_course(course_id: UUID, db: Session = Depends(get_db)) -> Course:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso não encontrado")
    return course


@router.patch("/{course_id}", response_model=CourseRead)
def update_course(course_id: UUID, payload: CourseUpdate, db: Session = Depends(get_db)) -> Course:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso não encontrado")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(course, key, value)
    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: UUID, db: Session = Depends(get_db)) -> None:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso não encontrado")
    db.delete(course)
    db.commit()
