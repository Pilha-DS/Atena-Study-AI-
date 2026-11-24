from uuid import UUID

from pydantic import Field

from app.models.level import LearnLevel
from app.schemas.common import TimestampSchema
from app.schemas.orm_base import ORMCreate


class SubjectCreate(ORMCreate):
    topic_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    sort_order: int = 0
    level: LearnLevel = LearnLevel.iniciante
    unlocked_manual: bool = False


class SubjectUpdate(ORMCreate):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    sort_order: int | None = None
    level: LearnLevel | None = None
    unlocked_manual: bool | None = None


class SubjectRead(TimestampSchema):
    topic_id: UUID
    name: str
    description: str | None
    sort_order: int
    level: LearnLevel
    unlocked_manual: bool
    is_unlocked: bool = True
