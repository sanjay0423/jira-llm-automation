# Jira Automation rule – screenshots

These screenshots show the **Jira Automation** rule setup (not webhooks). They were captured when configuring the “LLM triage: add hypothesis comment” rule.

| File | What it shows |
|------|----------------|
| **1-rule-flow-and-details.png** | Rule flow: When (Work item created) → Then (Send web request) → And (Add comment to work item). Rule details with scope set to Global. |
| **2-send-web-request-config.png** | Send web request: URL, POST method, custom JSON body with issue smart values, and headers (Content-Type, Authorization). |
| **3-send-web-request-response-values.png** | How to use the response in the next step: `{{webResponse.body.comment}}` for the comment body. |

Refer to the main [README](../README.md) for the full setup steps.
