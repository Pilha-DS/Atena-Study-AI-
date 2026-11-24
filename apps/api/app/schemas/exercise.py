from uuid import UUID

from pydantic import Field

from app.models.exercise import ExerciseType
from app.schemas.common import TimestampSchema
from app.schemas.orm_base import ORMCreate


class AlternativeCreate(ORMCreate):
    text: str = Field(min_length=1)
    is_correct: bool = False


class AlternativeRead(ORMCreate):
    id: UUID
    text: str
    is_correct: bool = False


class ExerciseCreate(ORMCreate):
    type: ExerciseType
    question: str = Field(min_length=1)
    explanation: str | None = None
    alternatives: list[AlternativeCreate] = []


class ExerciseRead(TimestampSchema):
    content_id: UUID
    type: ExerciseType
    question: str
    explanation: str | None
    alternatives: list[AlternativeRead] = []


class ExerciseAttemptCreate(ORMCreate):
    answer_text: str | None = None
    selected_alternative_id: UUID | None = None


class ExerciseAttemptRead(ORMCreate):
    id: UUID
    exercise_id: UUID
    answer_text: str | None
    selected_alternative_id: UUID | None
    is_correct: bool | None
    status: str
    feedback: str | None
    created_at: str
