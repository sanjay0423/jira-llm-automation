#!/usr/bin/env python3
"""
Run LLM triage for a Jira issue and post the hypothesis as a comment.

Usage:
  python triage_issue.py JLA-1

Requires in .env (or env): JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, OPENAI_API_KEY.
"""
from __future__ import annotations

import asyncio
import base64
import json
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Reuse triage logic from main
from main import (
    JiraTriageRequest,
    build_prompt,
    call_llm,
)
from config import get_settings


def _adf_to_plain_text(node: dict) -> str:
    """Extract plain text from Jira Atlassian Document Format (ADF)."""
    if not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    parts = []
    for item in node.get("content", []):
        parts.append(_adf_to_plain_text(item))
    return "".join(parts)


def fetch_issue(issue_key: str) -> JiraTriageRequest:
    """GET issue from Jira REST API and map to JiraTriageRequest."""
    settings = get_settings()
    if not settings.jira_base_url or not settings.jira_email or not settings.jira_api_token:
        raise SystemExit(
            "Set JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN in .env (see .env.example)."
        )
    base = settings.jira_base_url.rstrip("/")
    url = f"{base}/rest/api/3/issue/{issue_key}"
    auth = base64.b64encode(
        f"{settings.jira_email}:{settings.jira_api_token}".encode()
    ).decode()
    req = Request(url, headers={"Accept": "application/json", "Authorization": f"Basic {auth}"})
    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except HTTPError as e:
        body = e.read().decode() if e.fp else ""
        raise SystemExit(f"Jira API error {e.code}: {body or e.reason}")
    except URLError as e:
        raise SystemExit(f"Request failed: {e.reason}")

    fields = data.get("fields", {})
    description = fields.get("description")
    if isinstance(description, dict):
        description = _adf_to_plain_text(description).strip() or None
    elif isinstance(description, str):
        description = description.strip() or None
    else:
        description = None

    return JiraTriageRequest(
        issueKey=data.get("key", issue_key),
        summary=fields.get("summary") or "",
        description=description,
        priority=fields.get("priority", {}).get("name") if isinstance(fields.get("priority"), dict) else None,
        issueType=fields.get("issuetype", {}).get("name") if isinstance(fields.get("issuetype"), dict) else None,
        projectKey=fields.get("project", {}).get("key") if isinstance(fields.get("project"), dict) else None,
        reporter=fields.get("reporter", {}).get("displayName") if isinstance(fields.get("reporter"), dict) else None,
    )


def _comment_to_adf(text: str) -> dict:
    """Convert plain text comment to Jira ADF (one paragraph per line)."""
    content = []
    for line in text.split("\n"):
        content.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": line or " "}],
        })
    if not content:
        content = [{"type": "paragraph", "content": [{"type": "text", "text": " "}]}]
    return {"type": "doc", "version": 1, "content": content}


def add_comment(issue_key: str, comment_text: str) -> None:
    """POST comment to Jira issue via REST API v3."""
    settings = get_settings()
    base = settings.jira_base_url.rstrip("/")
    url = f"{base}/rest/api/3/issue/{issue_key}/comment"
    auth = base64.b64encode(
        f"{settings.jira_email}:{settings.jira_api_token}".encode()
    ).decode()
    body = json.dumps({"body": _comment_to_adf(comment_text)}).encode()
    req = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth}",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            pass
    except HTTPError as e:
        body = e.read().decode() if e.fp else ""
        raise SystemExit(f"Jira API error {e.code} when adding comment: {body or e.reason}")
    except URLError as e:
        raise SystemExit(f"Request failed: {e.reason}")


async def run_triage(issue_key: str) -> None:
    payload = fetch_issue(issue_key)
    summary_preview = (payload.summary[:60] + "...") if len(payload.summary) > 60 else payload.summary
    print(f"Issue: {payload.issueKey} – {summary_preview}")
    prompt = build_prompt(payload)
    comment_text = await call_llm(prompt)
    print("Generated hypothesis (first 200 chars):")
    print(comment_text[:200] + "..." if len(comment_text) > 200 else comment_text)
    add_comment(issue_key, comment_text)
    base = get_settings().jira_base_url.rstrip("/")
    print(f"Comment added to {base}/browse/{issue_key}")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python triage_issue.py <ISSUE_KEY>\nExample: python triage_issue.py JLA-1")
    issue_key = sys.argv[1].strip().upper()
    asyncio.run(run_triage(issue_key))


if __name__ == "__main__":
    main()
