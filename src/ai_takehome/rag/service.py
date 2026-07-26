from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from ai_takehome.common import append_jsonl, utc_now
from ai_takehome.config import Settings
from ai_takehome.rag.chunking import Chunker
from ai_takehome.rag.embeddings import HashingEmbedder
from ai_takehome.rag.generation import build_generator
from ai_takehome.rag.ingestion import IngestResult, Ingestor
from ai_takehome.rag.store import ChromaStore


class RAGEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.embedder = HashingEmbedder(settings.embedding_dim)
        if settings.embedding_model != self.embedder.model_name:
            raise ValueError(
                f"Unsupported EMBEDDING_MODEL {settings.embedding_model!r}; "
                f"this build implements {self.embedder.model_name!r}."
            )
        self.store = ChromaStore(
            settings.chroma_path,
            settings.collection_name,
            self.embedder,
        )
        self.ingestor = Ingestor(
            self.store,
            Chunker(
                settings.chunk_size_words,
                settings.chunk_overlap_words,
            ),
        )
        self.generator = build_generator(
            settings.generator_provider,
            settings.generator_model,
            self.embedder,
        )

    def ingest(self, path: Path) -> list[IngestResult]:
        return self.ingestor.ingest_path(path)

    def close(self) -> None:
        self.store.close()

    def ask(
        self,
        question: str,
        *,
        k: int | None = None,
        metadata_filter: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        request_id = request_id or str(uuid.uuid4())
        k = k or self.settings.retrieval_top_k
        started = time.perf_counter()
        retrieval_started = time.perf_counter()
        results = self.store.search(
            question,
            k=k,
            metadata_filter=metadata_filter,
            min_score=self.settings.min_relevance_score,
        )
        retrieval_ms = (time.perf_counter() - retrieval_started) * 1000
        generation_started = time.perf_counter()
        generated = self.generator.generate(question, results)
        generation_ms = (time.perf_counter() - generation_started) * 1000
        total_ms = (time.perf_counter() - started) * 1000
        payload = {
            "request_id": request_id,
            "answer": generated.answer,
            "citations": generated.used_chunk_ids,
            "contexts": [
                {
                    "chunk_id": result.chunk.id,
                    "score": round(result.score, 6),
                    "text": result.chunk.text,
                    "metadata": result.chunk.metadata,
                }
                for result in results
            ],
            "usage": {
                "input_tokens": generated.usage.input_tokens,
                "output_tokens": generated.usage.output_tokens,
                "total_tokens": generated.usage.total_tokens,
                "estimated": generated.usage.estimated,
            },
            "latency_ms": {
                "retrieval": round(retrieval_ms, 3),
                "generation": round(generation_ms, 3),
                "total": round(total_ms, 3),
            },
        }
        append_jsonl(
            self.settings.query_log_path,
            {
                "timestamp": utc_now(),
                "request_id": request_id,
                "question": question,
                "k": k,
                "metadata_filter": metadata_filter or {},
                "retrieved_chunk_count": len(results),
                "cited_chunk_count": len(generated.used_chunk_ids),
                "usage": payload["usage"],
                "latency_ms": payload["latency_ms"],
                "generator": getattr(
                    self.generator, "model_name", "unknown"
                ),
                "embedding_model": self.embedder.model_name,
                "embedding_dim": self.embedder.dimensions,
            },
        )
        return payload
