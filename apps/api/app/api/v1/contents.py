from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.content import Content
from app.models.subject import Subject
from app.schemas.content import ContentCreate, ContentRead, ContentUpdate

router = APIRouter(prefix="/contents", tags=["contents"])


@router.get("", response_model=list[ContentRead])
def list_contents(
    subject_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Content]:
    stmt = select(Content).order_by(Content.priority.desc(), Content.title)
    if subject_id:
        stmt = stmt.where(Content.subject_id == subject_id)
    return list(db.scalars(stmt).all())


@router.post("", response_model=ContentRead, status_code=status.HTTP_201_CREATED)
def create_content(payload: ContentCreate, db: Session = Depends(get_db)) -> Content:
    if not db.get(Subject, payload.subject_id):
        raise HTTPException(status_code=404, detail="Matéria não encontrada")
    content = Content(**payload.model_dump())
    db.add(content)
    db.commit()
    db.refresh(content)
    return content


@router.get("/{content_id}", response_model=ContentRead)
def get_content(content_id: UUID, db: Session = Depends(get_db)) -> Content:
    content = db.get(Content, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")
    return content


@router.patch("/{content_id}", response_model=ContentRead)
def update_content(
    content_id: UUID, payload: ContentUpdate, db: Session = Depends(get_db)
) -> Content:
    content = db.get(Content, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(content, key, value)
    db.commit()
    db.refresh(content)
    return content


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_content(content_id: UUID, db: Session = Depends(get_db)) -> None:
    content = db.get(Content, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")
    db.delete(content)
    db.commit()
