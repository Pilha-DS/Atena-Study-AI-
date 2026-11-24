from fastapi.testclient import TestClient

from app.services import web_search
from app.services.web_search import SearchHit, normalize_youtube_url, youtube_video_id


def test_youtube_url_helpers() -> None:
    assert youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert youtube_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert youtube_video_id("https://example.com/video") is None
    assert normalize_youtube_url("https://youtu.be/dQw4w9WgXcQ") == (
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )


def test_search_youtube_filters_and_normalizes(monkeypatch) -> None:
    def fake_search(_query: str, *, max_results: int) -> list[SearchHit]:
        return [
            SearchHit(
                title="Aula completa",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10",
                snippet="Ensino em português",
            ),
            SearchHit(
                title="Artigo",
                url="https://example.com/artigo",
                snippet="Texto",
            ),
            SearchHit(
                title="Curto",
                url="https://youtu.be/abcdefghijk",
                snippet="Short",
            ),
        ]

    monkeypatch.setattr(web_search, "_run_search", fake_search)
    videos = web_search.search_youtube("redes de computadores")
    assert [video.url for video in videos] == [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=abcdefghijk",
    ]


def test_ai_generate_materials_creates_markdown_and_video(
    client: TestClient, monkeypatch
) -> None:
    client.put("/api/v1/settings", json={"deepseek_api_key": "sk-test-1234567890"})
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
    content_id = client.post(
        "/api/v1/contents",
        json={"subject_id": subject_id, "title": "Conteúdo"},
    ).json()["id"]

    monkeypatch.setattr(
        "app.services.quiz_generator.search_web",
        lambda _query: [
            SearchHit(title="Blog", url="https://example.com/blog", snippet="Resumo")
        ],
    )
    monkeypatch.setattr(
        "app.services.quiz_generator.search_youtube",
        lambda _query: [
            SearchHit(
                title="Aula em vídeo pt-BR",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                snippet="Aula didática",
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.quiz_generator.write_teaching_material",
        lambda **_kwargs: {
            "material_title": "Material markdown",
            "body": "## Objetivo\nEntender o tema.\n\n## Explicação\nConteúdo real.",
            "reference_links": [
                {"title": "Blog", "url": "https://example.com/blog"},
            ],
        },
    )

    response = client.post(
        f"/api/v1/contents/{content_id}/ai/materials",
        json={"include_text": True, "include_video": True, "include_links": True},
    )
    assert response.status_code == 201, response.text
    assert response.json()["created"] >= 2

    materials = client.get(f"/api/v1/contents/{content_id}/materials").json()
    text_materials = [m for m in materials if m["type"] == "text"]
    video_materials = [m for m in materials if m["type"] == "video"]

    assert text_materials
    assert text_materials[0]["body"].startswith("## Objetivo")
    assert video_materials
    assert video_materials[0]["url_or_path"].startswith("https://www.youtube.com/watch?v=")


def test_course_materials_status_and_schedule(client: TestClient, monkeypatch) -> None:
    client.put("/api/v1/settings", json={"deepseek_api_key": "sk-test-1234567890"})
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
    client.post("/api/v1/contents", json={"subject_id": subject_id, "title": "A"})
    client.post("/api/v1/contents", json={"subject_id": subject_id, "title": "B"})

    status = client.get(f"/api/v1/courses/{course_id}/ai/materials-status").json()
    assert status["total_contents"] == 2
    assert status["pending_contents"] == 2
    assert status["contents_with_materials"] == 0

    monkeypatch.setattr(
        "app.services.structure_generator.search_web",
        lambda _query: [SearchHit(title="Blog", url="https://example.com/b", snippet="x")],
    )
    monkeypatch.setattr(
        "app.services.structure_generator.search_youtube", lambda _query: []
    )
    monkeypatch.setattr(
        "app.services.structure_generator.write_teaching_material",
        lambda **kwargs: {
            "material_title": "Material",
            "body": "## Objetivo\nEstudar.",
            "reference_links": [],
        },
    )

    response = client.post(f"/api/v1/courses/{course_id}/ai/materials")
    assert response.status_code == 202, response.text
    assert response.json()["scheduled"] is True

    status = client.get(f"/api/v1/courses/{course_id}/ai/materials-status").json()
    assert status["pending_contents"] == 0
    assert status["contents_with_materials"] == 2

    again = client.post(f"/api/v1/courses/{course_id}/ai/materials")
    assert again.json()["scheduled"] is False
