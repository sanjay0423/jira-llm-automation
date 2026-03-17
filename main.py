"""
Jira LLM Automation – triage endpoint for Jira Automation (Send web request).

Flow: Work item created → Jira Automation POSTs here → RAG retrieves internal
context → LLM generates comment text → Automation adds comment to work item
from response. (Uses Automation, not webhooks.)

Contract:
  - POST /jira/triage with JSON: issueKey, summary, description, priority, issueType, projectKey, reporter
  - Response: { "comment": "<markdown>" }
"""
from __future__ import annotations

import json
import logging
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from openai import AsyncOpenAI
from config import get_settings
from rag import IssueContext, KnowledgeSnippet, format_knowledge_snippets, retrieve_knowledge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Jira LLM Triage",
    description="AI first-pass analysis for Jira issues; used by Jira Automation to post internal notes.",
    version="1.0.0",
)


# --- Request/Response models (match Jira Automation contract) ---

class JiraTriageRequest(BaseModel):
    issueKey: str = Field(..., description="Jira issue key, e.g. ENG-123")
    summary: str = Field(..., description="Issue summary")
    description: str | None = Field(None, description="Issue description")
    priority: str | None = Field(None, description="e.g. High, Medium")
    issueType: str | None = Field(None, description="e.g. Bug, Incident")
    projectKey: str | None = Field(None, description="Project key")
    reporter: str | None = Field(None, description="Reporter display name")


class JiraTriageResponse(BaseModel):
    comment: str = Field(..., description="Markdown text for the internal note")


# --- Prompt template (TL;DR, Hypothesis, Immediate checks, Questions for reporter) ---

SYSTEM_PROMPT = """You are an internal incident triage assistant for engineers only.
Output only the internal note in Markdown. Do not add meta-commentary.
Use exactly these four sections with the given headings. Be concise and safe; label uncertainty clearly."""

USER_PROMPT_TEMPLATE = """Issue key: {issue_key}
Project: {project_key}
Type: {issue_type}
Priority: {priority}
Reporter: {reporter}

Summary:
{summary}

Description:
{description}

{knowledge_block}

Generate a concise internal note in Markdown with exactly these sections:

**TL;DR**
- One bullet with the most likely high-level cause or next step.

**Hypothesis**
- 2-4 bullets about likely root cause(s).

**Immediate checks**
- 2-5 bullets of concrete checks an engineer can do now.

**Questions for reporter**
- 2-4 bullets with clarifying questions.

Avoid exposing sensitive data. Be explicit when unsure. Start with "AI first pass – please validate before following." as the first line.

When relevant, use the retrieved internal context to ground the hypothesis and checks. If the retrieved context is weak or conflicting, mention that uncertainty."""


def _to_issue_context(payload: JiraTriageRequest) -> IssueContext:
    return IssueContext(
        issue_key=payload.issueKey,
        summary=payload.summary,
        description=payload.description,
        priority=payload.priority,
        issue_type=payload.issueType,
        project_key=payload.projectKey,
        reporter=payload.reporter,
    )


def build_prompt(
    payload: JiraTriageRequest,
    knowledge_snippets: list[KnowledgeSnippet] | None = None,
) -> str:
    knowledge_block = format_knowledge_snippets(knowledge_snippets or [])
    return USER_PROMPT_TEMPLATE.format(
        issue_key=payload.issueKey,
        project_key=payload.projectKey or "",
        issue_type=payload.issueType or "",
        priority=payload.priority or "",
        reporter=payload.reporter or "",
        summary=payload.summary or "",
        description=payload.description or "(no description)",
        knowledge_block=knowledge_block,
    )


async def call_llm(prompt: str) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="LLM not configured (OPENAI_API_KEY missing)",
        )
    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_api_base if settings.openai_api_base else None,
    )
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=1024,
    )
    text = response.choices[0].message.content
    if not text:
        raise HTTPException(status_code=502, detail="LLM returned empty response")
    return text.strip()


def verify_bearer(authorization: str | None) -> None:
    settings = get_settings()
    if not settings.jira_triage_token:
        logger.warning("JIRA_TRIAGE_TOKEN not set; accepting any request (dev only)")
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Missing or invalid Authorization header")
    token = authorization[7:].strip()
    if token != settings.jira_triage_token:
        raise HTTPException(status_code=403, detail="Unauthorized")


def _sanitize_json_body(raw: bytes) -> JiraTriageRequest:
    """Parse JSON from Jira, stripping invalid control chars that cause 422 (e.g. newlines in description)."""
    text = raw.decode("utf-8", errors="replace")
    sanitized = "".join(c if ord(c) >= 32 or c == " " else " " for c in text)
    data = json.loads(sanitized)
    return JiraTriageRequest(**data)


@app.post("/jira/triage", response_model=JiraTriageResponse)
async def jira_triage(
    request: Request,
    authorization: str | None = Header(None, alias="Authorization"),
):
    """Accept issue data from Jira Automation, call LLM, return comment for internal note."""
    verify_bearer(authorization)
    try:
        body = await request.body()
        payload = _sanitize_json_body(body)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Invalid request body: %s", e)
        raise HTTPException(status_code=422, detail="Invalid JSON or missing required fields")
    logger.info("Triage request for issue %s", payload.issueKey)

    try:
        snippets = []
        try:
            snippets = await retrieve_knowledge(_to_issue_context(payload))
            if snippets:
                logger.info("Retrieved %d knowledge snippets for %s", len(snippets), payload.issueKey)
        except Exception as rag_exc:  # noqa: BLE001 - RAG should fail soft
            logger.warning("RAG retrieval failed for %s: %s", payload.issueKey, rag_exc)
        prompt = build_prompt(payload, snippets if snippets else None)
        comment_text = await call_llm(prompt)
        # Never return empty comment so Jira Automation "Add comment" does not fail
        if not (comment_text and comment_text.strip()):
            comment_text = "AI first pass could not be generated. Please triage manually."
        return JiraTriageResponse(comment=comment_text)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Triage failed for %s", payload.issueKey)
        return JSONResponse(
            status_code=500,
            content={"detail": "Triage failed", "comment": "AI first pass could not be generated. Please triage manually."},
        )


@app.get("/health")
async def health():
    """Health check for deployments."""
    return {"status": "ok"}
