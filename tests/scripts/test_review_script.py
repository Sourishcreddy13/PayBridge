import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "claude_agent_review.py"
spec = importlib.util.spec_from_file_location("claude_agent_review", SCRIPT)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)  # the SDK is imported lazily, so this works without the AI extra


def good_report(verdict="PASS", status="PASS", findings=None):
    return {
        "verdict": verdict,
        "summary": "ok",
        "findings": findings or [],
        "criteria": [{"id": c, "status": status, "evidence": "tests"} for c in review.ACCEPTANCE + review.NON_FUNCTIONAL],
    }


def test_valid_report_parses_from_object_text_and_fence():
    data = good_report()
    assert review.parse_report(data).verdict == "PASS"
    assert review.parse_report(json.dumps(data)).verdict == "PASS"
    assert review.parse_report("```json\n" + json.dumps(data) + "\n```").verdict == "PASS"


@pytest.mark.parametrize("raw", ["not json at all", "[]", "{}", '{"verdict": "MAYBE"}', None])
def test_malformed_output_is_rejected(raw):
    with pytest.raises(ValueError):
        review.parse_report(raw)


def test_missing_or_unknown_criteria_are_rejected():
    data = good_report()
    data["criteria"].pop()
    with pytest.raises(ValueError, match="missing"):
        review.parse_report(data)
    data = good_report()
    data["criteria"].append({"id": "AC-99", "status": "PASS", "evidence": "x"})
    with pytest.raises(ValueError, match="unexpected"):
        review.parse_report(data)


def test_verdict_must_agree_with_findings():
    high = [{"id": "F-1", "severity": "HIGH", "criterion": "NFR-02", "file": "a.py", "line": 1, "evidence": "e", "recommendation": "r"}]
    with pytest.raises(ValueError, match="contradicts"):
        review.parse_report(good_report("PASS", findings=high))
    with pytest.raises(ValueError, match="no blocking"):
        review.parse_report(good_report("FAIL"))
    assert review.parse_report(good_report("FAIL", findings=high)).verdict == "FAIL"


def test_extra_fields_are_rejected():
    data = good_report()
    data["surprise"] = 1
    with pytest.raises(ValueError):
        review.parse_report(data)


def test_evaluator_may_run_checks_but_not_write():
    assert any(t.startswith("Bash(python -m pytest") for t in review.ALLOWED_TOOLS)
    assert not {"Write", "Edit"} & set(review.ALLOWED_TOOLS)
    assert {"Write", "Edit"} <= set(review.DISALLOWED_TOOLS)


def test_evidence_packet_contains_rubric_checks_and_schema(tmp_path):
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "app_spec.md").write_text("AC-01 something")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "m.py").write_text("x=1")
    packet = review.build_evidence_packet(tmp_path, [{"check": "pytest", "exit_code": 0, "tail": "ok"}])
    for needle in ("<rubric>", "AC-01 something", "deterministic_check_results", "src/m.py", "JSON Schema"):
        assert needle in packet
