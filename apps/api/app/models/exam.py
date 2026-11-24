from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.content import Content


class ExamQuestionType(str, enum.Enum):
    objetiva = "objetiva"
    discursiva = "discursiva"


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    content_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("contents.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    content: Mapped[Content] = relationship("Content", back_populates="exam")
    questions: Mapped[list[ExamQuestion]] = relationship(
        "ExamQuestion", back_populates="exam", cascade="all, delete-orphan"
    )
    attempts: Mapped[list[ExamAttempt]] = relationship(
        "ExamAttempt", back_populates="exam", cascade="all, delete-orphan"
    )


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[ExamQuestionType] = mapped_column(
        Enum(ExamQuestionType, name="exam_question_type", native_enum=False), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    points: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    exam: Mapped[Exam] = relationship("Exam", back_populates="questions")
    alternatives: Mapped[list[ExamAlternative]] = relationship(
        "ExamAlternative", back_populates="question", cascade="all, delete-orphan"
    )


class ExamAlternative(Base):
    __tablename__ = "exam_alternatives"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("exam_questions.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    question: Mapped[ExamQuestion] = relationship("ExamQuestion", back_populates="alternatives")


class ExamAttempt(Base):
    __tablename__ = "exam_attempts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="graded", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    exam: Mapped[Exam] = relationship("Exam", back_populates="attempts")
    answers: Mapped[list[ExamAnswer]] = relationship(
        "ExamAnswer", back_populates="attempt", cascade="all, delete-orphan"
    )


class ExamAnswer(Base):
    __tablename__ = "exam_answers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("exam_attempts.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("exam_questions.id", ondelete="CASCADE"), nullable=False
    )
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_alternative_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("exam_alternatives.id", ondelete="SET NULL"), nullable=True
    )
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    points_awarded: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    attempt: Mapped[ExamAttempt] = relationship("ExamAttempt", back_populates="answers")
    question: Mapped[ExamQuestion] = relationship("ExamQuestion")
