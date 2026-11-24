from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.content import Content
from app.models.material import Material
from app.schemas.dashboard import SearchHit, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search(q: str = Query(min_length=1), db: Session = Depends(get_db)) -> SearchResponse:
    pattern = f"%{q.strip()}%"
    results: list[SearchHit] = []

    contents = db.scalars(
        select(Content)
        .where(or_(Content.title.ilike(pattern), Content.description.ilike(pattern)))
        .order_by(Content.updated_at.desc())
        .limit(20)
    ).all()
    for content in contents:
        results.append(
            SearchHit(
                kind="content",
                id=str(content.id),
                title=content.title,
                description=content.description,
                content_id=str(content.id),
                status=content.status.value,
            )
        )

    materials = db.scalars(
        select(Material)
        .where(or_(Material.title.ilike(pattern), Material.body.ilike(pattern)))
        .order_by(Material.updated_at.desc())
        .limit(20)
    ).all()
    for material in materials:
        results.append(
            SearchHit(
                kind="material",
                id=str(material.id),
                title=material.title,
                description=material.body[:160] if material.body else None,
                content_id=str(material.content_id),
            )
        )

    return SearchResponse(query=q, results=results)
