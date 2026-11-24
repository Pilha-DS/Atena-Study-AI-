from __future__ import annotations

from typing import Any, Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.content import Content
from app.models.course import Course
from app.models.exam import Exam, ExamAnswer, ExamAttempt, ExamQuestion, ExamQuestionType
from app.models.exercise import Exercise, ExerciseAlternative, ExerciseAttempt, ExerciseType
from app.models.material import Material, MaterialType
from app.models.study_topic import StudyTopic
from app.models.subject import Subject
from app.services.deepseek import (
    generate_exam_json,
    generate_exercises_json,
    review_answer_json,
)
from app.services.exam_store import persist_exam
from app.services.material_writer import write_teaching_material
from app.services.settings_store import get_deepseek_config
from app.services.structure_generator import enrich_content_materials
from app.services.web_search import SearchHit, search_web, search_youtube


def _deepseek_config(db: Session) -> tuple[str, str, str]:
    config = get_deepseek_config(db)
    api_key = config["api_key"]
    if not api_key:
        raise ValueError("DeepSeek não configurada. Defina a API key em Configurações.")
    return (
        api_key,
        config["base_url"] or "https://api.deepseek.com",
        config["model"] or "deepseek-chat",
    )


def build_content_context(db: Session, content: Content) -> str:
    subject = db.get(Subject, content.subject_id)
    topic = db.get(StudyTopic, subject.topic_id) if subject else None
    course = db.get(Course, topic.course_id) if topic else None
    materials = list(
        db.scalars(
            select(Material)
            .where(Material.content_id == content.id, Material.type == MaterialType.text)
            .order_by(Material.created_at)
        ).all()
    )
    excerpt = "\n\n".join((m.body or "")[:1800] for m in materials)[:3000]

    lines = [
        f"Curso: {course.name if course else 'não informado'}",
        f"Categoria: {course.category if course else 'não informada'}",
        f"Tópico: {topic.name if topic else 'não informado'} ({topic.level.value if topic else 'iniciante'})",
        f"Matéria: {subject.name if subject else 'não informada'} ({subject.level.value if subject else 'iniciante'})",
        f"Conteúdo: {content.title}",
        f"Descrição: {content.description or 'sem descrição'}",
    ]
    if excerpt:
        lines.append(f"Material de estudo (trecho):\n{excerpt}")
    else:
        lines.append("Sem material de texto salvo; use conhecimento pedagógico sólido.")
    return "\n".join(lines)


def _clean_alternatives(raw: list[Any]) -> list[dict[str, Any]]:
    alternatives: list[dict[str, Any]] = []
    for alt in raw or []:
        text = str(alt.get("text") or "").strip()
        if not text:
            continue
        alternatives.append({"text": text, "is_correct": bool(alt.get("is_correct"))})
    return alternatives


def _validate_objective(alternatives: list[dict[str, Any]]) -> bool:
    return len(alternatives) >= 2 and sum(1 for a in alternatives if a["is_correct"]) == 1


def create_exercises_with_ai(
    db: Session,
    *,
    content_id: UUID,
    count: int = 3,
    include_discursive: bool = True,
    llm_callable=None,
    max_attempts: int = 2,
) -> list[Exercise]:
    content = db.get(Content, content_id)
    if content is None:
        raise ValueError("Conteúdo não encontrado")

    api_key, base_url, model = _deepseek_config(db)
    call_llm = llm_callable or generate_exercises_json

    first_type = "objetiva" if not include_discursive else "objetiva"
    created: list[Exercise] = []

    for _ in range(max_attempts):
        payload = call_llm(
            api_key=api_key,
            base_url=base_url,
            model=model,
            context=build_content_context(db, content),
            count=count,
            include_discursive=include_discursive,
        )
        raw_exercises = payload.get("exercises") or []
        for item in raw_exercises:
            type_value = str(item.get("type") or first_type).strip().lower()
            if type_value not in {"objetiva", "discursiva"}:
                type_value = first_type
            if type_value == "discursiva" and not include_discursive:
                continue
            question = str(item.get("question") or "").strip()
            if not question:
                continue
            alternatives = _clean_alternatives(item.get("alternatives", []))
            if type_value == "objetiva" and not _validate_objective(alternatives):
                continue
            if type_value == "discursiva":
                alternatives = []

            exercise = Exercise(
                content_id=content.id,
                type=ExerciseType(type_value),
                question=question,
                explanation=(item.get("explanation") or None),
            )
            db.add(exercise)
            db.flush()
            for alt in alternatives:
                db.add(
                    ExerciseAlternative(
                        exercise_id=exercise.id,
                        text=alt["text"],
                        is_correct=alt["is_correct"],
                    )
                )
            created.append(exercise)
            if len(created) >= count:
                break
        if created:
            # Evita duplicar exercícios ao repetir a chamada quando veio menos que o pedido.
            break

    db.commit()
    if not created:
        raise ValueError("A IA não retornou exercícios válidos. Tente novamente.")

    ids = [exercise.id for exercise in created]
    return list(
        db.scalars(
            select(Exercise)
            .where(Exercise.id.in_(ids))
            .options(selectinload(Exercise.alternatives))
        ).all()
    )


def create_exam_with_ai(
    db: Session,
    *,
    content_id: UUID,
    questions_count: int = 5,
    discursive_count: int = 1,
    llm_callable=None,
) -> Exam:
    content = db.get(Content, content_id)
    if content is None:
        raise ValueError("Conteúdo não encontrado")

    api_key, base_url, model = _deepseek_config(db)
    call_llm = llm_callable or generate_exam_json
    payload = call_llm(
        api_key=api_key,
        base_url=base_url,
        model=model,
        context=build_content_context(db, content),
        questions_count=questions_count,
        discursive_count=discursive_count,
    )

    valid_questions: list[dict[str, Any]] = []
    for item in payload.get("questions") or []:
        question = str(item.get("question") or "").strip()
        if not question:
            continue
        type_value = str(item.get("type") or "objetiva").strip().lower()
        if type_value not in {"objetiva", "discursiva"}:
            type_value = "objetiva"
        alternatives = _clean_alternatives(item.get("alternatives", []))
        if type_value == "objetiva" and not _validate_objective(alternatives):
            continue
        if type_value == "discursiva":
            alternatives = []
        valid_questions.append(
            {
                "type": type_value,
                "question": question,
                "points": float(item.get("points") or 1),
                "alternatives": alternatives,
            }
        )

    if not valid_questions:
        raise ValueError("A IA não retornou questões válidas. Tente novamente.")

    return persist_exam(
        db,
        content_id=content.id,
        title=str(payload.get("title") or f"Prova - {content.title}"),
        description=None,
        questions=valid_questions,
    )


def generate_materials_with_ai(
    db: Session,
    *,
    content_id: UUID,
    include_text: bool = True,
    include_video: bool = True,
    include_links: bool = True,
    search_callable: Callable[[str], list[SearchHit]] | None = None,
    youtube_callable: Callable[[str], list[SearchHit]] | None = None,
    writer_callable=None,
) -> list[UUID]:
    content = db.get(Content, content_id)
    if content is None:
        raise ValueError("Conteúdo não encontrado")

    api_key, base_url, model = _deepseek_config(db)
    subject = db.get(Subject, content.subject_id)
    topic = db.get(StudyTopic, subject.topic_id) if subject else None
    course = db.get(Course, topic.course_id) if topic else None

    return enrich_content_materials(
        db,
        content=content,
        category_name=course.category if course else "Geral",
        course_name=course.name if course else "Curso",
        subject_name=subject.name if subject else "Matéria",
        search_query=f"{content.title} {subject.name if subject else ''}".strip(),
        api_key=api_key,
        base_url=base_url,
        model=model,
        search_callable=search_callable or search_web,
        youtube_callable=youtube_callable if youtube_callable is not None else search_youtube,
        writer_callable=writer_callable or write_teaching_material,
        include_video=include_video,
        include_text=include_text,
        include_links=include_links,
    )


def review_exercise_attempt_with_ai(
    db: Session,
    *,
    attempt_id: UUID,
    llm_callable=None,
) -> ExerciseAttempt:
    attempt = db.get(ExerciseAttempt, attempt_id)
    if attempt is None:
        raise ValueError("Tentativa não encontrada")
    exercise = db.get(Exercise, attempt.exercise_id)
    if exercise is None:
        raise ValueError("Exercício não encontrado")
    if exercise.type != ExerciseType.discursiva:
        raise ValueError("Somente respostas discursivas podem ser revisadas pela IA")
    if not (attempt.answer_text or "").strip():
        raise ValueError("Tentativa sem resposta discursiva")

    api_key, base_url, model = _deepseek_config(db)
    call_llm = llm_callable or review_answer_json
    payload = call_llm(
        api_key=api_key,
        base_url=base_url,
        model=model,
        question=exercise.question,
        criteria=exercise.explanation,
        student_answer=attempt.answer_text or "",
    )

    try:
        ratio = float(payload.get("score_ratio") or 0)
    except (TypeError, ValueError):
        ratio = 0.0
    ratio = max(0.0, min(1.0, ratio))

    attempt.is_correct = ratio >= 0.6
    attempt.status = "graded"
    attempt.feedback = str(payload.get("feedback") or "").strip() or attempt.feedback
    db.commit()
    db.refresh(attempt)
    return attempt


def review_exam_attempt_with_ai(
    db: Session,
    *,
    attempt_id: UUID,
    llm_callable=None,
) -> ExamAttempt:
    attempt = db.get(ExamAttempt, attempt_id)
    if attempt is None:
        raise ValueError("Tentativa não encontrada")

    answers = list(
        db.scalars(
            select(ExamAnswer)
            .where(ExamAnswer.attempt_id == attempt.id)
            .options(selectinload(ExamAnswer.question))
        ).all()
    )
    discursive = [
        answer
        for answer in answers
        if answer.question is not None
        and answer.question.type == ExamQuestionType.discursiva
        and (answer.answer_text or "").strip()
    ]
    if not discursive:
        raise ValueError("Nenhuma resposta discursiva para revisar")

    api_key, base_url, model = _deepseek_config(db)
    call_llm = llm_callable or review_answer_json

    for answer in discursive:
        payload = call_llm(
            api_key=api_key,
            base_url=base_url,
            model=model,
            question=answer.question.question,
            criteria=None,
            student_answer=answer.answer_text or "",
        )
        try:
            ratio = float(payload.get("score_ratio") or 0)
        except (TypeError, ValueError):
            ratio = 0.0
        ratio = max(0.0, min(1.0, ratio))
        answer.is_correct = ratio >= 0.6
        answer.points_awarded = round((answer.question.points or 0) * ratio, 2)

    attempt.score = round(sum(a.points_awarded for a in answers), 2)
    attempt.status = "graded"
    db.commit()
    db.refresh(attempt)
    return attempt
