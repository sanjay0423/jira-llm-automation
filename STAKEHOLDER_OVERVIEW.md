# Jira LLM Automation – Stakeholder Overview

**Use this doc with the [Git repo](https://github.com/sanjay0423/jira-llm-automation) as the source of truth when explaining the program to stakeholders.**

---

## 1. What it does (elevator pitch)

When someone creates a Jira issue, an AI **automatically** adds a first-pass triage comment on the same issue with:

- **TL;DR** – one-line summary of likely cause or next step  
- **Hypothesis** – possible root causes  
- **Immediate checks** – concrete steps engineers can do now  
- **Questions for reporter** – clarifying questions  

No manual run required; it’s triggered by Jira the moment the issue is created. The goal is **faster triage and better consistency** for engineering (and related) teams.

---

## 2. High-level flow

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  Someone        │     │  Our service         │     │  Jira           │
│  creates a      │────▶│  (this repo)         │────▶│  adds the       │
│  Jira issue     │     │  LLM → hypothesis    │     │  AI comment     │
└─────────────────┘     └──────────────────────┘     └─────────────────┘
        │                           │
        │  Jira Automation          │  Returns one
        │  sends issue data         │  comment (text)
        │  (summary, description…)   │
        └───────────────────────────┘
```

- **Jira** = source of issues and where the comment appears.  
- **This repo** = the service that receives issue data, calls the LLM, and returns the comment text.  
- **Git** = single source of truth for how that service is built and run.

---

## 3. Repo as source of truth – what each part is for

Walk through the repo with stakeholders using this map. Everything that “is” the program lives here.

| File / folder | Purpose (for stakeholders) |
|---------------|----------------------------|
| **README.md** | Entry point: what the project does, how to run it, and how to wire Jira (quick start, env vars, rule summary). |
| **main.py** | Core application: HTTP endpoint Jira calls, prompt sent to the LLM, call to OpenAI (or compatible API), and response back to Jira. Defines the “contract” (what Jira sends, what we return). |
| **config.py** | Configuration from environment: secrets (tokens, API keys), model name, Jira base URL. No secrets in code; they’re in env / `.env`. |
| **triage_issue.py** | Optional script: “run triage for one issue now” (e.g. for an existing ticket). Fetches the issue from Jira, runs the same LLM logic, posts the comment via Jira API. Good for one-off use or testing. |
| **requirements.txt** | List of Python dependencies (FastAPI, OpenAI client, etc.). Ensures everyone runs the same stack. |
| **.env.example** | Template for environment variables (tokens, API keys, Jira URL). Copy to `.env` and fill in; actual `.env` is not in Git (security). |
| **AUTOMATIC_TRIAGE.md** | Step-by-step: how to turn on “automatic” mode (issue created → Jira calls our service → comment added). Useful for ops or anyone setting up the rule. |
| **JIRA_SETUP.md** | Detailed Jira-side setup: exposing the service (e.g. ngrok/deploy), creating the Automation rule, and testing. |
| **STAKEHOLDER_OVERVIEW.md** | This document: narrative for explaining the program and using the repo as the single source of truth. |

Nothing critical lives outside this repo; the “program” is what’s in Git plus the env/config you use when running it.

---

## 4. How we run it (without going deep into code)

- **Local / test:** Run the app on a laptop, expose it with a tunnel (e.g. ngrok). Jira Automation points to that URL. Good for demos and trying changes.  
- **Production / “always on”:** Deploy the same repo to a host (e.g. Railway, Render, internal server). Set the same env vars there; point the Jira rule at the deployed URL.  

The **same code and docs in Git** apply in both cases; only the URL and where env vars are set change.

---

## 5. Security and ownership (talking points)

- **Secrets:** All secrets (Jira API token, OpenAI key, triage token) are in environment variables, not in the repo. `.env` is in `.gitignore`.  
- **Who can trigger the service:** Only callers that send the correct `Authorization: Bearer <token>` (the triage token) are accepted. In production, only the Jira Automation rule (and anyone who knows that token) can trigger the endpoint.  
- **Data:** Issue summary and description are sent to the LLM to generate the comment. No PII is required by the prompt; teams can set policies (e.g. redact or limit which projects use this).  
- **Ownership:** The repo and this doc describe a team-owned, transparent solution: logic is in Git, behavior is documented, and changes are reviewable.

---

## 6. Quick “show the repo” script for the meeting

1. Open the repo (e.g. GitHub: `sanjay0423/jira-llm-automation`).  
2. **README.md** – “This is what it does and how you run it.”  
3. **main.py** – “This is the endpoint Jira calls and where the LLM is invoked; the contract is clear in code.”  
4. **config.py** – “Configuration and secrets live in the environment, not in code.”  
5. **triage_issue.py** – “Optional script to run triage on a single issue on demand.”  
6. **AUTOMATIC_TRIAGE.md** / **JIRA_SETUP.md** – “How we connect Jira to this service and keep it as the source of truth for setup.”  
7. **STAKEHOLDER_OVERVIEW.md** – “This document: we use the repo as the single source of truth to explain and run the program.”

---

## 7. Summary for stakeholders

- **What:** Automatic AI first-pass triage comment on new Jira issues (TL;DR, hypothesis, checks, questions).  
- **Where:** Logic and docs live in **this Git repo**; the repo is the **source of truth** for the program.  
- **How:** Jira Automation calls our service when an issue is created; the service uses an LLM and returns the comment; Jira posts it.  
- **Who:** Owned by the team; config and secrets in env; no “black box” – everything is in the repo and this overview.
