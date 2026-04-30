"""Shared LLM-as-Judge plumbing.

The judge is a tightly-prompted Ollama call that scores an agent's output
against a rubric. We use the SAME local model that powers the agents — no
paid APIs allowed by the assignment. We document this self-judging risk in
the technical report.

The judge always returns:
    {
      "score": 0.0..1.0,
      "verdict": "pass" | "fail",
      "reasons": [string]
    }

Each per-agent judge file (`judge_*.py`) provides:
    * a list of `Case` test fixtures
    * a rubric prompt
    * a function that converts the agent's output + the case into the user
      prompt for the judge
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from rxsentinel.llm import get_ollama_client


JUDGE_SYSTEM = """You are a strict evaluation judge.

You will be given:
  1. A rubric describing what correct behavior looks like.
  2. The input that was given to a model under test.
  3. The model's output.

You must score how well the output satisfies the rubric.

Return ONLY valid JSON:
{
  "score": <number from 0.0 to 1.0>,
  "verdict": "pass" | "fail",
  "reasons": [<short strings>]
}

Pass ONLY if the output:
  - Satisfies every "must" in the rubric.
  - Contains no fabricated facts beyond what the input supports.
  - Is well-formed (correct structure / format).
"""


@dataclass(slots=True)
class Case:
    """One judged test case."""

    name: str
    input: Any
    expected: dict[str, Any]


@dataclass(slots=True)
class JudgeResult:
    case: str
    score: float
    verdict: str
    reasons: list[str]


async def judge(rubric: str, agent_input: str, agent_output: str) -> JudgeResult:
    """Run the judge on one (input, output) pair against a rubric.

    Args:
        rubric: A short, structured rubric explaining what "good" looks like.
        agent_input: The string input the agent received.
        agent_output: The string output the agent produced.

    Returns:
        JudgeResult with score, verdict, and reasons.
    """
    client = get_ollama_client()
    user_prompt = (
        f"RUBRIC:\n{rubric}\n\n"
        f"INPUT TO MODEL:\n{agent_input}\n\n"
        f"MODEL OUTPUT:\n{agent_output}\n"
    )
    try:
        result = await client.chat_json(
            system=JUDGE_SYSTEM,
            user=user_prompt,
            temperature=0.0,
        )
    except Exception as e:  # noqa: BLE001
        return JudgeResult("?", 0.0, "fail", [f"judge raised: {e}"])

    score = float(result.get("score", 0))
    verdict = str(result.get("verdict", "fail"))
    reasons = list(result.get("reasons", []))
    return JudgeResult("?", score, verdict, reasons)


async def run_judge_suite(
    name: str,
    cases: list[Case],
    runner: Callable[[Case], Awaitable[tuple[str, str]]],
    rubric: str,
) -> list[JudgeResult]:
    """Run a list of cases through (a) the agent under test, and (b) the judge.

    Args:
        name: Suite name for logging.
        cases: List of test cases.
        runner: Async function that takes a Case, returns (input_repr, output_repr).
        rubric: The rubric to grade against.

    Returns:
        A list of JudgeResult, one per case.
    """
    results: list[JudgeResult] = []
    for case in cases:
        agent_input, agent_output = await runner(case)
        r = await judge(rubric, agent_input, agent_output)
        r.case = case.name
        results.append(r)
        print(
            f"[{name}] {case.name}: {r.verdict} (score={r.score:.2f}) "
            f"reasons={r.reasons[:1] if r.reasons else []}"
        )
    return results


def print_summary(suite_name: str, results: list[JudgeResult]) -> dict[str, float]:
    passed = sum(1 for r in results if r.verdict == "pass")
    avg_score = sum(r.score for r in results) / max(len(results), 1)
    print(
        f"\n{'='*60}\n{suite_name}: {passed}/{len(results)} pass | "
        f"avg score = {avg_score:.2f}\n{'='*60}\n"
    )
    return {"pass_rate": passed / max(len(results), 1), "avg_score": avg_score}


def main_dispatch(suite_runner: Callable[[], Awaitable[None]]) -> None:
    """Tiny CLI helper: `python -m rxsentinel.evals.judge_xxx`."""
    asyncio.run(suite_runner())
