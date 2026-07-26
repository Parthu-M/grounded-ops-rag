from __future__ import annotations

import math
import re
import time
from pathlib import Path
from typing import Any

from ai_takehome.common import (
    citations,
    normalized_text,
    percentile,
    read_json_or_yaml,
    tokenize,
    utc_now,
    write_json,
)
from ai_takehome.rag.generation import NO_CONTEXT_ANSWER
from ai_takehome.rag.service import RAGEngine

_CITATION_TEXT_RE = re.compile(r"\s*\[c_[a-f0-9]{16}\]\s*")


def _token_f1(prediction: str, gold: str) -> float:
    predicted = tokenize(prediction)
    expected = tokenize(gold)
    if not predicted and not expected:
        return 1.0
    if not predicted or not expected:
        return 0.0
    predicted_counts = {token: predicted.count(token) for token in set(predicted)}
    expected_counts = {token: expected.count(token) for token in set(expected)}
    common = sum(
        min(count, expected_counts.get(token, 0))
        for token, count in predicted_counts.items()
    )
    precision = common / len(predicted)
    recall = common / len(expected)
    return (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )


def _ndcg(retrieved: list[str], relevant: set[str], k: int) -> float:
    dcg = sum(
        (1.0 / math.log2(rank + 2))
        for rank, chunk_id in enumerate(retrieved[:k])
        if chunk_id in relevant
    )
    ideal_hits = min(k, len(relevant))
    idcg = sum(1.0 / math.log2(rank + 2) for rank in range(ideal_hits))
    return dcg / idcg if idcg else 0.0


def _faithfulness(answer: str, contexts: list[dict[str, Any]]) -> float:
    if answer == NO_CONTEXT_ANSWER:
        return 1.0 if not contexts else 0.0
    context_by_id = {item["chunk_id"]: item["text"] for item in contexts}
    cited = citations(answer)
    if not cited or any(chunk_id not in context_by_id for chunk_id in cited):
        return 0.0
    claim = normalized_text(_CITATION_TEXT_RE.sub(" ", answer))
    supported_text = normalized_text(
        " ".join(context_by_id[chunk_id] for chunk_id in cited)
    )
    if claim and claim in supported_text:
        return 1.0
    return _token_f1(claim, supported_text)


def evaluate_rag(
    engine: RAGEngine,
    questions_path: Path,
    output_path: Path,
    *,
    k: int = 3,
    latency_repeats: int = 10,
) -> dict[str, Any]:
    suite = read_json_or_yaml(questions_path)
    questions = suite["questions"]
    all_chunks = engine.store.all_chunks()
    per_case: list[dict[str, Any]] = []
    latency_samples: list[float] = []

    for case in questions:
        anchors = [anchor.lower() for anchor in case.get("relevant_anchors", [])]
        relevant = {
            chunk.id
            for chunk in all_chunks
            if any(anchor in chunk.text.lower() for anchor in anchors)
        }
        response = engine.ask(
            case["question"],
            k=k,
            metadata_filter=case.get("metadata_filter"),
            request_id=f"eval-{case['id']}",
        )
        retrieved = [item["chunk_id"] for item in response["contexts"]]
        answerable = bool(anchors)
        if answerable:
            relevant_retrieved = [item for item in retrieved if item in relevant]
            recall = len(set(relevant_retrieved)) / max(1, len(relevant))
            hit = float(bool(relevant_retrieved))
            reciprocal_rank = next(
                (
                    1.0 / (rank + 1)
                    for rank, chunk_id in enumerate(retrieved)
                    if chunk_id in relevant
                ),
                0.0,
            )
            ndcg = _ndcg(retrieved, relevant, k)
            context_precision = len(relevant_retrieved) / max(
                1, len(retrieved)
            )
        else:
            recall = hit = reciprocal_rank = ndcg = context_precision = None
        clean_answer = _CITATION_TEXT_RE.sub(" ", response["answer"]).strip()
        expected = case["gold_answer"]
        abstained = response["answer"] == NO_CONTEXT_ANSWER
        if not answerable:
            exact_match = float(abstained)
            token_f1 = float(abstained)
            answer_relevance = float(abstained)
        else:
            exact_match = float(
                normalized_text(clean_answer) == normalized_text(expected)
            )
            token_f1 = _token_f1(clean_answer, expected)
            answer_relevance = token_f1
        per_case.append(
            {
                "id": case["id"],
                "question": case["question"],
                "answerable": answerable,
                "relevant_chunk_ids": sorted(relevant),
                "retrieved_chunk_ids": retrieved,
                "answer": response["answer"],
                "gold_answer": expected,
                "retrieval": {
                    f"recall@{k}": recall,
                    "hit_rate": hit,
                    "mrr": reciprocal_rank,
                    f"ndcg@{k}": ndcg,
                    "context_precision": context_precision,
                },
                "answer_metrics": {
                    "faithfulness": _faithfulness(
                        response["answer"], response["contexts"]
                    ),
                    "answer_relevance": answer_relevance,
                    "exact_match": exact_match,
                    "token_f1": token_f1,
                },
                "latency_ms": response["latency_ms"],
            }
        )

    # Retrieval-only benchmark excludes generation and logs; one warm-up first.
    for case in questions:
        engine.store.search(
            case["question"],
            k=k,
            metadata_filter=case.get("metadata_filter"),
            min_score=engine.settings.min_relevance_score,
        )
    for _ in range(latency_repeats):
        for case in questions:
            start = time.perf_counter()
            engine.store.search(
                case["question"],
                k=k,
                metadata_filter=case.get("metadata_filter"),
                min_score=engine.settings.min_relevance_score,
            )
            latency_samples.append((time.perf_counter() - start) * 1000)

    answerable_cases = [item for item in per_case if item["answerable"]]
    metric_keys = [
        f"recall@{k}",
        "hit_rate",
        "mrr",
        f"ndcg@{k}",
        "context_precision",
    ]
    retrieval_aggregate = {
        key: sum(item["retrieval"][key] for item in answerable_cases)
        / len(answerable_cases)
        for key in metric_keys
    }
    answer_keys = [
        "faithfulness",
        "answer_relevance",
        "exact_match",
        "token_f1",
    ]
    answer_aggregate = {
        key: sum(item["answer_metrics"][key] for item in per_case)
        / len(per_case)
        for key in answer_keys
    }
    no_answer = [item for item in per_case if not item["answerable"]]
    report = {
        "run": {
            "timestamp": utc_now(),
            "store": "chroma",
            "vector_count": engine.store.count(),
            "embedding_model": engine.embedder.model_name,
            "embedding_dimensionality": engine.embedder.dimensions,
            "generator": getattr(engine.generator, "model_name", "unknown"),
            "chunk_size_words": engine.settings.chunk_size_words,
            "chunk_overlap_words": engine.settings.chunk_overlap_words,
            "k": k,
            "min_relevance_score": engine.settings.min_relevance_score,
            "question_count": len(per_case),
            "answerable_question_count": len(answerable_cases),
            "latency_sample_count": len(latency_samples),
        },
        "retrieval": retrieval_aggregate,
        "answer": answer_aggregate,
        "no_answer_accuracy": (
            sum(
                item["answer_metrics"]["exact_match"] for item in no_answer
            )
            / len(no_answer)
            if no_answer
            else None
        ),
        "latency_ms": {
            "retrieval_p50": percentile(latency_samples, 0.50),
            "retrieval_p95": percentile(latency_samples, 0.95),
            "retrieval_min": min(latency_samples, default=0.0),
            "retrieval_max": max(latency_samples, default=0.0),
        },
        "cases": per_case,
    }
    write_json(output_path, report)
    return report

