# AGENTS.md

This repository contains a Jira Automation + LLM triage service. The agent should use this file as the primary instruction layer for any work in this repo.

## Mission

Help the team generate a high-quality first-pass Jira triage comment using:

- Jira issue content
- Internal knowledge sources through RAG
- A structured, safe, and concise response format

The goal is to produce comments that are useful to engineers, clearly labeled as AI-generated, and grounded in available context.

## Operating principles

- Prefer correctness over cleverness.
- If evidence is weak, say so explicitly.
- Do not invent root causes, fixes, or ownership.
- Keep outputs concise, actionable, and professional.
- Use the repository as the source of truth for code, docs, and setup steps.
- Treat Jira Automation as the trigger mechanism. Do not describe the flow as a webhook-based integration.

## Knowledge sources

When available, use the following sources in order of preference:

1. Jira issue summary, description, type, priority, project, and reporter
2. Internal wiki / Confluence / runbooks
3. Selected GitHub repositories and docs
4. Existing repository documentation

For RAG, prioritize:

- Runbooks
- Troubleshooting guides
- Service READMEs
- Architecture docs
- Relevant code snippets only when documentation is insufficient

## Response format

When drafting a Jira triage comment, use this structure:

- `TL;DR`
- `Hypothesis`
- `Immediate checks`
- `Questions for reporter`

Additional rules:

- Start with a short safety line such as: `AI first pass – please validate before following.`
- Be specific about uncertainty.
- Keep bullet points short.
- Include links or references when they are available from retrieved context.

## RAG behavior

- Retrieve only the most relevant snippets.
- Prefer small, high-signal context over large dumps.
- If retrieved sources conflict, mention the conflict and avoid overcommitting.
- If no useful context is found, proceed with a conservative answer and clearly state the gap.

## Testing expectations

- Add or update tests when changing prompt behavior, retrieval logic, or response formatting.
- Prefer unit tests for pure logic.
- Prefer component tests for endpoint behavior.
- Keep regression fixtures for representative Jira issues.

## Security and privacy

- Never commit secrets.
- Do not expose tokens, credentials, or private internal URLs in generated comments.
- Minimize the amount of sensitive data passed to the LLM.
- Respect project boundaries and access controls for internal sources.

## Implementation guidance

- Keep the FastAPI endpoint stable unless the change requires an interface update.
- Preserve the response contract: `{ "comment": "<markdown>" }`.
- If a change affects Jira Automation fields or smart values, update docs and tests together.
- Prefer small, reviewable changes.

## Documentation style

- Use clear, professional language.
- Keep stakeholder-facing docs neutral and concise.
- Use `README.md` for setup, `JIRA_SETUP.md` for Jira configuration, and `STAKEHOLDER_OVERVIEW.md` for business-facing explanation.

