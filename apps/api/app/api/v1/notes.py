from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.content import Content
from app.models.note import Note
from app.schemas.note import NoteCreate, NoteRead, NoteUpdate

router = APIRouter(tags=["notes"])


@router.get("/contents/{content_id}/notes", response_model=list[NoteRead])
def list_notes(content_id: UUID, db: Session = Depends(get_db)) -> list[Note]:
    if not db.get(Content, content_id):
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")
    stmt = select(Note).where(Note.content_id == content_id).order_by(Note.created_at.desc())
    return list(db.scalars(stmt).all())


@router.post(
    "/contents/{content_id}/notes",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
)
def create_note(content_id: UUID, payload: NoteCreate, db: Session = Depends(get_db)) -> Note:
    if not db.get(Content, content_id):
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")
    note = Note(content_id=content_id, **payload.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/notes/{note_id}", response_model=NoteRead)
def get_note(note_id: UUID, db: Session = Depends(get_db)) -> Note:
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Anotação não encontrada")
    return note


@router.patch("/notes/{note_id}", response_model=NoteRead)
def update_note(note_id: UUID, payload: NoteUpdate, db: Session = Depends(get_db)) -> Note:
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Anotação não encontrada")
    note.body = payload.body
    db.commit()
    db.refresh(note)
    return note


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: UUID, db: Session = Depends(get_db)) -> None:
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Anotação não encontrada")
    db.delete(note)
    db.commit()
