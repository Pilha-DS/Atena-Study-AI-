from fastapi import APIRouter

from app.api.v1 import (
    ai,
    contents,
    courses,
    dashboard,
    exams,
    exercises,
    materials,
    notes,
    search,
    settings,
    subjects,
    topics,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(courses.router)
api_router.include_router(topics.router)
api_router.include_router(subjects.router)
api_router.include_router(contents.router)
api_router.include_router(materials.router)
api_router.include_router(notes.router)
api_router.include_router(exercises.router)
api_router.include_router(exams.router)
api_router.include_router(dashboard.router)
api_router.include_router(search.router)
api_router.include_router(settings.router)
api_router.include_router(ai.router)
