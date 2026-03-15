# Automatic triage: issue created → LLM comment (no script)

When someone **creates a Jira issue**, Jira Automation calls your LLM service and posts the hypothesis as a comment. No need to run `triage_issue.py`.

---

## Flow

```
Issue created (JLA) → Jira Automation → POST /jira/triage (your app) → LLM → response
       → Jira adds comment from response
```

---

## 1. Expose your app (Jira must reach it over HTTPS)

Your FastAPI app must be at a **public HTTPS URL**. Two options:

### A. Quick test: ngrok (local)

```bash
cd ~/code/jira-llm-automation
source .venv/bin/activate
uvicorn main:app --port 8000
```

In another terminal:

```bash
ngrok http 8000
```

Copy the **HTTPS** URL (e.g. `https://abc123.ngrok.io`). That is your **base URL** for the rule.

### B. Always on: deploy (Railway, Render, Fly.io)

Deploy this repo, set env vars `OPENAI_API_KEY`, `OPENAI_MODEL`, and `JIRA_TRIAGE_TOKEN`. Use the app’s HTTPS URL as the base URL in the rule.

---

## 2. Set JIRA_TRIAGE_TOKEN

In your `.env` (and in your deployed app’s env), set a **secret** you choose:

```env
JIRA_TRIAGE_TOKEN=some-long-random-secret-you-invent
```

You’ll put the **same value** in the Jira Automation rule (step 3). This proves the request to your app really comes from your Jira rule.

---

## 3. Create the Jira Automation rule

1. In Jira: [Project JLA](https://sanjayrane.atlassian.net/jira/software/projects/JLA/boards/2/backlog) → **Project settings** (gear) → **Automation** → **Create rule**.

2. **Trigger:** **Issue created** (optionally add condition: Project = JLA).

3. **Action 1 – Send web request**
   - **URL:** `https://YOUR-BASE-URL/jira/triage`  
     (e.g. `https://abc123.ngrok.io/jira/triage` or `https://your-app.railway.app/jira/triage`)
   - **Method:** `POST`
   - **Headers:**
     - `Content-Type` = `application/json`
     - `Authorization` = `Bearer same-value-as-JIRA_TRIAGE_TOKEN`
   - **Body:** Custom data (JSON):

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

   - Enable **“Wait for response”** (or “Delay rule until webhook response is received”).

4. **Action 2 – Comment on issue**
   - **Comment:** `{{webhookResponse.body.comment}}`  
     (or `{{response.body.comment}}` if your Jira version uses that)

5. **Save** and turn the rule **On**.

---

## 4. Test

Create a new issue in JLA. Within a short time, a comment with the AI hypothesis should appear. If not, check the rule is enabled, the URL is correct and reachable, and your app logs for incoming requests.

---

## Summary

| What | Where |
|------|--------|
| App running & reachable | Your machine (ngrok) or cloud (Railway etc.) |
| Same secret | `.env` → `JIRA_TRIAGE_TOKEN` and Automation header `Authorization: Bearer <token>` |
| Rule | Issue created → Send web request → Comment on issue |

More detail: [JIRA_SETUP.md](JIRA_SETUP.md).
