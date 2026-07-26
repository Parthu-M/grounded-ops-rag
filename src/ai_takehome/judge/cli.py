from __future__ import annotations

import argparse
import json

from ai_takehome.config import Settings
from ai_takehome.judge.clients import build_judge
from ai_takehome.judge.pipeline import JudgePipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bias-aware pairwise LLM-as-judge pipeline"
    )
    parser.add_argument("--suite", required=True, type=str)
    parser.add_argument("--report", required=True, type=str)
    parser.add_argument("--validation", required=True, type=str)
    parser.add_argument("--repeats", type=int, default=None)
    args = parser.parse_args()

    settings = Settings.from_env()
    client = build_judge(
        settings.judge_provider,
        settings.judge_model,
        settings.judge_family,
    )
    # Use the actual client family for the deterministic baseline and the
    # configured family for external LLMs.
    judge_family = getattr(client, "family", settings.judge_family)
    pipeline = JudgePipeline(
        client,
        log_path=settings.judge_log_path,
        judge_family=judge_family,
        generator_a_family=settings.generator_a_family,
        generator_b_family=settings.generator_b_family,
        allow_same_family=settings.allow_same_family_judge,
    )
    report, validation = pipeline.run(
        settings.project_root / args.suite,
        settings.project_root / args.report,
        settings.project_root / args.validation,
        repeats=args.repeats or settings.judge_repeats,
    )
    print(
        json.dumps(
            {
                "comparison": report["comparison"],
                "bias": report["bias"],
                "validation": {
                    "agreement_rate": validation["agreement_rate"],
                    "cohen_kappa": validation["cohen_kappa"],
                    "adversarial_probes": validation["adversarial_probes"],
                },
                "audit": report["audit"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

