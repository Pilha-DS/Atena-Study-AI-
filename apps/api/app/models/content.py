from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.exam import Exam
    from app.models.exercise import Exercise
    from app.models.material import Material
    from app.models.note import Note
    from app.models.subject import Subject


class ContentStatus(str, enum.Enum):
    pendente = "pendente"
    em_andamento = "em_andamento"
    concluido = "concluido"


class Content(Base):
    __tablename__ = "contents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, name="content_status", native_enum=False),
        default=ContentStatus.pendente,
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    subject: Mapped[Subject] = relationship("Subject", back_populates="contents")
    materials: Mapped[list[Material]] = relationship(
        "Material", back_populates="content", cascade="all, delete-orphan"
    )
    notes: Mapped[list[Note]] = relationship(
        "Note", back_populates="content", cascade="all, delete-orphan"
    )
    exercises: Mapped[list[Exercise]] = relationship(
        "Exercise", back_populates="content", cascade="all, delete-orphan"
    )
    exam: Mapped[Exam | None] = relationship(
        "Exam", back_populates="content", cascade="all, delete-orphan", uselist=False
    )
