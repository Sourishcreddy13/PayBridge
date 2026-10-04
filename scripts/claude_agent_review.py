#!/usr/bin/env python3
"""Programmatic Claude Agent SDK reviewer for the PayBridge harness substrate."""
from __future__ import annotations

import argparse
from pathlib import Path

import anyio

try:
    from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query
except ImportError as exc:  # pragma: no cover - dependency is optional in local runtime
    raise SystemExit("Install AI extras with `pip install -e '.[ai]'` before running this script.") from exc


async def run_review(repo: Path) -> None:
    prompt = f"""
Review the repository at {repo} against specs/app_spec.md.\n
Evaluate AC-01 through AC-10 and NFR-01 through NFR-08.\n
Focus on duplicate creation, illegal transitions, money precision, append-only storage, PII masking, controller RBAC, structured logging, health latency, reconciliation and settlement immutability.\n
Return a concise JSON object with keys: status, findings, ac_coverage, nfr_coverage.\n"""
    options = ClaudeAgentOptions(max_turns=2, allowed_tools=["Read"], verbatim_prompts=True)
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    anyio.run(run_review, Path(args.repo).resolve())


if __name__ == "__main__":
    main()
