from uuid import UUID

from pydantic import Field

from app.models.exam import ExamQuestionType
from app.schemas.common import TimestampSchema
from app.schemas.orm_base import ORMCreate


class ExamAlternativeCreate(ORMCreate):
    text: str = Field(min_length=1)
    is_correct: bool = False


class ExamAlternativeRead(ORMCreate):
    id: UUID
    text: str
    is_correct: bool = False


class ExamQuestionCreate(ORMCreate):
    type: ExamQuestionType
    question: str = Field(min_length=1)
    sort_order: int = 0
    points: float = 1.0
    alternatives: list[ExamAlternativeCreate] = []


class ExamQuestionRead(ORMCreate):
    id: UUID
    type: ExamQuestionType
    question: str
    sort_order: int
    points: float
    alternatives: list[ExamAlternativeRead] = []


class ExamCreate(ORMCreate):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    questions: list[ExamQuestionCreate] = Field(min_length=1)


class ExamRead(TimestampSchema):
    content_id: UUID
    title: str
    description: str | None
    questions: list[ExamQuestionRead] = []


class ExamAnswerSubmit(ORMCreate):
    question_id: UUID
    answer_text: str | None = None
    selected_alternative_id: UUID | None = None


class ExamAttemptCreate(ORMCreate):
    answers: list[ExamAnswerSubmit] = Field(min_length=1)


class ExamAnswerRead(ORMCreate):
    id: UUID
    question_id: UUID
    answer_text: str | None
    selected_alternative_id: UUID | None
    is_correct: bool | None
    points_awarded: float


class ExamAttemptRead(ORMCreate):
    id: UUID
    exam_id: UUID
    score: float
    max_score: float
    status: str
    created_at: str
    answers: list[ExamAnswerRead] = []
