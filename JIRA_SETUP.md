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

### Step 1: Open Automation and create the rule

1. Open your project: [JLA backlog](https://sanjayrane.atlassian.net/jira/software/projects/JLA/boards/2/backlog).
2. Go to **Project settings** (gear) → **Automation**, or **Jira settings** → **Automation** → **Global automation** for a site-wide rule.
3. Click **Create rule**.

### Step 2: Set the trigger and see the rule flow

4. **Trigger:** Choose **Work item created** (Jira may show “Issue created” in some UIs). Optionally add a condition (e.g. Project = JLA).
5. Add the two actions below so the rule looks like: **When** Work item created → **Then** Send web request → **And** Add comment to work item. Set **Scope** to Global (or your project) and save the rule name.

![Rule flow and details: When / Then / And, Scope Global](docs/screenshots/1-rule-flow-and-details.png)

### Step 3: Configure “Send web request”

6. **Action 1 – Send web request.** Use these settings (see screenshot for where each field lives):

   - **Web request URL**: `https://YOUR-SERVICE-URL/jira/triage`  
     (e.g. `https://abc123.ngrok-free.dev/jira/triage` or your deployed URL; **must include `/jira/triage`**.)
   - **HTTP method**: `POST`
   - **Headers** (add both):
     - `Content-Type`: `application/json`
     - `Authorization`: `Bearer YOUR_JIRA_TRIAGE_TOKEN`  
       (same value as in your `.env` as `JIRA_TRIAGE_TOKEN`; the word **Bearer** and a space are required.)
   - **Web request body**: choose **Custom data**, then paste this JSON:

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

   - **Execution options:** Turn **on** “Delay execution of subsequent rule actions until we've received a response for this web request”.

![Send web request: URL, method, body, headers](docs/screenshots/2-send-web-request-config.png)

### Step 4: Configure “Add comment to work item” with the response

7. **Action 2 – Add comment to work item.** In the comment body, use the **response** from the Send web request step. In Jira Cloud this is usually **`{{webResponse.body.comment}}`** (see screenshot for the exact smart value list).

![How to use the web request response: webResponse.body.comment](docs/screenshots/3-send-web-request-response-values.png)

8. **Save** and enable the rule.

---

## 3. Test it

1. Create a new issue in project **JLA** (e.g. from the [backlog](https://sanjayrane.atlassian.net/jira/software/projects/JLA/boards/2/backlog)).
2. After a few seconds, the automation should run: your service will be called, the LLM will generate the initial hypothesis, and Jira will add a comment with that text.

If nothing happens, check:

- Automation rule is **enabled** and the trigger is **Work item created** (or “Issue created”) for JLA.
- **Send web request** uses the correct URL and **Delay execution until response** is on.
- Your service is running and reachable (no firewall blocking Jira).
- **Comment** step uses `{{webResponse.body.comment}}` (or the response variable name your Jira UI shows).
- In your service logs: you should see a request for the new issue key.

---

## Summary

| Step | What you do |
|------|----------------------|
| 1 | Run the triage service and expose it (ngrok or deploy). See [section 1](#1-expose-the-triage-service-jira-must-reach-it). |
| 2 | In Jira Automation: **Work item created** → **Send web request** to `/jira/triage` with issue JSON; enable “Delay execution until response”. See [screenshots](docs/screenshots/) and [section 2](#2-create-the-automation-rule-in-jira). |
| 3 | **Add comment to work item** with `{{webResponse.body.comment}}`. See screenshot 3 above. |
| 4 | Create a work item in JLA → LLM comment appears on the item. |
