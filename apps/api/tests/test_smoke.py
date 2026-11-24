from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.course import Course
from app.services.settings_store import KEY_API_KEY, set_setting
from app.services.structure_generator import generate_and_persist
from app.services.web_search import SearchHit


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_full_hierarchy_flow(client: TestClient) -> None:
    course = client.post(
        "/api/v1/courses",
        json={
            "name": "Algoritmos",
            "category": "Ciência da Computação",
            "description": "Base",
        },
    )
    assert course.status_code == 201
    course_id = course.json()["id"]
    assert course.json()["category"] == "Ciência da Computação"

    topic = client.post(
        "/api/v1/topics",
        json={"course_id": course_id, "name": "Ordenação"},
    )
    assert topic.status_code == 201
    topic_id = topic.json()["id"]

    subject = client.post(
        "/api/v1/subjects",
        json={"topic_id": topic_id, "name": "Quicksort"},
    )
    assert subject.status_code == 201
    subject_id = subject.json()["id"]

    content = client.post(
        "/api/v1/contents",
        json={
            "subject_id": subject_id,
            "title": "Particionamento",
            "priority": 5,
            "status": "em_andamento",
        },
    )
    assert content.status_code == 201
    content_id = content.json()["id"]

    material = client.post(
        f"/api/v1/contents/{content_id}/materials",
        json={
            "type": "video",
            "title": "Aula Quicksort",
            "url_or_path": "https://example.com/quicksort",
        },
    )
    assert material.status_code == 201

    note = client.post(
        f"/api/v1/contents/{content_id}/notes",
        json={"body": "Particionar e recursão"},
    )
    assert note.status_code == 201

    dashboard = client.get("/api/v1/dashboard")
    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert payload["total_courses"] == 1
    assert payload["total_topics"] == 1
    assert payload["total_subjects"] == 1
    assert payload["total_contents"] == 1
    assert payload["status_counts"]["em_andamento"] == 1
    assert len(payload["high_priority"]) == 1
    assert len(payload["active_courses"]) == 1
    assert payload["active_courses"][0]["id"] == course_id
    assert payload["active_courses"][0]["progress_percent"] == 0

    filtered = client.get("/api/v1/courses", params={"category": "Ciência da Computação"})
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert len(filtered.json()["items"]) == 1

    search = client.get("/api/v1/search", params={"q": "Particion"})
    assert search.status_code == 200
    assert len(search.json()["results"]) >= 1

    updated = client.patch(
        f"/api/v1/contents/{content_id}",
        json={"status": "concluido"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "concluido"

    dashboard_done = client.get("/api/v1/dashboard").json()
    assert dashboard_done["active_courses"][0]["progress_percent"] == 100

    deleted = client.delete(f"/api/v1/courses/{course_id}")
    assert deleted.status_code == 204
    assert client.get("/api/v1/courses").json()["items"] == []


def test_courses_list_is_paginated_on_backend(client: TestClient) -> None:
    for index in range(12):
        client.post(
            "/api/v1/courses",
            json={"name": f"Curso {index:02d}", "category": "Geral"},
        )

    first = client.get("/api/v1/courses").json()
    assert first["total"] == 12
    assert first["limit"] == 10
    assert first["offset"] == 0
    assert len(first["items"]) == 10
    assert first["categories"] == ["Geral"]

    second = client.get("/api/v1/courses", params={"limit": 10, "offset": 10}).json()
    assert len(second["items"]) == 2
    assert second["offset"] == 10

    first_ids = {course["id"] for course in first["items"]}
    second_ids = {course["id"] for course in second["items"]}
    assert first_ids.isdisjoint(second_ids)


def test_dashboard_only_lists_courses_with_progress(client: TestClient) -> None:
    def make_course(name: str, status: str) -> str:
        course_id = client.post(
            "/api/v1/courses", json={"name": name, "category": "Geral"}
        ).json()["id"]
        topic_id = client.post(
            "/api/v1/topics", json={"course_id": course_id, "name": f"Tópico {name}"}
        ).json()["id"]
        subject_id = client.post(
            "/api/v1/subjects", json={"topic_id": topic_id, "name": f"Matéria {name}"}
        ).json()["id"]
        client.post(
            "/api/v1/contents",
            json={"subject_id": subject_id, "title": f"Conteúdo {name}", "status": status},
        )
        return course_id

    started = make_course("Em andamento", "em_andamento")
    make_course("Pendente", "pendente")

    payload = client.get("/api/v1/dashboard").json()
    active_ids = [course["id"] for course in payload["active_courses"]]
    assert active_ids == [started]
    assert payload["total_courses"] == 2


def test_exercise_objective_attempt(client: TestClient) -> None:
    course_id = client.post(
        "/api/v1/courses", json={"name": "Curso", "category": "Geral"}
    ).json()["id"]
    topic_id = client.post(
        "/api/v1/topics", json={"course_id": course_id, "name": "Tópico"}
    ).json()["id"]
    subject_id = client.post(
        "/api/v1/subjects", json={"topic_id": topic_id, "name": "Matéria"}
    ).json()["id"]
    content_id = client.post(
        "/api/v1/contents",
        json={"subject_id": subject_id, "title": "Conteúdo"},
    ).json()["id"]

    exercise = client.post(
        f"/api/v1/contents/{content_id}/exercises",
        json={
            "type": "objetiva",
            "question": "2+2?",
            "alternatives": [
                {"text": "3", "is_correct": False},
                {"text": "4", "is_correct": True},
            ],
        },
    )
    assert exercise.status_code == 201
    exercise_id = exercise.json()["id"]
    wrong_id = exercise.json()["alternatives"][0]["id"]
    correct_id = exercise.json()["alternatives"][1]["id"]

    wrong = client.post(
        f"/api/v1/exercises/{exercise_id}/attempts",
        json={"selected_alternative_id": wrong_id},
    )
    assert wrong.status_code == 201
    assert wrong.json()["is_correct"] is False

    right = client.post(
        f"/api/v1/exercises/{exercise_id}/attempts",
        json={"selected_alternative_id": correct_id},
    )
    assert right.status_code == 201
    assert right.json()["is_correct"] is True
    assert right.json()["status"] == "graded"


def test_exam_attempt(client: TestClient) -> None:
    course_id = client.post(
        "/api/v1/courses", json={"name": "Curso", "category": "Geral"}
    ).json()["id"]
    topic_id = client.post(
        "/api/v1/topics", json={"course_id": course_id, "name": "Tópico"}
    ).json()["id"]
    subject_id = client.post(
        "/api/v1/subjects", json={"topic_id": topic_id, "name": "Matéria"}
    ).json()["id"]
    content_id = client.post(
        "/api/v1/contents",
        json={"subject_id": subject_id, "title": "Conteúdo"},
    ).json()["id"]

    exam = client.put(
        f"/api/v1/contents/{content_id}/exam",
        json={
            "title": "Prova 1",
            "questions": [
                {
                    "type": "objetiva",
                    "question": "Capital?",
                    "points": 1,
                    "alternatives": [
                        {"text": "SP", "is_correct": False},
                        {"text": "Brasília", "is_correct": True},
                    ],
                },
                {
                    "type": "discursiva",
                    "question": "Explique",
                    "points": 1,
                    "alternatives": [],
                },
            ],
        },
    )
    assert exam.status_code == 200
    questions = exam.json()["questions"]
    q_obj = questions[0]
    q_disc = questions[1]
    correct_alt = next(a for a in q_obj["alternatives"] if a["is_correct"])

    attempt = client.post(
        f"/api/v1/contents/{content_id}/exam/attempts",
        json={
            "answers": [
                {
                    "question_id": q_obj["id"],
                    "selected_alternative_id": correct_alt["id"],
                },
                {"question_id": q_disc["id"], "answer_text": "Resposta aberta"},
            ]
        },
    )
    assert attempt.status_code == 201
    body = attempt.json()
    assert body["score"] == 1.0
    assert body["max_score"] == 2.0
    assert body["status"] == "pending_review"


def test_ai_generate_structure_with_mock(db: Session) -> None:
    course = Course(name="Redes", category="TI", description="Fundamentos")
    db.add(course)
    set_setting(db, KEY_API_KEY, "test-key")
    db.commit()
    db.refresh(course)

    def mock_llm(**_kwargs):
        return {
            "topics": [
                {
                    "name": "Camada de Rede",
                    "description": "IP e roteamento",
                    "subjects": [
                        {
                            "name": "IPv4",
                            "description": "Endereçamento",
                            "contents": [
                                {
                                    "title": "Máscara de sub-rede",
                                    "description": "CIDR",
                                    "search_query": "máscara de sub-rede tutorial",
                                }
                            ],
                        }
                    ],
                }
            ]
        }

    def mock_search(_query: str) -> list[SearchHit]:
        return [
            SearchHit(
                title="Tutorial CIDR",
                url="https://example.com/cidr",
                snippet="Explicação didática",
            )
        ]

    def mock_writer(**_kwargs):
        return {
            "material_title": "Máscara explicada",
            "body": "Texto didático sobre máscaras.",
            "reference_links": [{"title": "CIDR", "url": "https://example.com/cidr"}],
        }

    result = generate_and_persist(
        db,
        course_id=course.id,
        objective="Aprender fundamentos de redes IPv4",
        include_contents=True,
        llm_callable=mock_llm,
        search_callable=mock_search,
        youtube_callable=lambda _query: [],
        writer_callable=mock_writer,
    )

    assert result.topics_created == 1
    assert result.subjects_created == 1
    assert result.contents_created == 1
    assert result.materials_created >= 1
    assert "courses" not in mock_llm()
