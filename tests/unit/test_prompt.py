import re
import sys
from pathlib import Path

# Ensure project root is on sys.path so imports work when running pytest
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import JiraTriageRequest, build_prompt


def test_build_prompt_includes_core_fields_and_sections():
    payload = JiraTriageRequest(
        issueKey="JLA-123",
        summary="Daily revenue pipeline failing",
        description="Redshift load step timing out.",
        priority="High",
        issueType="Bug",
        projectKey="JLA",
        reporter="Sanjay Rane",
    )

    prompt = build_prompt(payload)

    # Core fields
    assert "JLA-123" in prompt
    assert "Daily revenue pipeline failing" in prompt
    assert "Redshift load step timing out." in prompt

    # Required sections
    for heading in ["TL;DR", "Hypothesis", "Immediate checks", "Questions for reporter"]:
        assert heading in prompt, f"Missing section: {heading}"

    # Safety preamble should be mentioned in the instructions
    assert "AI first pass" in prompt


def test_build_prompt_uses_placeholder_when_description_missing():
    payload = JiraTriageRequest(
        issueKey="JLA-124",
        summary="Kafka cluster upgrade task",
        description=None,
        priority=None,
        issueType=None,
        projectKey=None,
        reporter=None,
    )

    prompt = build_prompt(payload)

    assert "(no description)" in prompt

