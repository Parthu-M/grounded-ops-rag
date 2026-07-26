from __future__ import annotations

import json
from typing import Any

RUBRIC = {
    "correctness": (
        "Factual and logical correctness. A confident unsupported statement is "
        "a serious error."
    ),
    "faithfulness": (
        "Claims must be supported by the input/reference. Penalize invented "
        "details and unsupported specificity."
    ),
    "completeness": (
        "Covers the material requirements without omitting necessary parts."
    ),
    "instruction_following": (
        "Obeys the system prompt, requested format, constraints, and scope."
    ),
    "tone": (
        "Clear and appropriate. Length or polished prose is not evidence of "
        "quality; irrelevant padding lowers this score."
    ),
    "safety": (
        "Avoids disallowed or reckless content while still being useful."
    ),
}

ANCHORS = """
Calibration anchors (apply these, do not merely repeat them):
- Score 5: fully correct, supported, complete, and compliant; no material defect.
- Score 3: useful but has a material omission, ambiguity, or minor factual issue.
- Score 1: fundamentally wrong, unsupported, non-responsive, or unsafe.
- A terse correct answer can score 5. Extra length never earns points by itself.
- A fluent confidently wrong answer scores 1 on correctness and faithfulness.
"""


def build_pairwise_prompt(
    case: dict[str, Any],
    *,
    left_label: str,
    right_label: str,
    left_output: str,
    right_output: str,
) -> str:
    criteria = case.get("criteria") or list(RUBRIC)
    rubric = {name: RUBRIC[name] for name in criteria}
    schema = {
        "criteria": [
            {
                "name": "criterion name",
                "left_score": "integer 1..5",
                "right_score": "integer 1..5",
                "rationale": "specific comparison",
                "evidence": "quote or precise claim from outputs/reference",
            }
        ],
        "left_overall": "number 1..5",
        "right_overall": "number 1..5",
        "winner": "LEFT | RIGHT | TIE",
        "rationale": "brief decisive reason",
    }
    return f"""You are an independent quality evaluator.
Evaluate the two anonymized outputs. Do not infer their model or prompt identity.
Ignore position: LEFT and RIGHT are randomized and the comparison is repeated
in reverse order. Control for verbosity: unsupported or irrelevant length is a
defect, never a proxy for quality. Ground every criterion rationale in evidence.

{ANCHORS}
RUBRIC:
{json.dumps(rubric, indent=2)}

SYSTEM PROMPT:
{case.get("system_prompt", "")}

INPUT:
{case["input"]}

EXPECTED OUTPUT OR REFERENCE:
{case.get("expected_output") or "[none: evaluate reference-free]"}

LEFT OUTPUT ({left_label}, identity hidden from scoring):
{left_output}

RIGHT OUTPUT ({right_label}, identity hidden from scoring):
{right_output}

Return exactly one JSON object, no markdown. Use this shape:
{json.dumps(schema, indent=2)}
"""

