from fastapi.testclient import TestClient


def _create_course(client: TestClient) -> str:
    return client.post(
        "/api/v1/courses", json={"name": "Curso", "category": "TI"}
    ).json()["id"]


def _create_topic(client: TestClient, course_id: str, name: str, level: str) -> dict:
    return client.post(
        "/api/v1/topics",
        json={"course_id": course_id, "name": name, "level": level},
    ).json()


def _create_subject(client: TestClient, topic_id: str, name: str, level: str) -> dict:
    return client.post(
        "/api/v1/subjects",
        json={"topic_id": topic_id, "name": name, "level": level},
    ).json()


def _create_content(client: TestClient, subject_id: str, title: str) -> dict:
    return client.post(
        "/api/v1/contents", json={"subject_id": subject_id, "title": title}
    ).json()


def test_levels_unlock_by_completion(client: TestClient) -> None:
    course_id = _create_course(client)

    base_topic = _create_topic(client, course_id, "Fundamentos", "iniciante")
    mid_topic = _create_topic(client, course_id, "Prática", "intermediario")
    advanced_topic = _create_topic(client, course_id, "Especialização", "avancado")

    base_subject = _create_subject(client, base_topic["id"], "Intro", "iniciante")
    mid_subject = _create_subject(client, mid_topic["id"], "Aplicação", "iniciante")

    base_content = _create_content(client, base_subject["id"], "Primeiro passo")
    mid_content = _create_content(client, mid_subject["id"], "Segundo passo")

    # Matéria intermediária no tópico iniciante só libera após concluir o iniciante.
    inner_mid = _create_subject(client, base_topic["id"], "Intermediária", "intermediario")
    assert inner_mid["is_unlocked"] is False

    topics = client.get("/api/v1/topics", params={"course_id": course_id}).json()
    by_id = {topic["id"]: topic for topic in topics}
    assert by_id[base_topic["id"]]["is_unlocked"] is True
    assert by_id[mid_topic["id"]]["is_unlocked"] is False
    assert by_id[advanced_topic["id"]]["is_unlocked"] is False

    client.patch(f"/api/v1/contents/{base_content['id']}", json={"status": "concluido"})

    topics = client.get("/api/v1/topics", params={"course_id": course_id}).json()
    by_id = {topic["id"]: topic for topic in topics}
    assert by_id[mid_topic["id"]]["is_unlocked"] is True
    assert by_id[advanced_topic["id"]]["is_unlocked"] is False

    unlocked_subject = client.get(f"/api/v1/subjects/{inner_mid['id']}").json()
    assert unlocked_subject["is_unlocked"] is True

    client.patch(f"/api/v1/contents/{mid_content['id']}", json={"status": "concluido"})

    topics = client.get("/api/v1/topics", params={"course_id": course_id}).json()
    by_id = {topic["id"]: topic for topic in topics}
    assert by_id[advanced_topic["id"]]["is_unlocked"] is True


def test_blocked_topic_blocks_its_subjects(client: TestClient) -> None:
    course_id = _create_course(client)
    base_topic = _create_topic(client, course_id, "Base", "iniciante")
    advanced_topic = _create_topic(client, course_id, "Avançado", "avancado")

    base_subject = _create_subject(client, base_topic["id"], "Intro", "iniciante")
    _create_content(client, base_subject["id"], "Conteúdo pendente")

    subject = _create_subject(client, advanced_topic["id"], "Tema", "iniciante")
    assert subject["is_unlocked"] is False

    refreshed = client.get(f"/api/v1/topics/{advanced_topic['id']}").json()
    assert refreshed["is_unlocked"] is False


def test_manual_unlock_override(client: TestClient) -> None:
    course_id = _create_course(client)
    base_topic = _create_topic(client, course_id, "Base", "iniciante")
    advanced_topic = _create_topic(client, course_id, "Avançado", "avancado")

    base_subject = _create_subject(client, base_topic["id"], "Intro", "iniciante")
    _create_content(client, base_subject["id"], "Conteúdo pendente")

    updated = client.patch(
        f"/api/v1/topics/{advanced_topic['id']}",
        json={"unlocked_manual": True},
    ).json()
    assert updated["is_unlocked"] is True

    subject = _create_subject(client, advanced_topic["id"], "Tema", "iniciante")
    assert subject["is_unlocked"] is True
