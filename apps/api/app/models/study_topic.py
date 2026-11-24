from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.level import LearnLevel

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.subject import Subject


class StudyTopic(Base):
    __tablename__ = "study_topics"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[LearnLevel] = mapped_column(
        Enum(LearnLevel, name="learn_level", native_enum=False),
        default=LearnLevel.iniciante,
        nullable=False,
    )
    unlocked_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    course: Mapped[Course] = relationship("Course", back_populates="topics")
    subjects: Mapped[list[Subject]] = relationship(
        "Subject", back_populates="topic", cascade="all, delete-orphan"
    )
