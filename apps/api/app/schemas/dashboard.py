from pydantic import BaseModel

from app.schemas.content import ContentRead
from app.schemas.course import DashboardCourse


class StatusCounts(BaseModel):
    pendente: int = 0
    em_andamento: int = 0
    concluido: int = 0


class DashboardResponse(BaseModel):
    total_courses: int
    total_topics: int
    total_subjects: int
    total_contents: int
    status_counts: StatusCounts
    high_priority: list[ContentRead]
    recent_contents: list[ContentRead]
    active_courses: list[DashboardCourse] = []


class SearchHit(BaseModel):
    kind: str
    id: str
    title: str
    description: str | None = None
    content_id: str | None = None
    status: str | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchHit]
