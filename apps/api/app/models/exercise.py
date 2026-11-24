from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.content import Content


class ExerciseType(str, enum.Enum):
    objetiva = "objetiva"
    discursiva = "discursiva"


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    content_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("contents.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[ExerciseType] = mapped_column(
        Enum(ExerciseType, name="exercise_type", native_enum=False), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    content: Mapped[Content] = relationship("Content", back_populates="exercises")
    alternatives: Mapped[list[ExerciseAlternative]] = relationship(
        "ExerciseAlternative", back_populates="exercise", cascade="all, delete-orphan"
    )
    attempts: Mapped[list[ExerciseAttempt]] = relationship(
        "ExerciseAttempt", back_populates="exercise", cascade="all, delete-orphan"
    )


class ExerciseAlternative(Base):
    __tablename__ = "exercise_alternatives"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    exercise: Mapped[Exercise] = relationship("Exercise", back_populates="alternatives")


class ExerciseAttempt(Base):
    __tablename__ = "exercise_attempts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False
    )
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_alternative_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("exercise_alternatives.id", ondelete="SET NULL"), nullable=True
    )
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="graded", nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    exercise: Mapped[Exercise] = relationship("Exercise", back_populates="attempts")
