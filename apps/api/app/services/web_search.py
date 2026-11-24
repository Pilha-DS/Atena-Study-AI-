from __future__ import annotations

import os
import re
import threading
import time
from dataclasses import dataclass

from duckduckgo_search import DDGS

_SEARCH_INTERVAL_SECONDS = float(os.getenv("WEB_SEARCH_INTERVAL_SECONDS", "1.5"))
_lock = threading.Lock()
_last_search_at = 0.0

_YOUTUBE_ID_PATTERN = re.compile(
    r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|live/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str


def _wait_for_rate_limit() -> None:
    global _last_search_at
    with _lock:
        now = time.monotonic()
        wait_for = _SEARCH_INTERVAL_SECONDS - (now - _last_search_at)
        if wait_for > 0:
            time.sleep(wait_for)
        _last_search_at = time.monotonic()


def _run_search(query: str, *, max_results: int) -> list[SearchHit]:
    cleaned = query.strip()
    if not cleaned:
        return []

    _wait_for_rate_limit()
    hits: list[SearchHit] = []
    with DDGS() as ddgs:
        for item in ddgs.text(cleaned, max_results=max_results):
            hits.append(
                SearchHit(
                    title=(item.get("title") or "").strip(),
                    url=(item.get("href") or item.get("link") or "").strip(),
                    snippet=(item.get("body") or item.get("snippet") or "").strip(),
                )
            )
    return hits


def search_web(query: str, *, max_results: int = 4) -> list[SearchHit]:
    """Search the web with a hard limit of 1 request every 4 seconds."""
    return _run_search(query, max_results=max_results)


def youtube_video_id(url: str | None) -> str | None:
    if not url:
        return None
    match = _YOUTUBE_ID_PATTERN.search(url)
    return match.group(1) if match else None


def normalize_youtube_url(url: str) -> str | None:
    video_id = youtube_video_id(url)
    if not video_id:
        return None
    return f"https://www.youtube.com/watch?v={video_id}"


def search_youtube(query: str, *, max_results: int = 4) -> list[SearchHit]:
    """Busca aulas em vídeo no YouTube em português (reaproveita o rate limit global)."""
    cleaned = query.strip() or "aula"
    localized = f"{cleaned} aula em português site:youtube.com"
    hits = _run_search(localized, max_results=max_results * 2)

    videos: list[SearchHit] = []
    seen: set[str] = set()
    for hit in hits:
        normalized = normalize_youtube_url(hit.url)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        videos.append(
            SearchHit(title=hit.title, url=normalized, snippet=hit.snippet)
        )
        if len(videos) >= max_results:
            break
    return videos


def reset_rate_limit_for_tests() -> None:
    global _last_search_at
    with _lock:
        _last_search_at = 0.0
