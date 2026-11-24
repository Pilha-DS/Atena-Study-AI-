from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.level import LearnLevel

if TYPE_CHECKING:
    from app.models.content import Content
    from app.models.study_topic import StudyTopic


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("study_topics.id", ondelete="CASCADE"), nullable=False
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

    topic: Mapped[StudyTopic] = relationship("StudyTopic", back_populates="subjects")
    contents: Mapped[list[Content]] = relationship(
        "Content", back_populates="subject", cascade="all, delete-orphan"
    )
