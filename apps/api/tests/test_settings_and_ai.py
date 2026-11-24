from fastapi.testclient import TestClient

from app.services.web_search import SearchHit


def test_settings_crud(client: TestClient) -> None:
    initial = client.get("/api/v1/settings")
    assert initial.status_code == 200
    assert initial.json()["deepseek_configured"] is False

    updated = client.put(
        "/api/v1/settings",
        json={
            "deepseek_api_key": "sk-test-1234567890",
            "deepseek_base_url": "https://api.deepseek.com",
            "deepseek_model": "deepseek-chat",
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["deepseek_configured"] is True
    assert body["deepseek_api_key_masked"] is not None
    assert "sk-t" in body["deepseek_api_key_masked"]
    assert body["deepseek_model"] == "deepseek-chat"

    cleared = client.put("/api/v1/settings", json={"clear_api_key": True})
    assert cleared.status_code == 200
    assert cleared.json()["deepseek_configured"] is False


def test_generate_structure_requires_key(client: TestClient) -> None:
    course = client.post(
        "/api/v1/courses",
        json={"name": "Redes", "category": "TI"},
    ).json()
    response = client.post(
        f"/api/v1/courses/{course['id']}/ai/generate-structure",
        json={"objective": "Aprender redes do zero ao avançado"},
    )
    assert response.status_code == 400
    assert "DeepSeek" in response.json()["detail"]


def test_create_course_with_ai_requires_key(client: TestClient) -> None:
    response = client.post(
        "/api/v1/courses/ai/create",
        json={"objective": "Aprender redes do zero ao avançado"},
    )
    assert response.status_code == 400
    assert "DeepSeek" in response.json()["detail"]


def test_generate_structure_with_mock(client: TestClient, monkeypatch) -> None:
    client.put(
        "/api/v1/settings",
        json={"deepseek_api_key": "sk-test-1234567890"},
    )
    course = client.post(
        "/api/v1/courses",
        json={"name": "Programação", "category": "TI"},
    ).json()

    def fake_llm(**kwargs):
        return {
            "topics": [
                {
                    "name": "Fundamentos",
                    "description": "Base",
                    "subjects": [
                        {
                            "name": "Variáveis",
                            "description": "Tipos",
                            "contents": [
                                {
                                    "title": "Tipos primitivos",
                                    "description": "Intro",
                                    "search_query": "tipos primitivos programação",
                                },
                                {
                                    "title": "Escopo",
                                    "description": "Local vs global",
                                    "search_query": "escopo variáveis programação",
                                },
                            ],
                        },
                        {
                            "name": "Controle de fluxo",
                            "description": "Condicionais",
                            "contents": [
                                {
                                    "title": "If/else",
                                    "description": "Decisões",
                                    "search_query": "if else explicação didática",
                                }
                            ],
                        },
                    ],
                }
            ]
        }

    def fake_search(query: str):
        return [
            SearchHit(
                title="Aula didática",
                url="https://example.com/aula",
                snippet=f"Explicação sobre {query}",
            )
        ]

    def fake_writer(**kwargs):
        return {
            "material_title": f"Texto: {kwargs['content_title']}",
            "body": (
                "## Objetivo\nAprender o tema.\n\n## Explicação\nConteúdo didático real "
                "com exemplos e analogias para estudo.\n\n## Mini exercício\nPratique o conceito."
            ),
            "reference_links": [{"title": "Referência", "url": "https://example.com/aula"}],
        }

    monkeypatch.setattr(
        "app.services.structure_generator.generate_study_structure",
        fake_llm,
    )
    monkeypatch.setattr("app.services.structure_generator.search_web", fake_search)
    monkeypatch.setattr(
        "app.services.structure_generator.search_youtube", lambda _query: []
    )
    monkeypatch.setattr(
        "app.services.structure_generator.write_teaching_material",
        fake_writer,
    )

    response = client.post(
        f"/api/v1/courses/{course['id']}/ai/generate-structure",
        json={"objective": "Aprender programação básica", "include_contents": True},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["topics_created"] == 1
    assert payload["subjects_created"] == 2
    assert payload["contents_created"] == 3
    # Materiais são gerados em background (TestClient executa antes de retornar).
    assert payload["materials_pending"] is True

    topics = client.get("/api/v1/topics", params={"course_id": course["id"]}).json()
    assert len(topics) == 1
    subjects = client.get("/api/v1/subjects", params={"topic_id": topics[0]["id"]}).json()
    assert len(subjects) == 2
    assert all(item["topic_id"] == topics[0]["id"] for item in subjects)

    content_id = payload["content_ids"][0]
    materials = client.get(f"/api/v1/contents/{content_id}/materials").json()
    assert len(materials) >= 1
    assert any(item["type"] == "text" and item["body"] for item in materials)


def test_create_course_with_ai_mock(client: TestClient, monkeypatch) -> None:
    client.put(
        "/api/v1/settings",
        json={"deepseek_api_key": "sk-test-1234567890"},
    )

    def fake_llm(**kwargs):
        return {
            "course": {
                "name": "Redes do Zero",
                "category": "TI",
                "description": "Fundamentos de redes",
            },
            "topics": [
                {
                    "name": "Introdução",
                    "description": "Base",
                    "subjects": [
                        {
                            "name": "Modelo OSI",
                            "description": "Camadas",
                            "contents": [
                                {
                                    "title": "Camada de rede",
                                    "description": "IP",
                                    "search_query": "modelo OSI camada rede",
                                }
                            ],
                        }
                    ],
                }
            ],
        }

    def fake_search(query: str):
        return [
            SearchHit(
                title="Aula",
                url="https://example.com/osi",
                snippet=f"Sobre {query}",
            )
        ]

    def fake_writer(**kwargs):
        return {
            "material_title": f"Texto: {kwargs['content_title']}",
            "body": "## Objetivo\nEstudar redes.\n\n## Explicação\nConteúdo didático.",
            "reference_links": [{"title": "Ref", "url": "https://example.com/osi"}],
        }

    monkeypatch.setattr(
        "app.services.structure_generator.generate_course_from_objective",
        fake_llm,
    )
    monkeypatch.setattr("app.services.structure_generator.search_web", fake_search)
    monkeypatch.setattr(
        "app.services.structure_generator.search_youtube", lambda _query: []
    )
    monkeypatch.setattr(
        "app.services.structure_generator.write_teaching_material",
        fake_writer,
    )

    response = client.post(
        "/api/v1/courses/ai/create",
        json={
            "objective": "Quero aprender redes de computadores do zero",
            "category": "TI",
            "include_contents": True,
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["course_name"] == "Redes do Zero"
    assert payload["course_category"] == "TI"
    assert payload["topics_created"] == 1
    assert payload["subjects_created"] == 1
    assert payload["contents_created"] == 1

    course = client.get(f"/api/v1/courses/{payload['course_id']}")
    assert course.status_code == 200
    assert course.json()["name"] == "Redes do Zero"
