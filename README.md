# Jira LLM Automation

Team-owned **Jira → LLM → internal note** flow: when an issue is created, an AI takes a first look and posts an **internal note** (agents only) with TL;DR, Hypothesis, Immediate checks, and Questions for reporter.

## Flow

1. **Jira**: Issue created → Automation rule runs.
2. **Action 1**: Send web request → `POST https://your-service/jira/triage` with issue data.
3. **This service**: Calls LLM (OpenAI or compatible), returns `{ "comment": "<markdown>" }`.
4. **Action 2**: Add internal note with `{{webhookResponse.body.comment}}`.

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

1. **Trigger**: Issue created (JSM project).
2. **Condition** (optional): e.g. Issue type = Incident OR Bug.
3. **Action 1 – Send web request**
   - URL: `https://your-deployed-service/jira/triage`
   - Method: `POST`
   - Headers:
     - `Content-Type: application/json`
     - `Authorization: Bearer <your JIRA_TRIAGE_TOKEN>`
   - Body (Custom data, JSON):

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

   - Enable **Wait for response** so the next step can use the response.

4. **Action 2 – Comment on issue**
   - Choose **Add internal note** (not "Reply to customer").
   - Comment body: `{{webhookResponse.body.comment}}`  
     (or `{{response.body.comment}}` depending on your Jira version).

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JIRA_TRIAGE_TOKEN` | Yes (in prod) | Shared secret; Jira Automation sends it as `Authorization: Bearer <token>`. If unset, all requests are accepted (dev only). |
| `OPENAI_API_KEY` | Yes | OpenAI (or compatible) API key. |
| `OPENAI_MODEL` | No | Model name (default: `gpt-4o-mini`). |
| `OPENAI_API_BASE` | No | Override base URL (e.g. Azure OpenAI). |

## API contract

- **Request**: JSON body with `issueKey`, `summary`, `description`, `priority`, `issueType`, `projectKey`, `reporter` (all except `issueKey` and `summary` optional).
- **Response**: `{ "comment": "<markdown string>" }` for the internal note.

## Deployment

Run behind HTTPS (e.g. on a team server or cloud). Jira Automation must reach the `/jira/triage` URL. Example production run:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Use a process manager (systemd, Docker, or your platform) and set `JIRA_TRIAGE_TOKEN` and `OPENAI_API_KEY` in the environment.
