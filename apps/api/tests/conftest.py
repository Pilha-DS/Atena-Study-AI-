import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SKIP_DB_MIGRATIONS", "1")
os.environ.setdefault("ENRICH_CONCURRENCY", "1")
os.environ.setdefault("ENRICH_SYNC", "1")

from app.core.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: F401, E402
    AppSetting,
    Content,
    Course,
    Exam,
    ExamAlternative,
    ExamAnswer,
    ExamAttempt,
    ExamQuestion,
    Exercise,
    ExerciseAlternative,
    ExerciseAttempt,
    Material,
    Note,
    StudyTopic,
    Subject,
)


engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db: Session, monkeypatch) -> Generator[TestClient, None, None]:
    from app.services import background

    # Tarefas de background usam a mesma sessão/engine do teste.
    monkeypatch.setattr(background, "SessionLocal", TestingSessionLocal)

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
