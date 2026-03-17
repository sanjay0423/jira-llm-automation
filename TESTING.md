# Testing Jira LLM Automation

This service uses **pytest** for unit and component tests. The goal is to keep tests fast, deterministic, and easy to run locally and in CI.

## Setup

```bash
cd ~/code/jira-llm-automation
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Test layout

- `tests/unit/` – Pure unit tests:
  - `test_prompt.py` – prompt construction (`build_prompt`)
  - `test_sanitize_json.py` – JSON sanitization (`_sanitize_json_body`)
  - `test_auth_and_config.py` – bearer token verification and settings behavior
- `tests/component/` – Endpoint and service-level tests (to be added).
- `tests/integration/` – Integration and regression tests (to be added).

## Running tests

Run all tests:

```bash
pytest
```

Run only unit tests:

```bash
pytest tests/unit
```

As additional component and integration tests are added, they will live under `tests/component` and `tests/integration` and can be run in the same way.

