from uuid import UUID

from pydantic import Field

from app.schemas.common import TimestampSchema
from app.schemas.orm_base import ORMCreate


class NoteCreate(ORMCreate):
    body: str = Field(min_length=1)


class NoteUpdate(ORMCreate):
    body: str = Field(min_length=1)


class NoteRead(TimestampSchema):
    content_id: UUID
    body: str
