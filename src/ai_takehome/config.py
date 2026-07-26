from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    project_root: Path
    chroma_path: Path
    query_log_path: Path
    collection_name: str
    chunk_size_words: int
    chunk_overlap_words: int
    embedding_model: str
    embedding_dim: int
    retrieval_top_k: int
    min_relevance_score: float
    generator_provider: str
    generator_model: str
    judge_provider: str
    judge_model: str
    judge_family: str
    generator_a_family: str
    generator_b_family: str
    allow_same_family_judge: bool
    judge_repeats: int
    judge_log_path: Path

    @classmethod
    def from_env(cls) -> "Settings":
        package_root = Path(__file__).resolve().parents[2]
        root = Path(
            os.getenv(
                "GROUNDED_OPS_HOME",
                os.getenv("AI_TAKEHOME_HOME", package_root),
            )
        ).resolve()

        def rooted(name: str, default: str) -> Path:
            candidate = Path(os.getenv(name, default))
            return candidate if candidate.is_absolute() else root / candidate

        settings = cls(
            project_root=root,
            chroma_path=rooted("CHROMA_PATH", ".runtime/chroma"),
            query_log_path=rooted(
                "QUERY_LOG_PATH", ".runtime/logs/rag_queries.jsonl"
            ),
            collection_name=os.getenv("CHROMA_COLLECTION", "knowledge_base"),
            chunk_size_words=int(os.getenv("CHUNK_SIZE_WORDS", "120")),
            chunk_overlap_words=int(os.getenv("CHUNK_OVERLAP_WORDS", "25")),
            embedding_model=os.getenv(
                "EMBEDDING_MODEL", "local/hash-hybrid-ngram-v1"
            ),
            embedding_dim=int(os.getenv("EMBEDDING_DIM", "768")),
            retrieval_top_k=int(os.getenv("RETRIEVAL_TOP_K", "3")),
            min_relevance_score=float(
                os.getenv("MIN_RELEVANCE_SCORE", "0.12")
            ),
            generator_provider=os.getenv(
                "GENERATOR_PROVIDER", "extractive"
            ).lower(),
            generator_model=os.getenv("GENERATOR_MODEL", "gpt-5-mini"),
            judge_provider=os.getenv("JUDGE_PROVIDER", "heuristic").lower(),
            judge_model=os.getenv("JUDGE_MODEL", "gpt-5.1"),
            judge_family=os.getenv("JUDGE_FAMILY", "openai"),
            generator_a_family=os.getenv(
                "GENERATOR_A_FAMILY", "demo-rules-a"
            ),
            generator_b_family=os.getenv(
                "GENERATOR_B_FAMILY", "demo-rules-b"
            ),
            allow_same_family_judge=_bool_env(
                "ALLOW_SAME_FAMILY_JUDGE", False
            ),
            judge_repeats=max(1, int(os.getenv("JUDGE_REPEATS", "1"))),
            judge_log_path=rooted(
                "JUDGE_LOG_PATH", ".runtime/logs/judge_calls.jsonl"
            ),
        )
        if settings.chunk_size_words < 20:
            raise ValueError("CHUNK_SIZE_WORDS must be at least 20")
        if not 0 <= settings.chunk_overlap_words < settings.chunk_size_words:
            raise ValueError(
                "CHUNK_OVERLAP_WORDS must be >= 0 and smaller than chunk size"
            )
        if settings.embedding_dim < 64:
            raise ValueError("EMBEDDING_DIM must be at least 64")
        return settings
