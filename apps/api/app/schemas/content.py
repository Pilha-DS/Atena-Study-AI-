from uuid import UUID

from pydantic import Field

from app.models.content import ContentStatus
from app.schemas.common import TimestampSchema
from app.schemas.orm_base import ORMCreate


class ContentCreate(ORMCreate):
    subject_id: UUID
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: ContentStatus = ContentStatus.pendente
    priority: int = Field(default=3, ge=1, le=5)


class ContentUpdate(ORMCreate):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: ContentStatus | None = None
    priority: int | None = Field(default=None, ge=1, le=5)


class ContentRead(TimestampSchema):
    subject_id: UUID
    title: str
    description: str | None
    status: ContentStatus
    priority: int
