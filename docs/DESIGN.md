# Jira LLM Automation – Design Overview

This document provides a concise design overview of the Jira LLM Automation service so that engineers and stakeholders can understand the system at a glance.

## 1. Purpose

The service generates an AI-assisted first-pass triage **comment** for Jira work items. When a work item is created, Jira Automation sends key issue fields to this service, which calls an LLM and returns structured triage guidance (TL;DR, Hypothesis, Immediate checks, Questions for reporter).

The current implementation includes a lightweight **RAG layer** that fetches relevant context from configured documentation URLs (for example Apache Airflow docs and selected GitHub pages), scores the retrieved text against the Jira issue, and adds the best snippets to the LLM prompt.

## 2. High-level architecture

- **Jira Cloud**
  - Jira Automation rule with:
    - Trigger: Work item created
    - Action 1: Send web request → `/jira/triage` (this service)
    - Action 2: Add comment to work item using the response `comment` field
- **This service (FastAPI)**
  - Endpoint: `POST /jira/triage`
  - Responsibilities:
    - Authenticate the call via `JIRA_TRIAGE_TOKEN`
    - Validate and sanitize JSON payload
    - Build a structured prompt from issue data
    - Retrieve relevant knowledge snippets using RAG
    - Call the LLM
    - Return a single `comment` string in JSON
- **LLM provider**
  - OpenAI (or compatible API) accessed via the official Python client.

## 3. Key modules

- `main.py`
  - `JiraTriageRequest` / `JiraTriageResponse` – request/response models for `/jira/triage`
  - `build_prompt` – constructs the LLM prompt from Jira issue fields
  - `_sanitize_json_body` – parses and cleans incoming JSON to handle control characters
  - `verify_bearer` – enforces `Authorization: Bearer <JIRA_TRIAGE_TOKEN>` for production
  - `jira_triage` – FastAPI endpoint that orchestrates auth, validation, prompt building, and LLM calls
- `config.py`
  - `Settings` – loads configuration from environment variables (Jira tokens, LLM config, etc.)
- `triage_issue.py`
  - Optional script to run triage on an existing issue via Jira REST (outside of Automation).

## 4. Data flow for /jira/triage

1. Jira Automation sends a POST request to `/jira/triage` with issue fields in JSON.
2. The service:
   - Verifies the `Authorization` header (triage token).
   - Sanitizes the raw body and loads it into `JiraTriageRequest`.
   - Retrieves relevant snippets from configured knowledge sources.
   - Builds a prompt and calls the LLM.
3. The LLM response is validated and, if empty, replaced with a fallback comment.
4. The service returns `{ "comment": "<markdown>" }`.
5. Jira Automation uses `{{webResponse.body.comment}}` to add the comment to the work item.

## 5. Configuration and secrets

Configuration is provided via environment variables and loaded by `Settings` in `config.py`. Examples:

- `JIRA_TRIAGE_TOKEN` – shared secret for Jira Automation → service calls
- `OPENAI_API_KEY` – LLM provider API key
- `OPENAI_MODEL` – LLM model name (default `gpt-4o-mini`)
- `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` – used by `triage_issue.py` when interacting with Jira REST

Secrets are not committed to the repository; instead, `.env.example` documents required variables and `.env` is excluded via `.gitignore`.

Further details (setup steps, automation rule configuration, and stakeholder view) are in `JIRA_SETUP.md`, `AUTOMATIC_TRIAGE.md`, and `STAKEHOLDER_OVERVIEW.md`.

