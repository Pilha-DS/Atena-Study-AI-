from uuid import UUID

from pydantic import Field

from app.models.material import MaterialType
from app.schemas.common import TimestampSchema
from app.schemas.orm_base import ORMCreate


class MaterialCreate(ORMCreate):
    type: MaterialType
    title: str = Field(min_length=1, max_length=255)
    url_or_path: str | None = Field(default=None, max_length=1024)
    body: str | None = None


class MaterialUpdate(ORMCreate):
    type: MaterialType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    url_or_path: str | None = Field(default=None, max_length=1024)
    body: str | None = None


class MaterialRead(TimestampSchema):
    content_id: UUID
    type: MaterialType
    title: str
    url_or_path: str | None
    body: str | None
