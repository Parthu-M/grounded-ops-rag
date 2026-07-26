from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

from ai_takehome.common import utc_now, write_json


def build_cost_comparison() -> dict[str, Any]:
    """Model direct infra costs; excludes embeddings, LLM, labor, and egress."""

    # Quoted assumptions captured in README with primary-source links.
    ebs_per_gb_month = 0.08
    pinecone_storage_per_gb_month = 0.33
    pinecone_ru_per_million = 16.0
    pinecone_standard_minimum = 50.0
    p1_monthly_per_pod = 85.72
    queries_per_month = 100_000
    bytes_per_record = 768 * 4 + 1024  # vector plus assumed metadata

    rows: list[dict[str, Any]] = []
    # Instance values are explicit scenario assumptions, not autosizing claims.
    self_host = {
        100_000: ("t4g.small-equivalent", 12.26, 10),
        1_000_000: ("t4g.large-equivalent", 49.06, 30),
        10_000_000: ("r7g.2xlarge-equivalent", 312.73, 100),
    }
    for vector_count, (instance, compute, ebs_gb) in self_host.items():
        namespace_gb = vector_count * bytes_per_record / 1_000_000_000
        # Pinecone query billing: 1 RU/GB namespace, min 0.25 RU/query.
        ru_per_query = max(0.25, namespace_gb)
        pinecone_usage = (
            namespace_gb * pinecone_storage_per_gb_month
            + queries_per_month
            * ru_per_query
            * pinecone_ru_per_million
            / 1_000_000
        )
        serverless = max(pinecone_standard_minimum, pinecone_usage)
        # Conservative historical p1 capacity rule: 1M records per pod.
        pod_count = max(1, math.ceil(vector_count / 1_000_000))
        rows.append(
            {
                "vectors": vector_count,
                "estimated_record_data_gb": round(namespace_gb, 3),
                "queries_per_month": queries_per_month,
                "chroma_instance_assumption": instance,
                "chroma_compute_usd_month": round(compute, 2),
                "chroma_ebs_gb": ebs_gb,
                "chroma_ebs_usd_month": round(
                    ebs_gb * ebs_per_gb_month, 2
                ),
                "chroma_total_usd_month": round(
                    compute + ebs_gb * ebs_per_gb_month, 2
                ),
                "pinecone_serverless_usage_before_minimum_usd": round(
                    pinecone_usage, 2
                ),
                "pinecone_serverless_standard_usd_month": round(
                    serverless, 2
                ),
                "pinecone_legacy_p1_pods": pod_count,
                "pinecone_legacy_p1_usd_month": round(
                    pod_count * p1_monthly_per_pod, 2
                ),
            }
        )
    return {
        "generated_at": utc_now(),
        "currency": "USD",
        "scope": "Direct vector-store infrastructure only",
        "assumptions": {
            "embedding_dimensions": 768,
            "float_bytes": 4,
            "metadata_bytes_per_record": 1024,
            "queries_per_month": queries_per_month,
            "aws_ebs_gp3_usd_per_gb_month": ebs_per_gb_month,
            "pinecone_storage_usd_per_gb_month": (
                pinecone_storage_per_gb_month
            ),
            "pinecone_query_usd_per_million_ru": pinecone_ru_per_million,
            "pinecone_standard_monthly_minimum_usd": (
                pinecone_standard_minimum
            ),
            "pinecone_legacy_p1_estimated_monthly_per_pod_usd": (
                p1_monthly_per_pod
            ),
            "excluded": [
                "embedding generation",
                "LLM generation",
                "network egress",
                "backups",
                "observability",
                "engineering/on-call labor",
                "taxes",
            ],
        },
        "rows": rows,
    }


def write_cost_artifacts(json_path: Path, csv_path: Path) -> dict[str, Any]:
    report = build_cost_comparison()
    write_json(json_path, report)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(report["rows"][0]))
        writer.writeheader()
        writer.writerows(report["rows"])
    return report

