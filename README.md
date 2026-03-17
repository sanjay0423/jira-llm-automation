# Jira LLM Automation

Team-owned **Jira → LLM → comment** flow: when an issue is created, an AI takes a first look and posts a **comment** with TL;DR, Hypothesis, Immediate checks, and Questions for reporter.

This uses **Jira Automation** (Send web request), not Jira webhooks. When a work item is created, an Automation rule sends the issue data to this service; the service retrieves relevant internal knowledge with RAG, calls the LLM, and returns the comment text; the rule then adds that as a comment on the issue.

## Flow

1. **Jira**: Issue created → **Automation rule** runs (trigger: “Work item created”).
2. **Action 1 – Send web request**: Jira sends `POST https://your-service/jira/triage` with issue data (and waits for the response).
3. **This service**: Retrieves knowledge from configured docs/code sources, calls LLM (OpenAI or compatible), returns `{ "comment": "<markdown>" }`.
4. **Action 2 – Add comment to work item**: Jira posts the returned text using the response smart value (see below).

## Quick start

### 1. Install and configure

```bash
cd ~/code/jira-llm-automation
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set JIRA_TRIAGE_TOKEN, OPENAI_API_KEY, OPENAI_MODEL
```

### 2. Run locally

```bash
uvicorn main:app --reload --port 8000
```

- API: http://localhost:8000  
- Docs: http://localhost:8000/docs  
- Triage: `POST http://localhost:8000/jira/triage`

### 3. Jira Automation rule

This is an **Automation** rule (Jira settings → Automation → Global automation or project automation), not a webhook. Screenshots of the rule setup are in [docs/screenshots/](docs/screenshots/).

1. **Trigger**: **Work item created** (optionally limit by project, e.g. JLA).
2. **Action 1 – Send web request**
   - **URL**: `https://your-deployed-service/jira/triage` (must include `/jira/triage`).
   - **Method**: `POST`
   - **Headers**:
     - `Content-Type`: `application/json`
     - `Authorization`: `Bearer <your JIRA_TRIAGE_TOKEN>` (the word “Bearer ” plus a space is required)
   - **Body**: Custom data (JSON):

   ```json
   {
     "issueKey": "{{issue.key}}",
     "summary": "{{issue.summary}}",
     "description": "{{issue.description}}",
     "priority": "{{issue.priority.name}}",
     "issueType": "{{issue.issueType.name}}",
     "projectKey": "{{issue.project.key}}",
     "reporter": "{{issue.reporter.displayName}}"
   }
   ```

   - Enable **“Delay execution of subsequent rule actions until we've received a response for this web request”** so the next step can use the response.

3. **Action 2 – Add comment to work item**
   - **Comment body**: Use the response smart value. In most Jira Cloud UIs this is **`{{webResponse.body.comment}}`** (not `webhookResponse`). If your rule builder shows a different name for the “Send web request” response, use that (e.g. `{{response.body.comment}}`).

**Screenshots (from Jira Automation setup):**

| Screenshot | Description |
|------------|-------------|
| [1-rule-flow-and-details.png](docs/screenshots/1-rule-flow-and-details.png) | Rule flow (When / Then / And) and rule details with scope set to Global. |
| [2-send-web-request-config.png](docs/screenshots/2-send-web-request-config.png) | Send web request: URL, method, body (JSON with smart values), and headers. |
| [3-send-web-request-response-values.png](docs/screenshots/3-send-web-request-response-values.png) | How to use the response: `{{webResponse.body.comment}}` for the comment step. |

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JIRA_TRIAGE_TOKEN` | Yes (in prod) | Shared secret; Jira Automation sends it as `Authorization: Bearer <token>`. If unset, all requests are accepted (dev only). |
| `OPENAI_API_KEY` | Yes | OpenAI (or compatible) API key. |
| `OPENAI_MODEL` | No | Model name (default: `gpt-4o-mini`). |
| `OPENAI_API_BASE` | No | Override base URL (e.g. Azure OpenAI). |
| `RAG_SOURCE_URLS` | No | Newline or comma separated knowledge URLs for RAG. If empty, the app uses a starter Apache Airflow source set. |
| `RAG_TOP_K` | No | Number of retrieved snippets to include in the prompt (default: `4`). |
| `RAG_MAX_SOURCE_CHARS` | No | Maximum characters fetched from a source (default: `24000`). |
| `RAG_MAX_SNIPPET_CHARS` | No | Maximum characters included per snippet in the prompt (default: `600`). |
| `RAG_TIMEOUT_SECONDS` | No | HTTP timeout for retrieval fetches (default: `10.0`). |

## API contract

- **Request**: JSON body with `issueKey`, `summary`, `description`, `priority`, `issueType`, `projectKey`, `reporter` (all except `issueKey` and `summary` optional).
- **Response**: `{ "comment": "<markdown string>" }` for the internal note.

## Run triage for an existing issue (script)

To fetch a Jira issue, run the LLM triage, and **post the hypothesis as a comment** (e.g. for [JLA-1](https://sanjayrane.atlassian.net/browse/JLA-1)):

1. In `.env` set:
   - `JIRA_BASE_URL=https://sanjayrane.atlassian.net`
   - `JIRA_EMAIL` = your Atlassian account email
   - `JIRA_API_TOKEN` = [Create an API token](https://id.atlassian.com/manage-profile/security/api-tokens)
   - `OPENAI_API_KEY` = your OpenAI key

2. Run:

   ```bash
   python triage_issue.py JLA-1
   ```

The script fetches the issue from Jira, generates the same TL;DR / Hypothesis / Immediate checks / Questions, and adds that as a comment on the issue.

## Deployment

Run behind HTTPS (e.g. on a team server or cloud). Jira Automation must reach the `/jira/triage` URL. Example production run:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Use a process manager (systemd, Docker, or your platform) and set `JIRA_TRIAGE_TOKEN` and `OPENAI_API_KEY` in the environment.
