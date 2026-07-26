from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from ai_takehome.common import estimate_tokens, tokenize
from ai_takehome.judge.prompts import RUBRIC


@dataclass(frozen=True)
class JudgeResponse:
    raw: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str
    usage_estimated: bool


class JudgeClient(Protocol):
    family: str

    def judge(
        self, prompt: str, payload: dict[str, Any]
    ) -> JudgeResponse: ...


def _f1(left: list[str], right: list[str]) -> float:
    if not left or not right:
        return 0.0
    common = sum(min(left.count(item), right.count(item)) for item in set(left))
    precision = common / len(left)
    recall = common / len(right)
    return (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )


class HeuristicJudge:
    """Transparent deterministic CI oracle; explicitly not an LLM."""

    family = "deterministic-rules"
    model = "heuristic-ci-v1"
    provider = "heuristic"

    def _scores(
        self,
        output: str,
        expected: str | None,
        input_text: str,
        criteria: list[str],
    ) -> dict[str, float]:
        output_tokens = tokenize(output)
        reference_tokens = tokenize(expected or "")
        input_tokens = tokenize(input_text)
        reference_f1 = (
            _f1(output_tokens, reference_tokens) if reference_tokens else 0.6
        )
        reference_recall = (
            sum(
                min(output_tokens.count(item), reference_tokens.count(item))
                for item in set(reference_tokens)
            )
            / max(1, len(reference_tokens))
            if reference_tokens
            else 0.6
        )
        supported = set(reference_tokens) | set(input_tokens)
        content = [
            token
            for token in output_tokens
            if len(token) > 2 and token not in {"the", "and", "for", "with"}
        ]
        support_ratio = (
            sum(token in supported for token in content) / len(content)
            if content
            else 0.0
        )
        verbosity_ratio = len(output_tokens) / max(1, len(reference_tokens))
        padding_penalty = min(1.5, max(0.0, verbosity_ratio - 2.0) * 0.18)
        base = {
            "correctness": 1 + 4 * reference_f1,
            "faithfulness": 1 + 4 * support_ratio,
            "completeness": 1 + 4 * reference_recall,
            "instruction_following": 4.5 if output.strip() else 1.0,
            "tone": 4.5 - padding_penalty,
            "safety": 4.5,
        }
        return {
            criterion: round(
                max(1.0, min(5.0, base.get(criterion, 3.0))), 2
            )
            for criterion in criteria
        }

    def judge(
        self, prompt: str, payload: dict[str, Any]
    ) -> JudgeResponse:
        case = payload["case"]
        criteria = case.get("criteria") or list(RUBRIC)
        left = self._scores(
            payload["left_output"],
            case.get("expected_output"),
            case["input"],
            criteria,
        )
        right = self._scores(
            payload["right_output"],
            case.get("expected_output"),
            case["input"],
            criteria,
        )
        left_overall = sum(left.values()) / len(left)
        right_overall = sum(right.values()) / len(right)
        if abs(left_overall - right_overall) < 0.15:
            winner = "TIE"
        else:
            winner = "LEFT" if left_overall > right_overall else "RIGHT"
        verdict = {
            "criteria": [
                {
                    "name": criterion,
                    "left_score": left[criterion],
                    "right_score": right[criterion],
                    "rationale": (
                        f"Reference/support signals: left {left[criterion]:.2f}, "
                        f"right {right[criterion]:.2f}."
                    ),
                    "evidence": (
                        "Deterministic lexical overlap and unsupported-length "
                        "features; this CI oracle is not an LLM judgment."
                    ),
                }
                for criterion in criteria
            ],
            "left_overall": round(left_overall, 3),
            "right_overall": round(right_overall, 3),
            "winner": winner,
            "rationale": (
                "Winner is the higher rubric mean after unsupported-length "
                "penalty."
            ),
        }
        raw_json = json.dumps(verdict)
        # Exercise the fenced-JSON recovery path deterministically.
        raw = (
            f"```json\n{raw_json}\n```"
            if sum(ord(char) for char in case["id"]) % 3 == 0
            else raw_json
        )
        return JudgeResponse(
            raw=raw,
            input_tokens=estimate_tokens(prompt),
            output_tokens=estimate_tokens(raw),
            model=self.model,
            provider="heuristic",
            usage_estimated=True,
        )


class OpenAIJudge:
    def __init__(self, model: str, family: str) -> None:
        from openai import OpenAI

        self.client = OpenAI()
        self.model = model
        self.family = family
        self.provider = "openai"

    def judge(
        self, prompt: str, payload: dict[str, Any]
    ) -> JudgeResponse:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Apply the supplied rubric independently and return "
                        "strict JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        raw = response.output_text
        usage = getattr(response, "usage", None)
        return JudgeResponse(
            raw=raw,
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            model=self.model,
            provider="openai",
            usage_estimated=False,
        )


def build_judge(provider: str, model: str, family: str) -> JudgeClient:
    if provider == "heuristic":
        return HeuristicJudge()
    if provider == "openai":
        return OpenAIJudge(model, family)
    raise ValueError(f"Unsupported JUDGE_PROVIDER: {provider}")
