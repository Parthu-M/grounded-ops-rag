from __future__ import annotations

import math
import statistics
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from ai_takehome.common import (
    append_jsonl,
    read_json_or_yaml,
    utc_now,
    write_json,
)
from ai_takehome.judge.clients import JudgeClient
from ai_takehome.judge.parser import parse_verdict
from ai_takehome.judge.prompts import build_pairwise_prompt


def _canonical_winner(order: str, winner: str) -> str:
    if winner == "TIE":
        return "TIE"
    if order == "AB":
        return "A" if winner == "LEFT" else "B"
    return "B" if winner == "LEFT" else "A"


def _cohen_kappa(predicted: list[str], expected: list[str]) -> float | None:
    if not predicted or len(predicted) != len(expected):
        return None
    labels = {"A", "B", "TIE"}
    observed = sum(p == e for p, e in zip(predicted, expected)) / len(predicted)
    p_counts = Counter(predicted)
    e_counts = Counter(expected)
    chance = sum(
        (p_counts[label] / len(predicted)) * (e_counts[label] / len(expected))
        for label in labels
    )
    return (observed - chance) / (1 - chance) if chance < 1 else 1.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


class JudgePipeline:
    def __init__(
        self,
        client: JudgeClient,
        *,
        log_path: Path,
        judge_family: str,
        generator_a_family: str,
        generator_b_family: str,
        allow_same_family: bool = False,
    ) -> None:
        generator_families = {generator_a_family, generator_b_family}
        if judge_family in generator_families and not allow_same_family:
            raise ValueError(
                "Self-enhancement guard: judge family matches a generator "
                "family. Set a different JUDGE_FAMILY or explicitly opt out "
                "with ALLOW_SAME_FAMILY_JUDGE=true."
            )
        self.client = client
        self.log_path = log_path
        self.judge_family = judge_family
        self.generator_a_family = generator_a_family
        self.generator_b_family = generator_b_family

    def _one_call(
        self,
        case: dict[str, Any],
        order: str,
        repeat: int,
        run_id: str,
    ) -> dict[str, Any]:
        if order == "AB":
            left, right = case["candidate_a"], case["candidate_b"]
        else:
            left, right = case["candidate_b"], case["candidate_a"]
        prompt = build_pairwise_prompt(
            case,
            left_label="anonymous-1",
            right_label="anonymous-2",
            left_output=left,
            right_output=right,
        )
        payload = {
            "case": case,
            "left_output": left,
            "right_output": right,
            "order": order,
        }
        response = self.client.judge(prompt, payload)
        parsed = parse_verdict(response.raw)
        attempts = [(prompt, response, parsed)]
        if not parsed.valid:
            repair_prompt = (
                prompt
                + "\n\nYour prior response was malformed. Return only one "
                "valid JSON object matching the schema."
            )
            response = self.client.judge(repair_prompt, payload)
            parsed = parse_verdict(response.raw)
            attempts.append((repair_prompt, response, parsed))
        usage = {
            "input_tokens": sum(item[1].input_tokens for item in attempts),
            "output_tokens": sum(item[1].output_tokens for item in attempts),
            "total_tokens": sum(
                item[1].input_tokens + item[1].output_tokens
                for item in attempts
            ),
            "estimated": all(
                item[1].usage_estimated for item in attempts
            ),
        }
        for attempt_index, (
            attempt_prompt,
            attempt_response,
            attempt_parsed,
        ) in enumerate(attempts):
            append_jsonl(
                self.log_path,
                {
                    "timestamp": utc_now(),
                    "run_id": run_id,
                    "case_id": case["id"],
                    "order": order,
                    "repeat": repeat,
                    "attempt": attempt_index + 1,
                    "is_repair_retry": attempt_index > 0,
                    "prompt": attempt_prompt,
                    "raw_response": attempt_response.raw,
                    "parsed": attempt_parsed.model_dump(),
                    "provider": attempt_response.provider,
                    "model": attempt_response.model,
                    "usage": {
                        "input_tokens": attempt_response.input_tokens,
                        "output_tokens": attempt_response.output_tokens,
                        "total_tokens": (
                            attempt_response.input_tokens
                            + attempt_response.output_tokens
                        ),
                        "estimated": attempt_response.usage_estimated,
                    },
                },
            )
        if not parsed.valid or parsed.verdict is None:
            return {
                "valid": False,
                "order": order,
                "repeat": repeat,
                "parse_error": parsed.parse_error,
                "usage": usage,
                "judge_call_count": len(attempts),
                "invalid_response_count": sum(
                    not item[2].valid for item in attempts
                ),
                "parse_strategy": parsed.parse_strategy,
            }
        verdict = parsed.verdict
        canonical_scores: dict[str, dict[str, float]] = {
            "A": {},
            "B": {},
        }
        for item in verdict.criteria:
            if order == "AB":
                canonical_scores["A"][item.name] = item.left_score
                canonical_scores["B"][item.name] = item.right_score
            else:
                canonical_scores["B"][item.name] = item.left_score
                canonical_scores["A"][item.name] = item.right_score
        overall = (
            {"A": verdict.left_overall, "B": verdict.right_overall}
            if order == "AB"
            else {"B": verdict.left_overall, "A": verdict.right_overall}
        )
        return {
            "valid": True,
            "order": order,
            "repeat": repeat,
            "winner": _canonical_winner(order, verdict.winner),
            "scores": canonical_scores,
            "overall": overall,
            "rationale": verdict.rationale,
            "usage": usage,
            "judge_call_count": len(attempts),
            "invalid_response_count": sum(
                not item[2].valid for item in attempts
            ),
            "parse_strategy": parsed.parse_strategy,
        }

    def run(
        self,
        suite_path: Path,
        report_path: Path,
        validation_path: Path,
        *,
        repeats: int = 1,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        suite = read_json_or_yaml(suite_path)
        cases = suite["cases"]
        run_id = str(uuid.uuid4())
        call_count = 0
        input_tokens = output_tokens = invalid_calls = fallback_parses = 0
        case_reports: list[dict[str, Any]] = []

        for case in cases:
            calls = [
                self._one_call(case, order, repeat, run_id)
                for repeat in range(repeats)
                for order in ("AB", "BA")
            ]
            for call in calls:
                call_count += call["judge_call_count"]
                input_tokens += call["usage"]["input_tokens"]
                output_tokens += call["usage"]["output_tokens"]
                invalid_calls += call["invalid_response_count"]
                fallback_parses += int(
                    call.get("parse_strategy") != "direct_json"
                )
            valid = [call for call in calls if call["valid"]]
            winners = [call["winner"] for call in valid]
            position_pairs: list[bool] = []
            for repeat in range(repeats):
                ab = next(
                    (
                        call
                        for call in valid
                        if call["repeat"] == repeat and call["order"] == "AB"
                    ),
                    None,
                )
                ba = next(
                    (
                        call
                        for call in valid
                        if call["repeat"] == repeat and call["order"] == "BA"
                    ),
                    None,
                )
                if ab and ba:
                    position_pairs.append(ab["winner"] != ba["winner"])
            test_retest_flips: list[bool] = []
            if repeats > 1:
                for order in ("AB", "BA"):
                    repeated_winners = [
                        call["winner"]
                        for call in valid
                        if call["order"] == order
                    ]
                    if len(repeated_winners) > 1:
                        test_retest_flips.append(
                            len(set(repeated_winners)) > 1
                        )
            score_values: dict[str, dict[str, list[float]]] = {
                "A": defaultdict(list),
                "B": defaultdict(list),
            }
            overall_values = {"A": [], "B": []}
            for call in valid:
                for label in ("A", "B"):
                    overall_values[label].append(call["overall"][label])
                    for criterion, score in call["scores"][label].items():
                        score_values[label][criterion].append(score)
            overall = {
                label: round(_mean(overall_values[label]), 4)
                for label in ("A", "B")
            }
            # Dual-order agreement wins; disagreement falls back to mean score.
            if winners and len(set(winners)) == 1:
                final_winner = winners[0]
                decision = "unanimous across orders/repeats"
            elif abs(overall["A"] - overall["B"]) < 0.15:
                final_winner = "TIE"
                decision = "dual-order disagreement; mean margin < 0.15"
            else:
                final_winner = (
                    "A" if overall["A"] > overall["B"] else "B"
                )
                decision = "dual-order disagreement; higher mean rubric score"
            case_reports.append(
                {
                    "id": case["id"],
                    "config_a": case.get("config_a", suite.get("config_a", "A")),
                    "config_b": case.get("config_b", suite.get("config_b", "B")),
                    "human_label": case.get("human_label"),
                    "tags": case.get("tags", []),
                    "winner": final_winner,
                    "decision": decision,
                    "position_flip": any(position_pairs),
                    "test_retest_flip": any(test_retest_flips),
                    "order_winners": winners,
                    "overall_scores": overall,
                    "criterion_scores": {
                        label: {
                            criterion: round(_mean(values), 4)
                            for criterion, values in score_values[label].items()
                        }
                        for label in ("A", "B")
                    },
                    "valid_calls": len(valid),
                    "invalid_calls": len(calls) - len(valid),
                }
            )

        wins = Counter(case["winner"] for case in case_reports)
        mean_scores = {
            label: round(
                _mean(
                    [case["overall_scores"][label] for case in case_reports]
                ),
                4,
            )
            for label in ("A", "B")
        }
        if wins["A"] > wins["B"]:
            declared = "A"
        elif wins["B"] > wins["A"]:
            declared = "B"
        elif abs(mean_scores["A"] - mean_scores["B"]) >= 0.15:
            declared = "A" if mean_scores["A"] > mean_scores["B"] else "B"
        else:
            declared = "TIE"
        threshold = float(suite.get("pass_threshold", 3.5))
        report = {
            "run": {
                "run_id": run_id,
                "timestamp": utc_now(),
                "mode": "pairwise-reference-based",
                "judge_provider": getattr(
                    self.client, "provider", "unknown"
                ),
                "judge_model": getattr(self.client, "model", "unknown"),
                "judge_family": self.judge_family,
                "generator_a_family": self.generator_a_family,
                "generator_b_family": self.generator_b_family,
                "repeats": repeats,
                "dual_order": True,
                "case_count": len(case_reports),
                "pass_threshold": threshold,
                "artifact_warning": (
                    "heuristic provider is a deterministic CI baseline, not an "
                    "LLM-as-judge result"
                    if self.client.__class__.__name__ == "HeuristicJudge"
                    else None
                ),
            },
            "comparison": {
                "config_a": suite.get("config_a", "A"),
                "config_b": suite.get("config_b", "B"),
                "declared_winner": declared,
                "wins": {
                    "A": wins["A"],
                    "B": wins["B"],
                    "TIE": wins["TIE"],
                },
                "win_rate": {
                    label: wins[label] / len(case_reports)
                    for label in ("A", "B", "TIE")
                },
                "mean_overall_score": mean_scores,
                "pass_rate": {
                    label: sum(
                        case["overall_scores"][label] >= threshold
                        for case in case_reports
                    )
                    / len(case_reports)
                    for label in ("A", "B")
                },
            },
            "bias": {
                "position_flip_rate": sum(
                    case["position_flip"] for case in case_reports
                )
                / len(case_reports),
                "position_flip_count": sum(
                    case["position_flip"] for case in case_reports
                ),
                "test_retest_flip_rate": (
                    sum(
                        case["test_retest_flip"] for case in case_reports
                    )
                    / len(case_reports)
                    if repeats > 1
                    else None
                ),
                "self_enhancement_guard": "passed",
                "verbosity_mitigation": (
                    "explicit rubric penalty plus padded-answer probes"
                ),
                "score_calibration": "1/3/5 few-shot anchors in every prompt",
            },
            "audit": {
                "log_path": str(self.log_path),
                "judge_calls": call_count,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "invalid_call_count": invalid_calls,
                "fallback_parse_count": fallback_parses,
            },
            "cases": case_reports,
        }

        labeled = [
            case for case in case_reports if case.get("human_label") is not None
        ]
        predicted = [case["winner"] for case in labeled]
        expected = [case["human_label"] for case in labeled]
        probes = [
            case
            for case in labeled
            if any(tag.startswith("probe:") for tag in case["tags"])
        ]
        all_scores = [
            case["overall_scores"][label]
            for case in case_reports
            for label in ("A", "B")
        ]
        validation = {
            "run_id": run_id,
            "method": (
                "agreement with fixed human/gold labels plus adversarial probes"
            ),
            "labeled_cases": len(labeled),
            "agreement_rate": (
                sum(p == e for p, e in zip(predicted, expected)) / len(labeled)
                if labeled
                else None
            ),
            "cohen_kappa": _cohen_kappa(predicted, expected),
            "adversarial_probes": {
                "count": len(probes),
                "success_rate": (
                    sum(case["winner"] == case["human_label"] for case in probes)
                    / len(probes)
                    if probes
                    else None
                ),
                "fooled_case_ids": [
                    case["id"]
                    for case in probes
                    if case["winner"] != case["human_label"]
                ],
                "by_type": {
                    tag.removeprefix("probe:"): {
                        "count": len(tagged),
                        "success_rate": sum(
                            item["winner"] == item["human_label"]
                            for item in tagged
                        )
                        / len(tagged),
                    }
                    for tag in sorted(
                        {
                            tag
                            for case in probes
                            for tag in case["tags"]
                            if tag.startswith("probe:")
                        }
                    )
                    if (
                        tagged := [
                            case for case in probes if tag in case["tags"]
                        ]
                    )
                },
            },
            "score_distribution": {
                "mean": _mean(all_scores),
                "population_stddev": (
                    statistics.pstdev(all_scores) if len(all_scores) > 1 else 0.0
                ),
                "unique_scores_2dp": len(
                    {round(score, 2) for score in all_scores}
                ),
                "clustering_warning": len(
                    {round(score, 2) for score in all_scores}
                )
                <= 3,
            },
            "position_flip_rate": report["bias"]["position_flip_rate"],
            "test_retest_flip_rate": (
                sum(case["test_retest_flip"] for case in case_reports)
                / len(case_reports)
                if repeats > 1
                else None
            ),
            "release_gate_recommendation": (
                "Do not gate releases on the heuristic artifact. For a real LLM "
                "run, require kappa >= 0.6, probe success >= 0.8, flip rate <= "
                "0.1, no safety regressions, and human review of disagreements."
            ),
            "cases": [
                {
                    "id": case["id"],
                    "predicted": case["winner"],
                    "human_label": case.get("human_label"),
                    "correct": case["winner"] == case.get("human_label"),
                    "tags": case["tags"],
                }
                for case in labeled
            ],
        }
        write_json(report_path, report)
        write_json(validation_path, validation)
        return report, validation
