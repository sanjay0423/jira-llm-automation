import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import JiraTriageRequest, _sanitize_json_body


def _make_body(data: dict, inject_control: bool = False) -> bytes:
    text = json.dumps(data)
    if inject_control:
        # Inject a vertical tab and other control chars that would break strict JSON parsing
        text = text.replace("description", "descri\x0bption")
    return text.encode("utf-8")


def test_sanitize_json_body_parses_valid_json_unchanged():
    data = {
        "issueKey": "JLA-200",
        "summary": "Simple summary",
        "description": "Normal description",
    }
    body = _make_body(data)

    result = _sanitize_json_body(body)

    assert isinstance(result, JiraTriageRequest)
    assert result.issueKey == "JLA-200"
    assert result.summary == "Simple summary"
    assert result.description == "Normal description"


def test_sanitize_json_body_handles_control_characters():
    data = {
        "issueKey": "JLA-201",
        "summary": "Summary with control chars",
        "description": "Line1\nLine2",
    }
    body = _make_body(data, inject_control=True)

    result = _sanitize_json_body(body)

    # Parsing should still succeed and key fields should be present
    assert result.issueKey == "JLA-201"
    assert "Summary with control chars" in result.summary


def test_sanitize_json_body_raises_on_invalid_json():
    # Truncated JSON that cannot be recovered by sanitization
    bad_body = b'{"issueKey": "JLA-202", "summary": "oops"'

    with pytest.raises(json.JSONDecodeError):
        _sanitize_json_body(bad_body)

