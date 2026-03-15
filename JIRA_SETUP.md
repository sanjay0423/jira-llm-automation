# Jira setup: sanjayrane.atlassian.net (project JLA)

This guide wires your [JLA backlog](https://sanjayrane.atlassian.net/jira/software/projects/JLA/boards/2/backlog) so that **when you create an issue**, the LLM does an initial hypothesis and **adds a comment** with TL;DR, Hypothesis, Immediate checks, and Questions for reporter.

---

## 1. Expose the triage service (Jira must reach it)

Jira Cloud will **call your service** when an issue is created. Your service must be reachable at a **public HTTPS URL**.

### Option A – Quick test with ngrok (local)

```bash
cd ~/code/jira-llm-automation
source .venv/bin/activate
uvicorn main:app --port 8000
```

In another terminal:

```bash
ngrok http 8000
```

Use the **HTTPS** URL ngrok gives you (e.g. `https://abc123.ngrok.io`) as the base URL in the Jira Automation rule below.

### Option B – Deploy (Railway, Render, Fly.io, etc.)

Deploy the app and set env vars `JIRA_TRIAGE_TOKEN`, `OPENAI_API_KEY`, `OPENAI_MODEL`. Use your app’s HTTPS URL as the base URL in the rule.

---

## 2. Create the Automation rule in Jira

1. Open your project:  
   [JLA backlog](https://sanjayrane.atlassian.net/jira/software/projects/JLA/boards/2/backlog)

2. Go to **Project settings** (gear) → **Automation** (or **Jira settings** → **Automation** for a global rule).

3. **Create rule**.

4. **Trigger**
   - Choose **Issue created**.
   - Scope: limit to **Project = JLA** (or leave global if you want all projects).

5. **Action 1 – Send web request**
   - **URL**: `https://YOUR-SERVICE-URL/jira/triage`  
     (e.g. `https://abc123.ngrok.io/jira/triage` or `https://your-app.railway.app/jira/triage`)
   - **Method**: `POST`
   - **Headers**:
     - `Content-Type`: `application/json`
     - `Authorization`: `Bearer YOUR_JIRA_TRIAGE_TOKEN`  
       (same value as in your `.env` as `JIRA_TRIAGE_TOKEN`)
   - **Body**: choose **Custom data** / **JSON**, and paste:

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

   - Turn **on** “Delay execution of subsequent rule actions until we've received a response for this web request” so the next step can use the response.

6. **Action 2 – Add comment to work item**
   - **Comment** (body): **`{{webResponse.body.comment}}`** (Jira Automation typically uses `webResponse`; some UIs show `response` or `webhookResponse`.)

7. **Save** and enable the rule.

---

## 3. Test it

1. Create a new issue in project **JLA** (e.g. from the [backlog](https://sanjayrane.atlassian.net/jira/software/projects/JLA/boards/2/backlog)).
2. After a few seconds, the automation should run: your service will be called, the LLM will generate the initial hypothesis, and Jira will add a comment with that text.

If nothing happens, check:

- Automation rule is **enabled** and the trigger is **Issue created** for JLA.
- **Send web request** uses the correct URL and **Delay execution until response** is on.
- Your service is running and reachable (no firewall blocking Jira).
- **Comment** step uses `{{webResponse.body.comment}}` (or the response variable name your Jira UI shows).
- In your service logs: you should see a request for the new issue key.

---

## Summary

| Step | What you do |
|------|----------------------|
| 1 | Run the triage service and expose it (ngrok or deploy). |
| 2 | In Jira Automation: **Issue created** → **Send web request** to `/jira/triage` with issue JSON, wait for response. |
| 3 | **Comment on issue** with `{{webResponse.body.comment}}`. |
| 4 | Create an issue in JLA → LLM comment appears on the issue. |
