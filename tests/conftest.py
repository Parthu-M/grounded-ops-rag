from __future__ import annotations

from pathlib import Path

import pytest

from ai_takehome.config import Settings


@pytest.fixture
def settings_factory(tmp_path: Path):
    def build(**overrides) -> Settings:
        values = {
            "project_root": tmp_path,
            "chroma_path": tmp_path / "chroma",
            "query_log_path": tmp_path / "logs" / "queries.jsonl",
            "collection_name": "test_collection",
            "chunk_size_words": 40,
            "chunk_overlap_words": 8,
            "embedding_model": "local/hash-hybrid-ngram-v1",
            "embedding_dim": 256,
            "retrieval_top_k": 3,
            "min_relevance_score": 0.08,
            "generator_provider": "extractive",
            "generator_model": "unused",
            "judge_provider": "heuristic",
            "judge_model": "heuristic-ci-v1",
            "judge_family": "deterministic-rules",
            "generator_a_family": "generator-a",
            "generator_b_family": "generator-b",
            "allow_same_family_judge": False,
            "judge_repeats": 1,
            "judge_log_path": tmp_path / "logs" / "judge.jsonl",
        }
        values.update(overrides)
        return Settings(**values)

    return build

