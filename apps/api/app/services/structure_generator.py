from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.content import Content
from app.models.course import Course
from app.models.level import normalize_level
from app.models.material import Material, MaterialType
from app.models.study_topic import StudyTopic
from app.models.subject import Subject
from app.services.deepseek import generate_course_from_objective, generate_study_structure
from app.services.material_writer import write_teaching_material
from app.services.settings_store import get_deepseek_config
from app.services.web_search import (
    SearchHit,
    normalize_youtube_url,
    search_web,
    search_youtube,
)

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    topics_created: int
    subjects_created: int
    contents_created: int
    materials_created: int
    topic_ids: list[UUID] = field(default_factory=list)
    subject_ids: list[UUID] = field(default_factory=list)
    content_ids: list[UUID] = field(default_factory=list)
    material_ids: list[UUID] = field(default_factory=list)
    course_id: UUID | None = None


@dataclass
class CreateCourseResult(GenerationResult):
    course_name: str = ""
    course_category: str = ""


def _existing_summary(db: Session, course_id: UUID) -> str:
    topics = list(
        db.scalars(
            select(StudyTopic).where(StudyTopic.course_id == course_id).order_by(StudyTopic.name)
        ).all()
    )
    if not topics:
        return ""
    lines: list[str] = []
    for topic in topics:
        subjects = list(
            db.scalars(
                select(Subject).where(Subject.topic_id == topic.id).order_by(Subject.name)
            ).all()
        )
        subject_names = ", ".join(
            f"{s.name} [{s.level.value}]" for s in subjects
        ) or "sem matérias"
        lines.append(
            f"- Tópico: {topic.name} [{topic.level.value}] | Matérias: {subject_names}"
        )
    return "\n".join(lines)


def _youtube_hits_from(
    hits: list[SearchHit], *, limit: int = 2
) -> list[SearchHit]:
    videos: list[SearchHit] = []
    seen: set[str] = set()
    for hit in hits:
        url = normalize_youtube_url(hit.url)
        if not url or url in seen:
            continue
        seen.add(url)
        videos.append(SearchHit(title=hit.title, url=url, snippet=hit.snippet))
        if len(videos) >= limit:
            break
    return videos


def enrich_content_materials(
    db: Session,
    *,
    content: Content,
    category_name: str,
    course_name: str,
    subject_name: str,
    search_query: str,
    api_key: str,
    base_url: str,
    model: str,
    search_callable: Callable[[str], list[SearchHit]] | None = None,
    youtube_callable: Callable[[str], list[SearchHit]] | None = None,
    writer_callable=None,
    include_video: bool = True,
    include_text: bool = True,
    include_links: bool = True,
) -> list[UUID]:
    search_fn = search_callable or search_web
    query = search_query.strip() or f"{content.title} {subject_name} explicação didática"
    hits = search_fn(query)
    writer_fn = writer_callable or write_teaching_material
    material_payload = writer_fn(
        api_key=api_key,
        base_url=base_url,
        model=model,
        category_name=category_name,
        course_name=course_name,
        subject_name=subject_name,
        content_title=content.title,
        content_description=content.description,
        search_hits=hits,
    )

    created_ids: list[UUID] = []
    body = (material_payload.get("body") or "").strip()
    material_title = (material_payload.get("material_title") or content.title).strip()
    if include_text and body:
        text_material = Material(
            content_id=content.id,
            type=MaterialType.text,
            title=material_title[:255],
            body=body,
        )
        db.add(text_material)
        db.flush()
        created_ids.append(text_material.id)

    for link in material_payload.get("reference_links", [])[:3]:
        if not include_links:
            break
        url = (link.get("url") or "").strip()
        title = (link.get("title") or "Referência").strip()
        if not url.startswith("http"):
            continue
        youtube_url = normalize_youtube_url(url)
        link_material = Material(
            content_id=content.id,
            type=MaterialType.video if youtube_url else MaterialType.link,
            title=title[:255],
            url_or_path=(youtube_url or url)[:1024],
            body=None,
        )
        db.add(link_material)
        db.flush()
        created_ids.append(link_material.id)

    if include_video:
        video_pool = _youtube_hits_from(hits, limit=2)
        if len(video_pool) < 2:
            video_fn = youtube_callable or search_youtube
            existing = {(video.url, video.title) for video in video_pool}
            for video in video_fn(query)[:2]:
                if (video.url, video.title) in existing:
                    continue
                video_pool.append(video)
                if len(video_pool) >= 2:
                    break
        for video in video_pool[:2]:
            video_url = normalize_youtube_url(video.url)
            if not video_url:
                continue
            video_material = Material(
                content_id=content.id,
                type=MaterialType.video,
                title=(video.title or "Aula em vídeo")[:255],
                url_or_path=video_url[:1024],
                body=video.snippet or None,
            )
            db.add(video_material)
            db.flush()
            created_ids.append(video_material.id)

    if not created_ids and include_links:
        for hit in hits[:3]:
            if not hit.url.startswith("http"):
                continue
            link_material = Material(
                content_id=content.id,
                type=MaterialType.link,
                title=(hit.title or "Referência")[:255],
                url_or_path=hit.url[:1024],
                body=hit.snippet or None,
            )
            db.add(link_material)
            db.flush()
            created_ids.append(link_material.id)

    return created_ids


def persist_generated_structure(
    db: Session,
    *,
    course: Course,
    payload: dict[str, Any],
    include_contents: bool,
    api_key: str | None = None,
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
    enrich_materials: bool = True,
    search_callable: Callable[[str], list[SearchHit]] | None = None,
    youtube_callable: Callable[[str], list[SearchHit]] | None = None,
    writer_callable=None,
) -> GenerationResult:
    topics_created = 0
    subjects_created = 0
    contents_created = 0
    materials_created = 0
    topic_ids: list[UUID] = []
    subject_ids: list[UUID] = []
    content_ids: list[UUID] = []
    material_ids: list[UUID] = []
    search_fn = search_callable or search_web
    video_fn = youtube_callable if youtube_callable is not None else search_youtube
    writer_fn = writer_callable or write_teaching_material

    for topic_index, topic_data in enumerate(payload.get("topics", [])):
        name = (topic_data.get("name") or "").strip()
        if not name:
            continue
        topic = StudyTopic(
            course_id=course.id,
            name=name,
            description=(topic_data.get("description") or None),
            level=normalize_level(topic_data.get("level")),
            sort_order=topic_index,
        )
        db.add(topic)
        db.flush()
        topic_ids.append(topic.id)
        topics_created += 1

        for subject_index, subject_data in enumerate(topic_data.get("subjects", [])):
            subject_name = (subject_data.get("name") or "").strip()
            if not subject_name:
                continue
            subject = Subject(
                topic_id=topic.id,
                name=subject_name,
                description=(subject_data.get("description") or None),
                level=normalize_level(subject_data.get("level")),
                sort_order=subject_index,
            )
            db.add(subject)
            db.flush()
            subject_ids.append(subject.id)
            subjects_created += 1

            if not include_contents:
                continue
            for content_data in subject_data.get("contents", []):
                title = (content_data.get("title") or "").strip()
                if not title:
                    continue
                content = Content(
                    subject_id=subject.id,
                    title=title,
                    description=(content_data.get("description") or None),
                )
                db.add(content)
                db.flush()
                content_ids.append(content.id)
                contents_created += 1

                if enrich_materials and api_key:
                    created = enrich_content_materials(
                        db,
                        content=content,
                        category_name=course.category,
                        course_name=course.name,
                        subject_name=subject.name,
                        search_query=str(content_data.get("search_query") or ""),
                        api_key=api_key,
                        base_url=base_url,
                        model=model,
                        search_callable=search_fn,
                        youtube_callable=video_fn,
                        writer_callable=writer_fn,
                    )
                    material_ids.extend(created)
                    materials_created += len(created)

    db.commit()
    return GenerationResult(
        topics_created=topics_created,
        subjects_created=subjects_created,
        contents_created=contents_created,
        materials_created=materials_created,
        topic_ids=topic_ids,
        subject_ids=subject_ids,
        content_ids=content_ids,
        material_ids=material_ids,
    )


def generate_and_persist(
    db: Session,
    *,
    course_id: UUID,
    objective: str,
    include_contents: bool,
    enrich_materials: bool | None = None,
    llm_callable=None,
    search_callable: Callable[[str], list[SearchHit]] | None = None,
    youtube_callable: Callable[[str], list[SearchHit]] | None = None,
    writer_callable=None,
) -> GenerationResult:
    course = db.get(Course, course_id)
    if course is None:
        raise ValueError("Curso não encontrado")

    config = get_deepseek_config(db)
    api_key = config["api_key"]
    if not api_key:
        raise ValueError("DeepSeek não configurada. Defina a API key em Configurações.")

    base_url = config["base_url"] or "https://api.deepseek.com"
    model = config["model"] or "deepseek-chat"

    call_llm = llm_callable or generate_study_structure
    payload = call_llm(
        api_key=api_key,
        base_url=base_url,
        model=model,
        course_name=course.name,
        course_category=course.category,
        course_description=course.description,
        objective=objective,
        existing_summary=_existing_summary(db, course_id),
        include_contents=include_contents,
    )
    if not isinstance(payload, dict) or "topics" not in payload:
        raise ValueError("Resposta da IA inválida: JSON sem tópicos")

    return persist_generated_structure(
        db,
        course=course,
        payload=payload,
        include_contents=include_contents,
        api_key=api_key,
        base_url=base_url,
        model=model,
        enrich_materials=include_contents if enrich_materials is None else enrich_materials,
        search_callable=search_callable,
        youtube_callable=youtube_callable,
        writer_callable=writer_callable,
    )


def create_course_from_objective(
    db: Session,
    *,
    objective: str,
    preferred_category: str | None = None,
    include_contents: bool = True,
    enrich_materials: bool | None = None,
    llm_callable=None,
    search_callable: Callable[[str], list[SearchHit]] | None = None,
    youtube_callable: Callable[[str], list[SearchHit]] | None = None,
    writer_callable=None,
) -> CreateCourseResult:
    config = get_deepseek_config(db)
    api_key = config["api_key"]
    if not api_key:
        raise ValueError("DeepSeek não configurada. Defina a API key em Configurações.")

    base_url = config["base_url"] or "https://api.deepseek.com"
    model = config["model"] or "deepseek-chat"

    call_llm = llm_callable or generate_course_from_objective
    payload = call_llm(
        api_key=api_key,
        base_url=base_url,
        model=model,
        objective=objective,
        preferred_category=preferred_category,
        include_contents=include_contents,
    )
    if not isinstance(payload, dict) or "topics" not in payload:
        raise ValueError("Resposta da IA inválida: JSON sem tópicos")

    course_data = payload.get("course") or {}
    name = (course_data.get("name") or "").strip() or objective.strip()[:80]
    category = (
        (preferred_category or "").strip()
        or (course_data.get("category") or "").strip()
        or "Geral"
    )
    description = (course_data.get("description") or None)

    course = Course(name=name[:255], category=category[:255], description=description)
    db.add(course)
    db.flush()

    result = persist_generated_structure(
        db,
        course=course,
        payload=payload,
        include_contents=include_contents,
        api_key=api_key,
        base_url=base_url,
        model=model,
        enrich_materials=include_contents if enrich_materials is None else enrich_materials,
        search_callable=search_callable,
        youtube_callable=youtube_callable,
        writer_callable=writer_callable,
    )
    return CreateCourseResult(
        topics_created=result.topics_created,
        subjects_created=result.subjects_created,
        contents_created=result.contents_created,
        materials_created=result.materials_created,
        topic_ids=result.topic_ids,
        subject_ids=result.subject_ids,
        content_ids=result.content_ids,
        material_ids=result.material_ids,
        course_id=course.id,
        course_name=course.name,
        course_category=course.category,
    )


@dataclass
class EnrichmentResult:
    contents_processed: int = 0
    contents_pending: int = 0
    materials_created: int = 0


def _course_contents(db: Session, course_id: UUID) -> list[Content]:
    return list(
        db.scalars(
            select(Content)
            .join(Subject, Content.subject_id == Subject.id)
            .join(StudyTopic, Subject.topic_id == StudyTopic.id)
            .where(StudyTopic.course_id == course_id)
            .order_by(Content.created_at, Content.title)
        ).all()
    )


def content_has_text_material(db: Session, content_id: UUID) -> bool:
    return (
        db.scalar(
            select(func.count())
            .select_from(Material)
            .where(Material.content_id == content_id, Material.type == MaterialType.text)
        )
        or 0
    ) > 0


def count_content_enrichment(db: Session, course_id: UUID) -> tuple[int, int]:
    """Retorna (total de conteúdos, conteúdos ainda sem material de texto)."""
    contents = _course_contents(db, course_id)
    enriched = db.scalars(
        select(Material.content_id)
        .join(Content, Content.id == Material.content_id)
        .join(Subject, Content.subject_id == Subject.id)
        .join(StudyTopic, Subject.topic_id == StudyTopic.id)
        .where(StudyTopic.course_id == course_id, Material.type == MaterialType.text)
        .distinct()
    ).all()
    enriched_ids = set(enriched)
    pending = sum(1 for content in contents if content.id not in enriched_ids)
    return len(contents), pending


def pending_content_ids(db: Session, course_id: UUID) -> list[UUID]:
    contents = _course_contents(db, course_id)
    enriched = set(
        db.scalars(
            select(Material.content_id)
            .join(Content, Content.id == Material.content_id)
            .join(Subject, Content.subject_id == Subject.id)
            .join(StudyTopic, Subject.topic_id == StudyTopic.id)
            .where(StudyTopic.course_id == course_id, Material.type == MaterialType.text)
            .distinct()
        ).all()
    )
    return [content.id for content in contents if content.id not in enriched]


def enrich_content_by_id(
    db: Session,
    content_id: UUID,
    *,
    search_callable: Callable[[str], list[SearchHit]] | None = None,
    youtube_callable: Callable[[str], list[SearchHit]] | None = None,
    writer_callable=None,
) -> int:
    """Gera materiais de um conteúdo (uma sessão por conteúdo)."""
    content = db.get(Content, content_id)
    if content is None:
        return 0

    subject = db.get(Subject, content.subject_id)
    topic = db.get(StudyTopic, subject.topic_id) if subject else None
    course = db.get(Course, topic.course_id) if topic else None

    config = get_deepseek_config(db)
    api_key = config["api_key"]
    if not api_key:
        raise ValueError("DeepSeek não configurada. Defina a API key em Configurações.")

    created = enrich_content_materials(
        db,
        content=content,
        category_name=course.category if course else "Geral",
        course_name=course.name if course else "Curso",
        subject_name=subject.name if subject else "Matéria",
        search_query=f"{content.title} {subject.name if subject else ''}".strip(),
        api_key=api_key,
        base_url=config["base_url"] or "https://api.deepseek.com",
        model=config["model"] or "deepseek-chat",
        search_callable=search_callable,
        youtube_callable=youtube_callable,
        writer_callable=writer_callable,
    )
    db.commit()
    return len(created)


def enrich_course_contents(
    db: Session,
    *,
    course_id: UUID,
    only_missing: bool = True,
    max_contents: int | None = None,
    search_callable: Callable[[str], list[SearchHit]] | None = None,
    youtube_callable: Callable[[str], list[SearchHit]] | None = None,
    writer_callable=None,
) -> EnrichmentResult:
    """Gera materiais (texto markdown + vídeos pt-BR) para os conteúdos do curso.

    Usado em background após criar a estrutura, para o usuário receber o curso
    imediatamente. Faz commit por conteúdo, então o progresso fica visível.
    """
    course = db.get(Course, course_id)
    if course is None:
        return EnrichmentResult()

    config = get_deepseek_config(db)
    api_key = config["api_key"]
    if not api_key:
        raise ValueError("DeepSeek não configurada. Defina a API key em Configurações.")
    base_url = config["base_url"] or "https://api.deepseek.com"
    model = config["model"] or "deepseek-chat"

    search_fn = search_callable or search_web
    video_fn = youtube_callable if youtube_callable is not None else search_youtube
    writer_fn = writer_callable or write_teaching_material

    contents = _course_contents(db, course_id)
    result = EnrichmentResult()

    for content in contents:
        if max_contents is not None and result.contents_processed >= max_contents:
            result.contents_pending += 1
            continue
        if only_missing and content_has_text_material(db, content.id):
            continue

        subject = db.get(Subject, content.subject_id)
        try:
            created = enrich_content_materials(
                db,
                content=content,
                category_name=course.category,
                course_name=course.name,
                subject_name=subject.name if subject else course.name,
                search_query=f"{content.title} {subject.name if subject else ''}".strip(),
                api_key=api_key,
                base_url=base_url,
                model=model,
                search_callable=search_fn,
                youtube_callable=video_fn,
                writer_callable=writer_fn,
            )
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
            logger.exception("Falha ao gerar materiais do conteúdo %s", content.id)
            result.contents_pending += 1
            continue

        result.contents_processed += 1
        result.materials_created += len(created)

    return result
