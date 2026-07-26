from __future__ import annotations

import json
from pathlib import Path

from ai_takehome.judge.clients import HeuristicJudge, JudgeResponse
from ai_takehome.judge.parser import parse_verdict
from ai_takehome.judge.pipeline import JudgePipeline


def _raw_verdict() -> str:
    return json.dumps(
        {
            "criteria": [
                {
                    "name": "correctness",
                    "left_score": 5,
                    "right_score": 1,
                    "rationale": "Left matches the reference.",
                    "evidence": "The expected value is 42.",
                }
            ],
            "left_overall": 5,
            "right_overall": 1,
            "winner": "LEFT",
            "rationale": "Left is correct.",
        }
    )


def test_parser_recovers_fenced_and_trailing_comma_json() -> None:
    fenced = parse_verdict(f"preface\n```json\n{_raw_verdict()}\n```")
    assert fenced.valid
    assert fenced.parse_strategy == "markdown_fence"
    trailing = _raw_verdict()[:-1] + ",}"
    repaired = parse_verdict(trailing)
    assert repaired.valid
    assert "repair" in repaired.parse_strategy
    invalid = parse_verdict("not json")
    assert not invalid.valid
    assert invalid.parse_error


def test_dual_order_pipeline_writes_auditable_calls(tmp_path: Path) -> None:
    suite = {
        "config_a": "new",
        "config_b": "old",
        "cases": [
            {
                "id": "case-1",
                "input": "The answer in context is 42.",
                "system_prompt": "Answer with the number.",
                "expected_output": "42",
                "candidate_a": "42",
                "candidate_b": "41",
                "human_label": "A",
                "criteria": ["correctness", "instruction_following"],
                "tags": ["factual"],
            }
        ],
    }
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(json.dumps(suite), encoding="utf-8")
    log_path = tmp_path / "calls.jsonl"
    pipeline = JudgePipeline(
        HeuristicJudge(),
        log_path=log_path,
        judge_family="deterministic-rules",
        generator_a_family="new-family",
        generator_b_family="old-family",
    )
    report, validation = pipeline.run(
        suite_path,
        tmp_path / "report.json",
        tmp_path / "validation.json",
        repeats=1,
    )
    assert report["audit"]["judge_calls"] == 2
    assert report["comparison"]["declared_winner"] == "A"
    assert report["bias"]["position_flip_rate"] == 0
    assert validation["agreement_rate"] == 1
    records = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == 2
    assert {record["order"] for record in records} == {"AB", "BA"}
    assert all(record["prompt"] and record["raw_response"] for record in records)


def test_self_enhancement_guard_rejects_same_family(tmp_path: Path) -> None:
    try:
        JudgePipeline(
            HeuristicJudge(),
            log_path=tmp_path / "calls.jsonl",
            judge_family="same",
            generator_a_family="same",
            generator_b_family="other",
        )
    except ValueError as exc:
        assert "Self-enhancement guard" in str(exc)
    else:
        raise AssertionError("Expected same-family judge guard to fail")


def test_malformed_response_retry_is_fully_logged(tmp_path: Path) -> None:
    class AlternatingJudge:
        family = "independent"
        model = "test"
        provider = "test"

        def __init__(self) -> None:
            self.calls = 0

        def judge(self, prompt, payload):
            self.calls += 1
            raw = "malformed" if self.calls % 2 else _raw_verdict()
            return JudgeResponse(
                raw=raw,
                input_tokens=10,
                output_tokens=5,
                model=self.model,
                provider=self.provider,
                usage_estimated=False,
            )

    suite = {
        "cases": [
            {
                "id": "retry-case",
                "input": "The reference value is 42.",
                "system_prompt": "Answer.",
                "expected_output": "42",
                "candidate_a": "42",
                "candidate_b": "41",
                "human_label": "A",
                "criteria": ["correctness"],
            }
        ]
    }
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(json.dumps(suite), encoding="utf-8")
    log_path = tmp_path / "retry.jsonl"
    pipeline = JudgePipeline(
        AlternatingJudge(),
        log_path=log_path,
        judge_family="independent",
        generator_a_family="a",
        generator_b_family="b",
    )
    report, _ = pipeline.run(
        suite_path,
        tmp_path / "report.json",
        tmp_path / "validation.json",
    )
    records = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]
    assert report["audit"]["judge_calls"] == 4
    assert report["audit"]["invalid_call_count"] == 2
    assert len(records) == 4
    assert sum(record["is_repair_retry"] for record in records) == 2
