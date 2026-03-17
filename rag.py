"""Lightweight RAG retrieval for Jira triage comments.

This module fetches a curated set of public or internal knowledge URLs,
chunks their content, scores relevance against the Jira issue context, and
returns short snippets that can be inserted into the LLM prompt.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Iterable, Sequence
from urllib.parse import urlparse

import httpx

from config import get_settings

logger = logging.getLogger(__name__)

# Small default source set for Airflow-centric triage. These are public and can
# be replaced/extended via RAG_SOURCE_URLS in the environment.
DEFAULT_RAG_SOURCE_URLS: tuple[str, ...] = (
    "https://airflow.apache.org/docs/apache-airflow/stable/",
    "https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html",
    "https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/operators.html",
    "https://airflow.apache.org/docs/apache-airflow/stable/best-practices/index.html",
    "https://airflow.apache.org/docs/apache-airflow/stable/configurations-ref.html",
    "https://airflow.apache.org/docs/apache-airflow/stable/troubleshooting.html",
    "https://airflow.apache.org/docs/apache-airflow/stable/release_notes.html",
    "https://github.com/apache/airflow/blob/main/README.md",
)


@dataclass(frozen=True)
class IssueContext:
    issue_key: str
    summary: str
    description: str | None = None
    priority: str | None = None
    issue_type: str | None = None
    project_key: str | None = None
    reporter: str | None = None


@dataclass(frozen=True)
class KnowledgeSnippet:
    title: str
    url: str
    excerpt: str
    source: str
    score: float


@dataclass(frozen=True)
class _SourceDocument:
    url: str
    title: str
    text: str


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._title_parts: list[str] = []
        self._in_title = False
        self._ignore_depth = 0

    def handle_starttag(self, tag: str, attrs):  # type: ignore[override]
        if tag in {"script", "style", "noscript"}:
            self._ignore_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag in {"p", "div", "li", "section", "br", "tr", "h1", "h2", "h3", "h4"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._ignore_depth > 0:
            self._ignore_depth -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._ignore_depth:
            return
        clean = data.strip()
        if not clean:
            return
        if self._in_title:
            self._title_parts.append(clean)
        else:
            self._parts.append(clean)

    @property
    def text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "\n".join(self._parts)).strip()

    @property
    def title(self) -> str:
        return " ".join(self._title_parts).strip()


def parse_rag_source_urls(raw: str | None) -> list[str]:
    """Parse newline/comma separated source URLs into a cleaned list."""
    if not raw:
        return []
    parts = re.split(r"[\n,]", raw)
    return [part.strip() for part in parts if part and part.strip()]


def get_rag_source_urls() -> list[str]:
    settings = get_settings()
    configured = parse_rag_source_urls(settings.rag_source_urls)
    return configured or list(DEFAULT_RAG_SOURCE_URLS)


def build_retrieval_query(issue: IssueContext) -> str:
    parts = [
        issue.issue_key,
        issue.project_key or "",
        issue.issue_type or "",
        issue.priority or "",
        issue.summary or "",
        issue.description or "",
    ]
    query = " ".join(part for part in parts if part)
    return re.sub(r"\s+", " ", query).strip()[:400]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_./:-]+", text.lower())


def _ngrams(tokens: Sequence[str], n: int) -> set[str]:
    if n <= 0 or len(tokens) < n:
        return set()
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def _overlap_score(query_terms: set[str], candidate_terms: set[str]) -> float:
    if not query_terms:
        return 0.0
    return len(query_terms & candidate_terms) / max(len(query_terms), 1)


def score_text(query: str, candidate: str, title: str = "") -> float:
    """Score relevance using unigram and bigram overlap plus title bonus."""
    query_tokens = _tokenize(query)
    candidate_tokens = _tokenize(candidate)
    query_terms = set(query_tokens)
    candidate_terms = set(candidate_tokens)

    unigram = _overlap_score(query_terms, candidate_terms)
    bigram = _overlap_score(_ngrams(query_tokens, 2), _ngrams(candidate_tokens, 2))

    title_bonus = 0.0
    if title:
        title_terms = set(_tokenize(title))
        title_bonus = 0.15 if query_terms & title_terms else 0.0

    return (0.65 * unigram) + (0.35 * bigram) + title_bonus


def chunk_text(text: str, max_chars: int) -> list[str]:
    """Split text into compact chunks while preserving paragraphs."""
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        return [text[:max_chars]]

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if not current:
            current = paragraph
            continue
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}"
        else:
            chunks.append(current)
            current = paragraph
    if current:
        chunks.append(current)
    return chunks


def _extract_text_from_html(html: str) -> tuple[str, str]:
    parser = _HTMLTextExtractor()
    parser.feed(html)
    title = parser.title or ""
    return parser.text, title


def _best_title(url: str, fallback: str, text: str) -> str:
    if fallback:
        return fallback
    path = urlparse(url).path.rstrip("/")
    if path:
        candidate = path.split("/")[-1]
        if candidate:
            return candidate.replace("-", " ").replace("_", " ")
    first_line = next((line.strip("# ").strip() for line in text.splitlines() if line.strip()), "")
    return first_line[:80] or url


async def _fetch_source_document(
    client: httpx.AsyncClient,
    url: str,
    max_chars: int,
) -> _SourceDocument | None:
    try:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001 - retrieval should fail soft
        logger.warning("RAG source fetch failed for %s: %s", url, exc)
        return None

    content_type = response.headers.get("content-type", "").lower()
    raw_text = response.text[:max_chars]

    if "html" in content_type:
        text, title = _extract_text_from_html(raw_text)
    else:
        text, title = raw_text, ""

    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return None

    return _SourceDocument(url=url, title=_best_title(url, title, text), text=text)


async def retrieve_knowledge(
    issue: IssueContext,
    *,
    top_k: int | None = None,
    source_urls: Sequence[str] | None = None,
) -> list[KnowledgeSnippet]:
    """Fetch candidate docs, score them, and return the best snippets."""
    settings = get_settings()
    urls = list(source_urls) if source_urls is not None else get_rag_source_urls()
    if not urls:
        return []

    query = build_retrieval_query(issue)
    max_chars = settings.rag_max_source_chars
    top_k = top_k or settings.rag_top_k

    async with httpx.AsyncClient(timeout=settings.rag_timeout_seconds) as client:
        docs = await asyncio.gather(
            *(_fetch_source_document(client, url, max_chars) for url in urls),
            return_exceptions=False,
        )

    snippets: list[KnowledgeSnippet] = []
    for doc in docs:
        if doc is None:
            continue
        chunks = chunk_text(doc.text, max_chars=min(1600, max_chars))
        best_score = -1.0
        best_excerpt = ""
        for chunk in chunks:
            score = score_text(query, chunk, doc.title)
            if score > best_score:
                best_score = score
                best_excerpt = chunk
        if best_score <= 0:
            continue
        snippets.append(
            KnowledgeSnippet(
                title=doc.title,
                url=doc.url,
                excerpt=best_excerpt[: settings.rag_max_snippet_chars].strip(),
                source=urlparse(doc.url).netloc,
                score=best_score,
            )
        )

    snippets.sort(key=lambda item: item.score, reverse=True)
    return snippets[:top_k]


def format_knowledge_snippets(snippets: Sequence[KnowledgeSnippet]) -> str:
    if not snippets:
        return ""

    lines = ["Relevant internal context (retrieved):"]
    for idx, snippet in enumerate(snippets, start=1):
        excerpt = re.sub(r"\s+", " ", snippet.excerpt).strip()
        lines.append(f"{idx}. {snippet.title} ({snippet.url})")
        lines.append(f"   {excerpt}")
    return "\n".join(lines).strip()

