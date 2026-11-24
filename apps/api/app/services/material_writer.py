from __future__ import annotations

from typing import Any

from openai import OpenAI

from app.services.deepseek import extract_json_object
from app.services.web_search import SearchHit


def write_teaching_material(
    *,
    api_key: str,
    base_url: str,
    model: str,
    category_name: str,
    course_name: str,
    subject_name: str,
    content_title: str,
    content_description: str | None,
    search_hits: list[SearchHit],
) -> dict[str, Any]:
    """Ask DeepSeek for a real teaching text + optional reference links."""
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=120.0, max_retries=1)

    sources = "\n".join(
        f"- {hit.title}: {hit.snippet} (fonte: {hit.url})"
        for hit in search_hits
        if hit.title or hit.snippet
    ) or "Nenhuma fonte externa encontrada; use conhecimento pedagógico sólido."

    system = (
        "Você é um professor experiente. Priorize ensino real: explicar com clareza, "
        "exemplos concretos, analogias e exercícios curtos. "
        "Escreva o corpo em markdown (sem HTML). "
        "Responda APENAS com JSON válido, sem markdown fora do JSON."
    )
    user = f"""
Crie material didático em português para este conteúdo de estudo.

Categoria: {category_name}
Curso: {course_name}
Matéria: {subject_name}
Conteúdo: {content_title}
Descrição: {content_description or "sem descrição"}

Fontes da internet (use como referência; não copie literalmente):
{sources}

Formato JSON obrigatório:
{{
  "material_title": "string",
  "body": "texto didático longo em MARKDOWN (mínimo ~400 palavras)",
  "reference_links": [
    {{ "title": "string", "url": "https://..." }}
  ]
}}

Regras:
- O campo body DEVE ser markdown válido (use ## para seções, listas com -, **negrito**, tabelas e blocos ``` quando fizer sentido).
- Estrutura mínima do body: "## Objetivo", "## Explicação", "## Exemplo", "## Analogia", "## Resumo", "## Mini exercício".
- Não use HTML; apenas markdown.
- Comece pelo nível iniciante quando o conteúdo for introdutório e suba a complexidade aos poucos.
- Foque em ensinar de verdade, não em outline vazio.
- Corpo do material deve ser útil sozinho para estudar.
- Inclua no máximo 3 links de referência confiáveis (podem vir das fontes).
- Não invente URLs; se não houver fonte boa, deixe reference_links vazio.
""".strip()

    response = client.chat.completions.create(
        model=model,
        temperature=0.35,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    return extract_json_object(raw)
