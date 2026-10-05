#!/usr/bin/env python3
"""Programmatic Claude Agent SDK evaluator for PayBridge.

The evaluator is given a structured evidence packet (requirements, deterministic check results,
repository facts, a rubric and an example), may run a small allowlist of read-only validation
commands, and must answer with JSON matching ``ReviewReport``. The answer is parsed and validated;
anything malformed fails the run. The validated report is persisted as an artifact so CI can
publish it and a human can audit it.

Usage:  python scripts/claude_agent_review.py --repo . [--output review-report.json]
Exit codes: 0 = PASS, 1 = FAIL verdict, 2 = evaluator output invalid / could not run.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

ACCEPTANCE = [f"AC-{i:02d}" for i in range(1, 11)]
NON_FUNCTIONAL = [f"NFR-{i:02d}" for i in range(1, 9)]

# Read-only inspection plus the project's own deterministic gates. No Write/Edit/Web tools.
ALLOWED_TOOLS = [
    "Read",
    "Grep",
    "Glob",
    "Bash(python -m pytest:*)",
    "Bash(python -m mypy:*)",
    "Bash(ruff check:*)",
    "Bash(lint-imports)",
    "Bash(bash .claude/hooks/amount-precision-check.sh)",
    "Bash(bash .claude/hooks/payment-immutability-check.sh)",
    "Bash(bash .claude/hooks/masked-pii-check.sh)",
]
DISALLOWED_TOOLS = ["Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch"]

RUBRIC = """\
Priority order: (1) money correctness and atomicity, (2) lifecycle/state-machine integrity,
(3) authorization and audit attribution, (4) immutability of audit/routing/settlement evidence,
(5) idempotency of creation, refunds, imports, reconciliation, settlement, (6) observability.
A criterion is PASS only with evidence you observed (file:line or a command result you ran);
otherwise it is FAIL or UNVERIFIED. Never infer a pass from names or comments."""

EXAMPLE = {
    "verdict": "FAIL",
    "summary": "One blocking finding.",
    "findings": [
        {
            "id": "F-1",
            "severity": "HIGH",
            "criterion": "NFR-02",
            "file": "src/paybridge/infrastructure/example.py",
            "line": 42,
            "evidence": "execute('UPDATE payments ...') found at example.py:42",
            "recommendation": "Append a new row instead of updating.",
        }
    ],
    "criteria": [{"id": "AC-01", "status": "PASS", "evidence": "tests/integration/test_payment_flow.py::test_AC_01"}],
}


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=20)
    severity: Literal["CRITICAL", "HIGH", "MED", "LOW"]
    criterion: str = Field(pattern=r"^(AC|NFR)-\d{2}$")
    file: str = Field(min_length=1, max_length=300)
    line: int | None = Field(default=None, ge=1)
    evidence: str = Field(min_length=1, max_length=2000)
    recommendation: str = Field(min_length=1, max_length=2000)


class Criterion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^(AC|NFR)-\d{2}$")
    status: Literal["PASS", "FAIL", "UNVERIFIED"]
    evidence: str = Field(min_length=1, max_length=2000)


class ReviewReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: Literal["PASS", "FAIL"]
    summary: str = Field(min_length=1, max_length=4000)
    findings: list[Finding]
    criteria: list[Criterion]

    def check_consistency(self) -> None:
        """Reject reports whose verdict contradicts their own content or that skip criteria."""
        expected = set(ACCEPTANCE + NON_FUNCTIONAL)
        reported = {c.id for c in self.criteria}
        if reported != expected:
            missing = sorted(expected - reported)
            extra = sorted(reported - expected)
            raise ValueError(f"criteria mismatch: missing={missing} unexpected={extra}")
        blocking = any(f.severity in {"CRITICAL", "HIGH"} for f in self.findings)
        failing = any(c.status != "PASS" for c in self.criteria)
        if self.verdict == "PASS" and (blocking or failing):
            raise ValueError("verdict PASS contradicts findings/criteria")
        if self.verdict == "FAIL" and not (blocking or failing):
            raise ValueError("verdict FAIL has no blocking finding or failing criterion")


REPORT_SCHEMA: dict[str, Any] = ReviewReport.model_json_schema()


def parse_report(raw: Any) -> ReviewReport:
    """Parse model output (structured object or text containing one JSON object) and validate it."""
    data: Any = raw
    if isinstance(raw, str):
        text = raw.strip()
        fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
        if fenced:
            text = fenced.group(1)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"evaluator did not return JSON: {exc}") from exc
    try:
        report = ReviewReport.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"evaluator JSON failed schema validation: {exc}") from exc
    report.check_consistency()
    return report


def run_check(repo: Path, label: str, command: list[str]) -> dict[str, Any]:
    """Run one deterministic gate and capture a bounded result for the evidence packet."""
    try:
        done = subprocess.run(command, cwd=repo, capture_output=True, text=True, timeout=600, check=False)
        output = (done.stdout + done.stderr).strip()
        return {"check": label, "exit_code": done.returncode, "tail": output[-1500:]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"check": label, "exit_code": None, "tail": f"could not run: {exc}"}


def collect_checks(repo: Path) -> list[dict[str, Any]]:
    py = sys.executable
    return [
        run_check(repo, "pytest", [py, "-m", "pytest", "-q", "-x", "--no-header", "-p", "no:cacheprovider"]),
        run_check(repo, "mypy", [py, "-m", "mypy"]),
        run_check(repo, "ruff", ["ruff", "check", "src", "tests", "scripts"]),
        run_check(repo, "import-linter", ["lint-imports"]),
        *[
            run_check(repo, hook, ["bash", f".claude/hooks/{hook}.sh"])
            for hook in ("amount-precision-check", "payment-immutability-check", "masked-pii-check")
        ],
    ]


def build_evidence_packet(repo: Path, checks: list[dict[str, Any]]) -> str:
    spec = (repo / "specs" / "app_spec.md").read_text(encoding="utf-8")
    layout = sorted(
        str(p.relative_to(repo)) for p in (repo / "src").rglob("*.py") if "__pycache__" not in p.parts
    )
    packet = {
        "repository": str(repo),
        "requirements_file": "specs/app_spec.md",
        "criteria_to_judge": ACCEPTANCE + NON_FUNCTIONAL,
        "deterministic_check_results": checks,
        "source_files": layout,
    }
    return (
        "You are the independent evaluator for the PayBridge repository.\n\n"
        f"<rubric>\n{RUBRIC}\n</rubric>\n\n"
        f"<requirements>\n{spec}\n</requirements>\n\n"
        f"<evidence_packet>\n{json.dumps(packet, indent=2)}\n</evidence_packet>\n\n"
        f"<output_contract>\nReturn ONLY one JSON object matching this JSON Schema, with exactly one "
        f"entry in `criteria` for every id in criteria_to_judge:\n{json.dumps(REPORT_SCHEMA)}\n"
        f"Example of the shape (content is illustrative):\n{json.dumps(EXAMPLE)}\n</output_contract>"
    )


async def run_review(repo: Path, output: Path) -> ReviewReport:
    # Imported lazily so the validation helpers above are usable without the optional AI extra.
    from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

    prompt = build_evidence_packet(repo, collect_checks(repo))
    options = ClaudeAgentOptions(
        cwd=str(repo),
        max_turns=40,
        allowed_tools=ALLOWED_TOOLS,
        disallowed_tools=DISALLOWED_TOOLS,
        permission_mode="dontAsk",
        output_format={"type": "json_schema", "schema": REPORT_SCHEMA},
    )
    result: ResultMessage | None = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            result = message
    if result is None or result.is_error:
        raise RuntimeError(f"evaluator run failed: {getattr(result, 'errors', None) or 'no result message'}")
    report = parse_report(result.structured_output if result.structured_output is not None else result.result)
    output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def main() -> int:
    import anyio

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--output", default="review-report.json")
    args = parser.parse_args()
    try:
        report = anyio.run(run_review, Path(args.repo).resolve(), Path(args.output))
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"REVIEW INVALID: {exc}", file=sys.stderr)
        return 2
    print(f"{report.verdict}: {report.summary} (report: {args.output})")
    return 0 if report.verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
