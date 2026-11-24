from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def generate_study_structure(
    *,
    api_key: str,
    base_url: str,
    model: str,
    course_name: str,
    course_category: str,
    course_description: str | None,
    objective: str,
    existing_summary: str,
    include_contents: bool,
) -> dict[str, Any]:
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=120.0, max_retries=1)

    content_rule = (
        "Inclua 2 a 3 conteúdos em cada matéria, pensados para ensino real "
        "(cada conteúdo deve ter um search_query específico para pesquisa na web)."
        if include_contents
        else "Não inclua conteúdos; deixe contents como lista vazia."
    )

    system = (
        "Você é um professor e planejador curricular. "
        "NÃO crie novos cursos. Gere apenas tópicos dentro do curso informado. "
        "Respeite progressão pedagógica real (iniciante antes de avançado). "
        "Priorize ensino real e progressão didática. "
        "Responda APENAS com JSON válido."
    )
    user = f"""
Curso (já existente — NÃO criar outro curso): {course_name}
Categoria do curso: {course_category}
Descrição do curso: {course_description or "sem descrição"}
Objetivo do usuário: {objective}

Estrutura já existente no curso (evite duplicar nomes óbvios):
{existing_summary or "nenhuma"}

Gere tópicos de estudo em português com este formato:
{{
  "topics": [
    {{
      "name": "string",
      "description": "string",
      "level": "iniciante | intermediario | avancado",
      "subjects": [
        {{
          "name": "string",
          "description": "string",
          "level": "iniciante | intermediario | avancado",
          "contents": [
            {{
              "title": "string",
              "description": "string",
              "search_query": "consulta curta para pesquisar material didático na web"
            }}
          ]
        }}
      ]
    }}
  ]
}}

Regras de progressão (obrigatórias):
- O primeiro tópico de um curso novo DEVE ser "iniciante" e cobrir pré-requisitos básicos.
- Nunca comece por tópico "avancado"; avance um nível por vez.
- Cada tópico declara na description qual pré-requisito do tópico anterior ele assume.
- Dentro de cada tópico, as matérias também progridem iniciante → intermediario → avancado.
- Se o curso já tiver estrutura, continue de onde parou e evite repetir níveis já cobertos.
- Crie de 2 a 5 tópicos dentro DESTE curso (1 a 2 por nível).
- Cada tópico deve ter de 1 a 4 matérias.
- Toda matéria pertence a um tópico.
- {content_rule}
- Nomes claros, progressivos e úteis para estudo real.""".strip()

    response = client.chat.completions.create(
        model=model,
        temperature=0.4,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    return extract_json_object(raw)


def _chat_json(*, api_key: str, base_url: str, model: str, system: str, user: str, temperature: float = 0.4) -> dict[str, Any]:
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=120.0, max_retries=1)
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    return extract_json_object(raw)


def generate_exercises_json(
    *,
    api_key: str,
    base_url: str,
    model: str,
    context: str,
    count: int,
    include_discursive: bool,
) -> dict[str, Any]:
    system = (
        "Você é um professor que cria exercícios de fixação reais, "
        "alinhados ao material estudado e ao nível do aluno. "
        "Responda APENAS com JSON válido."
    )
    rule = (
        "Alterne exercícios objetivos e discursivos."
        if include_discursive
        else "Crie apenas exercícios objetivos."
    )
    user = f"""
Contexto do conteúdo estudado:
{context}

Crie {count} exercícios em português. {rule}

Formato JSON:
{{
  "exercises": [
    {{
      "type": "objetiva" | "discursiva",
      "question": "enunciado claro, contextualizado",
      "explanation": "explicação do gabarito (para objetiva) ou critérios de correção (discursiva)",
      "alternatives": [
        {{ "text": "alternativa", "is_correct": true }}
      ]
    }}
  ]
}}

Regras:
- Exercícios objetivos: exatamente 4 alternativas, apenas 1 correta, distratores plausíveis.
- Exercícios discursivos: alternatives = [] e explanation com o que a resposta deve conter.
- Nada de perguntas triviais ou de memorização vazia; cobre compreensão e aplicação.
- Não repita o mesmo conceito em exercícios diferentes.
""".strip()
    return _chat_json(
        api_key=api_key,
        base_url=base_url,
        model=model,
        system=system,
        user=user,
        temperature=0.5,
    )


def generate_exam_json(
    *,
    api_key: str,
    base_url: str,
    model: str,
    context: str,
    questions_count: int,
    discursive_count: int,
) -> dict[str, Any]:
    system = (
        "Você é um professor que monta provas reais, cobrindo compreensão, "
        "aplicação e análise do conteúdo estudado. Responda APENAS com JSON válido."
    )
    user = f"""
Contexto do conteúdo estudado:
{context}

Monte uma prova em português com {questions_count} questões no total,
sendo {discursive_count} discursivas e o restante objetivas.

Formato JSON:
{{
  "title": "título da prova",
  "questions": [
    {{
      "type": "objetiva" | "discursiva",
      "question": "enunciado",
      "points": 1,
      "alternatives": [
        {{ "text": "alternativa", "is_correct": true }}
      ]
    }}
  ]
}}

Regras:
- Objetivas: exatamente 4 alternativas, apenas 1 correta.
- Discursivas: alternatives = [].
- Progrida a dificuldade: comece com questões conceituais e termine com aplicação.
- Não repita a mesma pergunta.
""".strip()
    return _chat_json(
        api_key=api_key,
        base_url=base_url,
        model=model,
        system=system,
        user=user,
        temperature=0.45,
    )


def review_answer_json(
    *,
    api_key: str,
    base_url: str,
    model: str,
    question: str,
    criteria: str | None,
    student_answer: str,
) -> dict[str, Any]:
    system = (
        "Você é um professor corrigindo uma resposta discursiva. "
        "Seja justo e construtivo. Responda APENAS com JSON válido."
    )
    user = f"""
Pergunta: {question}
Critérios esperados: {criteria or "não informados"}
Resposta do aluno: {student_answer}

Formato JSON:
{{ "score_ratio": 0.0, "feedback": "feedback curto em português explicando acertos e lacunas" }}

Regras:
- score_ratio entre 0 e 1, proporcional ao que a resposta cobre dos critérios.
- Feedback direto, no máximo 3 frases, apontando o que faltou.
""".strip()
    return _chat_json(
        api_key=api_key,
        base_url=base_url,
        model=model,
        system=system,
        user=user,
        temperature=0.2,
    )


def generate_course_from_objective(
    *,
    api_key: str,
    base_url: str,
    model: str,
    objective: str,
    preferred_category: str | None,
    include_contents: bool,
) -> dict[str, Any]:
    """Cria um curso novo (nome/categoria/descrição) + tópicos iniciais."""
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=120.0, max_retries=1)

    content_rule = (
        "Inclua 2 a 3 conteúdos em cada matéria, pensados para ensino real "
        "(cada conteúdo deve ter um search_query específico para pesquisa na web)."
        if include_contents
        else "Não inclua conteúdos; deixe contents como lista vazia."
    )
    category_hint = preferred_category.strip() if preferred_category else ""

    system = (
        "Você é um professor e planejador curricular. "
        "Crie UM curso completo com tópicos, matérias e conteúdos. "
        "Respeite progressão pedagógica real: nada de tópicos avançados no começo. "
        "Priorize ensino real e progressão didática. "
        "Responda APENAS com JSON válido."
    )
    user = f"""
Objetivo do usuário: {objective}
Categoria preferida (use se fizer sentido): {category_hint or "definir a mais adequada"}

Gere em português com este formato:
{{
  "course": {{
    "name": "nome curto do curso",
    "category": "categoria livre, ex.: Ciência da Computação",
    "description": "descrição curta do curso"
  }},
  "topics": [
    {{
      "name": "string",
      "description": "string (inclua o pré-requisito assumido)",
      "level": "iniciante | intermediario | avancado",
      "subjects": [
        {{
          "name": "string",
          "description": "string",
          "level": "iniciante | intermediario | avancado",
          "contents": [
            {{
              "title": "string",
              "description": "string",
              "search_query": "consulta curta para pesquisar material didático na web"
            }}
          ]
        }}
      ]
    }}
  ]
}}

Regras de progressão (obrigatórias):
- O primeiro tópico DEVE ser "iniciante" e cobrir fundamentos/pré-requisitos.
- Nunca comece por "avancado"; suba um nível por vez.
- Sequência esperada: 1-2 tópicos iniciante, depois 1-2 intermediario, depois só se necessário 1 avancado.
- Dentro de cada tópico, as matérias também progridem iniciante → intermediario → avancado.
- Não pule etapas: cada nível depende do anterior estar dominado.
- Crie exatamente 1 curso.
- Crie de 2 a 5 tópicos.
- Cada tópico deve ter de 1 a 4 matérias.
- {content_rule}
- Nomes claros, progressivos e úteis para estudo real.
""".strip()

    response = client.chat.completions.create(
        model=model,
        temperature=0.4,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    return extract_json_object(raw)
