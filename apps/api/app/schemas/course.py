from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import TimestampSchema
from app.schemas.orm_base import ORMCreate


class CourseCreate(ORMCreate):
    name: str = Field(min_length=1, max_length=255)
    category: str = Field(default="Geral", min_length=1, max_length=255)
    description: str | None = None


class CourseUpdate(ORMCreate):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class CourseRead(TimestampSchema):
    name: str
    category: str
    description: str | None


class CourseListResponse(BaseModel):
    items: list[CourseRead]
    total: int
    limit: int
    offset: int
    categories: list[str] = Field(default_factory=list)


class DashboardCourse(BaseModel):
    id: UUID
    name: str
    category: str
    description: str | None = None
    total_contents: int = 0
    concluded_contents: int = 0
    started_contents: int = 0
    progress_percent: int = 0
