from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.content import Content
from app.models.material import Material
from app.schemas.material import MaterialCreate, MaterialRead, MaterialUpdate

router = APIRouter(tags=["materials"])


@router.get("/contents/{content_id}/materials", response_model=list[MaterialRead])
def list_materials(content_id: UUID, db: Session = Depends(get_db)) -> list[Material]:
    if not db.get(Content, content_id):
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")
    stmt = select(Material).where(Material.content_id == content_id).order_by(Material.title)
    return list(db.scalars(stmt).all())


@router.post(
    "/contents/{content_id}/materials",
    response_model=MaterialRead,
    status_code=status.HTTP_201_CREATED,
)
def create_material(
    content_id: UUID, payload: MaterialCreate, db: Session = Depends(get_db)
) -> Material:
    if not db.get(Content, content_id):
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")
    material = Material(content_id=content_id, **payload.model_dump())
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


@router.get("/materials/{material_id}", response_model=MaterialRead)
def get_material(material_id: UUID, db: Session = Depends(get_db)) -> Material:
    material = db.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado")
    return material


@router.patch("/materials/{material_id}", response_model=MaterialRead)
def update_material(
    material_id: UUID, payload: MaterialUpdate, db: Session = Depends(get_db)
) -> Material:
    material = db.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(material, key, value)
    db.commit()
    db.refresh(material)
    return material


@router.delete("/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(material_id: UUID, db: Session = Depends(get_db)) -> None:
    material = db.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado")
    db.delete(material)
    db.commit()
