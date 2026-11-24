from fastapi.testclient import TestClient


def _setup_content(client: TestClient) -> str:
    client.put(
        "/api/v1/settings",
        json={"deepseek_api_key": "sk-test-1234567890"},
    )
    course_id = client.post(
        "/api/v1/courses", json={"name": "Curso", "category": "TI"}
    ).json()["id"]
    topic_id = client.post(
        "/api/v1/topics",
        json={"course_id": course_id, "name": "Tópico", "level": "iniciante"},
    ).json()["id"]
    subject_id = client.post(
        "/api/v1/subjects",
        json={"topic_id": topic_id, "name": "Matéria", "level": "iniciante"},
    ).json()["id"]
    return client.post(
        "/api/v1/contents",
        json={"subject_id": subject_id, "title": "Conteúdo"},
    ).json()["id"]


def test_ai_generates_exercises_and_reviews_discursive(
    client: TestClient, monkeypatch
) -> None:
    content_id = _setup_content(client)

    def fake_exercises(**_kwargs):
        return {
            "exercises": [
                {
                    "type": "objetiva",
                    "question": "2+2?",
                    "explanation": "Soma básica",
                    "alternatives": [
                        {"text": "3", "is_correct": False},
                        {"text": "4", "is_correct": True},
                        {"text": "5", "is_correct": False},
                        {"text": "6", "is_correct": False},
                    ],
                },
                {
                    "type": "objetiva",
                    "question": "Alternativa inválida?",
                    "explanation": "Duas corretas",
                    "alternatives": [
                        {"text": "a", "is_correct": True},
                        {"text": "b", "is_correct": True},
                    ],
                },
                {
                    "type": "discursiva",
                    "question": "Explique a soma",
                    "explanation": "Deve citar adição de parcelas",
                    "alternatives": [],
                },
            ]
        }

    monkeypatch.setattr(
        "app.services.quiz_generator.generate_exercises_json", fake_exercises
    )

    response = client.post(
        f"/api/v1/contents/{content_id}/ai/exercises",
        json={"count": 3, "include_discursive": True},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    # Exercício inválido (2 corretas) é descartado.
    assert payload["created"] == 2

    exercises = client.get(f"/api/v1/contents/{content_id}/exercises").json()
    assert len(exercises) == 2
    discursive = next(item for item in exercises if item["type"] == "discursiva")
    objective = next(item for item in exercises if item["type"] == "objetiva")
    assert len(objective["alternatives"]) == 4

    attempt = client.post(
        f"/api/v1/exercises/{discursive['id']}/attempts",
        json={"answer_text": "Somei as parcelas."},
    ).json()
    assert attempt["status"] == "pending_review"

    monkeypatch.setattr(
        "app.services.quiz_generator.review_answer_json",
        lambda **_kwargs: {"score_ratio": 0.8, "feedback": "Boa resposta, faltou exemplo."},
    )
    review = client.post(f"/api/v1/exercises/attempts/{attempt['id']}/ai-review")
    assert review.status_code == 200, review.text
    body = review.json()
    assert body["status"] == "graded"
    assert body["is_correct"] is True


def test_ai_generates_exam_and_reviews(client: TestClient, monkeypatch) -> None:
    content_id = _setup_content(client)

    def fake_exam(**_kwargs):
        return {
            "title": "Prova de teste",
            "questions": [
                {
                    "type": "objetiva",
                    "question": "Capital do Brasil?",
                    "points": 2,
                    "alternatives": [
                        {"text": "São Paulo", "is_correct": False},
                        {"text": "Brasília", "is_correct": True},
                    ],
                },
                {
                    "type": "discursiva",
                    "question": "Explique a resposta",
                    "points": 2,
                    "alternatives": [],
                },
            ],
        }

    monkeypatch.setattr("app.services.quiz_generator.generate_exam_json", fake_exam)

    created = client.put(
        f"/api/v1/contents/{content_id}/ai/exam",
        json={"questions_count": 2, "discursive_count": 1},
    )
    assert created.status_code == 200, created.text
    assert created.json()["questions_created"] == 2

    exam = client.get(f"/api/v1/contents/{content_id}/exam").json()
    assert exam["title"] == "Prova de teste"
    objective = next(q for q in exam["questions"] if q["type"] == "objetiva")
    discursive = next(q for q in exam["questions"] if q["type"] == "discursiva")
    correct = next(
        alt for alt in objective["alternatives"] if alt["text"] == "Brasília"
    )

    attempt = client.post(
        f"/api/v1/contents/{content_id}/exam/attempts",
        json={
            "answers": [
                {
                    "question_id": objective["id"],
                    "selected_alternative_id": correct["id"],
                },
                {"question_id": discursive["id"], "answer_text": "Brasília é a capital."},
            ]
        },
    ).json()
    assert attempt["status"] == "pending_review"
    assert attempt["score"] == 2.0
    assert attempt["max_score"] == 4.0

    monkeypatch.setattr(
        "app.services.quiz_generator.review_answer_json",
        lambda **_kwargs: {"score_ratio": 1.0, "feedback": "Perfeito."},
    )
    review = client.post(f"/api/v1/exam-attempts/{attempt['id']}/ai-review")
    assert review.status_code == 200, review.text
    body = review.json()
    assert body["status"] == "graded"
    assert body["score"] == 4.0
