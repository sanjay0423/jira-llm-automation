# Jira LLM Automation – Stakeholder Overview

This document supports discussions with stakeholders using the [Git repository](https://github.com/sanjay0423/jira-llm-automation) as the single source of truth for the program.

---

## 1. Purpose and value

When a Jira work item is created, an AI-generated first-pass triage comment is added automatically to that item. The comment includes:

- **TL;DR** – One-line summary of likely cause or recommended next step  
- **Hypothesis** – Possible root causes  
- **Immediate checks** – Concrete steps engineers can take immediately  
- **Questions for reporter** – Clarifying questions to improve the ticket  

No manual step is required; Jira triggers the flow at creation time. The program aims to **shorten time-to-triage** and **standardize** first-pass analysis across engineering and related teams.

---

## 2. High-level flow

```
┌─────────────────────┐     ┌──────────────────────────┐     ┌─────────────────────┐
│  Work item created  │     │  Triage service          │     │  Jira                │
│  in Jira            │────▶│  (this repository)       │────▶│  adds AI comment    │
│                     │     │  LLM → hypothesis text   │     │  to the work item   │
└─────────────────────┘     └──────────────────────────┘     └─────────────────────┘
         │                                    │
         │  Jira Automation                   │  Returns a single
         │  (Send web request)                 │  comment string
         │  sends issue data                   │
         └────────────────────────────────────┘
```

- **Jira** – Source of work items and the surface where the comment appears.  
- **Triage service** – Application that receives issue data, calls the LLM, and returns the comment text. Implemented in this repository.  
- **Integration** – Implemented via **Jira Automation** (Send web request), not Jira webhooks. The Automation rule invokes the service and then adds the returned text as a comment.

---

## 3. Repository as source of truth

The following table maps each significant file or folder to its role. All program logic and documentation reside in this repository.

| File or folder | Purpose |
|----------------|---------|
| **README.md** | Entry point: project purpose, how to run the service, and how to configure the Jira Automation rule. Includes links to setup screenshots. |
| **main.py** | Core application: HTTP endpoint invoked by Jira, prompt construction, LLM call (OpenAI or compatible API), and response returned to Jira. Defines the request/response contract. |
| **config.py** | Configuration loaded from the environment: credentials (tokens, API keys), model name, Jira base URL. No secrets are stored in code; they are supplied via environment variables. |
| **triage_issue.py** | Optional CLI: run triage for a single existing issue (fetch from Jira, run same LLM logic, post comment via Jira API). Used for one-off triage or testing. |
| **requirements.txt** | Python dependencies (e.g. FastAPI, OpenAI client). Ensures a consistent runtime across environments. |
| **.env.example** | Template for required environment variables. The actual `.env` file is not committed; it is created locally and listed in `.gitignore`. |
| **docs/screenshots/** | Screenshots of the Jira Automation rule configuration (rule flow, Send web request, response variable). Referenced from the README. |
| **AUTOMATIC_TRIAGE.md** | Step-by-step guide for enabling automatic triage (work item created → service invoked → comment added). |
| **JIRA_SETUP.md** | Detailed Jira-side setup: exposing the service (e.g. ngrok or deployment), creating the Automation rule, and verifying behavior. |
| **STAKEHOLDER_OVERVIEW.md** | This document: program summary and repository walkthrough for stakeholder discussions. |

No critical logic or configuration lives outside this repository; the program is defined by the contents of the repo plus the environment configuration used at runtime.

---

## 4. Deployment and operation

- **Local or test** – The application is run on a developer machine and exposed via a tunnel (e.g. ngrok). The Jira Automation rule is pointed at that URL. Suitable for demos and iterative changes.  
- **Production** – The same repository is deployed to a hosted environment (e.g. Railway, Render, or an internal server). The same environment variables are configured there, and the Jira Automation rule is updated to use the deployed URL.  

The same code and documentation apply in both cases; only the endpoint URL and the location of environment configuration differ.

---

## 5. Security and governance

- **Secrets** – All sensitive values (Jira API token, OpenAI API key, triage authorization token) are provided via environment variables. The `.env` file is not committed.  
- **Access control** – The triage endpoint accepts requests only when the caller sends the expected `Authorization: Bearer <token>`. In production, the Jira Automation rule is configured with this token; possession of the token implies permission to invoke the service.  
- **Data** – Issue summary and description are sent to the LLM to generate the comment. The prompt does not require PII; teams may define policies (e.g. redaction or project-level eligibility) as needed.  
- **Ownership and transparency** – The solution is team-owned. Logic, behavior, and setup are documented in the repository; changes are reviewable and traceable in version control.

---

## 6. Suggested repository walkthrough for meetings

1. Open the repository (e.g. [github.com/sanjay0423/jira-llm-automation](https://github.com/sanjay0423/jira-llm-automation)).  
2. **README.md** – Describes what the program does and how to run and connect Jira.  
3. **main.py** – Shows the endpoint Jira calls and where the LLM is invoked; the contract is explicit in code.  
4. **config.py** – Shows that configuration and secrets are read from the environment.  
5. **triage_issue.py** – Optional script for on-demand triage of a single issue.  
6. **docs/screenshots/** – Reference screenshots for the Jira Automation rule setup.  
7. **AUTOMATIC_TRIAGE.md** / **JIRA_SETUP.md** – Step-by-step integration and setup.  
8. **STAKEHOLDER_OVERVIEW.md** – This document; positions the repository as the source of truth for the program.

---

## 7. Summary

| Aspect | Description |
|--------|-------------|
| **What** | Automatic, AI-generated first-pass triage comment on new Jira work items (TL;DR, hypothesis, immediate checks, questions for reporter). |
| **Where** | Logic and documentation live in this Git repository; the repository is the source of truth. |
| **How** | Jira Automation (Send web request) calls the triage service when a work item is created; the service calls the LLM and returns the comment; the Automation rule adds it to the work item. |
| **Who** | Team-owned; configuration and secrets are environment-based; design and behavior are documented and reviewable in the repository. |
