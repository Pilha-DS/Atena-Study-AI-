from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.course import Course
from app.schemas.ai import (
    AIGenerateExamRequest,
    AIGenerateExamResponse,
    AIGenerateExercisesRequest,
    AIGenerateExercisesResponse,
    AIGenerateMaterialsRequest,
    AIGenerateMaterialsResponse,
    AIScheduleMaterialsResponse,
    AIReviewExamResponse,
    AIReviewExerciseResponse,
    CourseEnrichmentStatus,
    CreateCourseAIRequest,
    CreateCourseAIResponse,
    GenerateStructureRequest,
    GenerateStructureResponse,
)
from app.services.background import run_course_enrichment
from app.services.quiz_generator import (
    create_exam_with_ai,
    create_exercises_with_ai,
    generate_materials_with_ai,
    review_exam_attempt_with_ai,
    review_exercise_attempt_with_ai,
)
from app.services.structure_generator import (
    count_content_enrichment,
    create_course_from_objective,
    generate_and_persist,
)

router = APIRouter(tags=["ai"])


@router.post(
    "/courses/ai/create",
    response_model=CreateCourseAIResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_course_with_ai(
    payload: CreateCourseAIRequest,
    db: Session = Depends(get_db),
) -> CreateCourseAIResponse:
    try:
        # Cria a estrutura rápido; materiais são gerados em background.
        result = create_course_from_objective(
            db,
            objective=payload.objective.strip(),
            preferred_category=(payload.category or "").strip() or None,
            include_contents=payload.include_contents,
            enrich_materials=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao consultar DeepSeek: {exc}",
        ) from exc

    assert result.course_id is not None
    materials_pending = payload.include_contents and result.contents_created > 0
    if materials_pending:
        run_course_enrichment(result.course_id)

    return CreateCourseAIResponse(
        course_id=result.course_id,
        course_name=result.course_name,
        course_category=result.course_category,
        topics_created=result.topics_created,
        subjects_created=result.subjects_created,
        contents_created=result.contents_created,
        materials_created=result.materials_created,
        materials_pending=materials_pending,
        topic_ids=result.topic_ids,
        subject_ids=result.subject_ids,
        content_ids=result.content_ids,
        material_ids=result.material_ids,
    )


@router.post(
    "/courses/{course_id}/ai/generate-structure",
    response_model=GenerateStructureResponse,
)
def generate_structure(
    course_id: UUID,
    payload: GenerateStructureRequest,
    db: Session = Depends(get_db),
) -> GenerateStructureResponse:
    if not db.get(Course, course_id):
        raise HTTPException(status_code=404, detail="Curso não encontrado")

    try:
        result = generate_and_persist(
            db,
            course_id=course_id,
            objective=payload.objective.strip(),
            include_contents=payload.include_contents,
            enrich_materials=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao consultar DeepSeek: {exc}",
        ) from exc

    materials_pending = payload.include_contents and result.contents_created > 0
    if materials_pending:
        run_course_enrichment(course_id)

    return GenerateStructureResponse(
        topics_created=result.topics_created,
        subjects_created=result.subjects_created,
        contents_created=result.contents_created,
        materials_created=result.materials_created,
        materials_pending=materials_pending,
        topic_ids=result.topic_ids,
        subject_ids=result.subject_ids,
        content_ids=result.content_ids,
        material_ids=result.material_ids,
    )


@router.get(
    "/courses/{course_id}/ai/materials-status",
    response_model=CourseEnrichmentStatus,
)
def materials_status(
    course_id: UUID,
    db: Session = Depends(get_db),
) -> CourseEnrichmentStatus:
    if not db.get(Course, course_id):
        raise HTTPException(status_code=404, detail="Curso não encontrado")
    total, pending = count_content_enrichment(db, course_id)
    return CourseEnrichmentStatus(
        total_contents=total,
        contents_with_materials=total - pending,
        pending_contents=pending,
    )


@router.post(
    "/courses/{course_id}/ai/materials",
    response_model=AIScheduleMaterialsResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def schedule_course_materials(
    course_id: UUID,
    db: Session = Depends(get_db),
) -> AIScheduleMaterialsResponse:
    if not db.get(Course, course_id):
        raise HTTPException(status_code=404, detail="Curso não encontrado")

    _, pending = count_content_enrichment(db, course_id)
    if pending > 0:
        run_course_enrichment(course_id)
    return AIScheduleMaterialsResponse(scheduled=pending > 0, pending_contents=pending)


def _handle_ai_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ValueError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Falha ao consultar DeepSeek: {exc}",
    )


@router.post(
    "/contents/{content_id}/ai/exercises",
    response_model=AIGenerateExercisesResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_exercises(
    content_id: UUID,
    payload: AIGenerateExercisesRequest,
    db: Session = Depends(get_db),
) -> AIGenerateExercisesResponse:
    try:
        exercises = create_exercises_with_ai(
            db,
            content_id=content_id,
            count=payload.count,
            include_discursive=payload.include_discursive,
        )
    except Exception as exc:  # noqa: BLE001
        raise _handle_ai_error(exc) from exc

    return AIGenerateExercisesResponse(
        created=len(exercises),
        exercise_ids=[exercise.id for exercise in exercises],
    )


@router.put(
    "/contents/{content_id}/ai/exam",
    response_model=AIGenerateExamResponse,
)
def generate_exam(
    content_id: UUID,
    payload: AIGenerateExamRequest,
    db: Session = Depends(get_db),
) -> AIGenerateExamResponse:
    try:
        exam = create_exam_with_ai(
            db,
            content_id=content_id,
            questions_count=payload.questions_count,
            discursive_count=payload.discursive_count,
        )
    except Exception as exc:  # noqa: BLE001
        raise _handle_ai_error(exc) from exc

    return AIGenerateExamResponse(
        exam_id=exam.id,
        title=exam.title,
        questions_created=len(exam.questions),
    )


@router.post(
    "/contents/{content_id}/ai/materials",
    response_model=AIGenerateMaterialsResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_materials(
    content_id: UUID,
    payload: AIGenerateMaterialsRequest,
    db: Session = Depends(get_db),
) -> AIGenerateMaterialsResponse:
    try:
        material_ids = generate_materials_with_ai(
            db,
            content_id=content_id,
            include_text=payload.include_text,
            include_video=payload.include_video,
            include_links=payload.include_links,
        )
    except Exception as exc:  # noqa: BLE001
        raise _handle_ai_error(exc) from exc

    return AIGenerateMaterialsResponse(
        created=len(material_ids),
        material_ids=material_ids,
    )


@router.post(
    "/exercises/attempts/{attempt_id}/ai-review",
    response_model=AIReviewExerciseResponse,
)
def review_exercise_attempt(
    attempt_id: UUID,
    db: Session = Depends(get_db),
) -> AIReviewExerciseResponse:
    try:
        attempt = review_exercise_attempt_with_ai(db, attempt_id=attempt_id)
    except Exception as exc:  # noqa: BLE001
        raise _handle_ai_error(exc) from exc

    return AIReviewExerciseResponse(
        attempt_id=attempt.id,
        is_correct=attempt.is_correct,
        status=attempt.status,
        feedback=attempt.feedback,
    )


@router.post(
    "/exam-attempts/{attempt_id}/ai-review",
    response_model=AIReviewExamResponse,
)
def review_exam_attempt(
    attempt_id: UUID,
    db: Session = Depends(get_db),
) -> AIReviewExamResponse:
    try:
        attempt = review_exam_attempt_with_ai(db, attempt_id=attempt_id)
    except Exception as exc:  # noqa: BLE001
        raise _handle_ai_error(exc) from exc

    return AIReviewExamResponse(
        attempt_id=attempt.id,
        score=attempt.score,
        max_score=attempt.max_score,
        status=attempt.status,
    )
