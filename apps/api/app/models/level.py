from __future__ import annotations

import enum


class LearnLevel(str, enum.Enum):
    iniciante = "iniciante"
    intermediario = "intermediario"
    avancado = "avancado"


LEVEL_ORDER: list[LearnLevel] = [
    LearnLevel.iniciante,
    LearnLevel.intermediario,
    LearnLevel.avancado,
]


def normalize_level(value: str | LearnLevel | None) -> LearnLevel:
    if isinstance(value, LearnLevel):
        return value
    if not value:
        return LearnLevel.iniciante
    cleaned = str(value).strip().lower()
    for level in LEVEL_ORDER:
        if level.value == cleaned:
            return level
    if cleaned in {"intermediário", "intermediaria", "medium", "intermediate"}:
        return LearnLevel.intermediario
    if cleaned in {"avancada", "avançado", "advanced"}:
        return LearnLevel.avancado
    if cleaned in {"beginner", "basico", "básico", "iniciante"}:
        return LearnLevel.iniciante
    return LearnLevel.iniciante


def level_index(level: LearnLevel) -> int:
    return LEVEL_ORDER.index(level)
