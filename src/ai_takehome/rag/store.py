from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

from ai_takehome.common import tokenize
from ai_takehome.rag.embeddings import HashingEmbedder
from ai_takehome.rag.models import Chunk, SearchResult

_QUERY_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "long",
    "many",
    "nimbus",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "with",
}


class ChromaStore:
    def __init__(
        self,
        path: Path,
        collection_name: str,
        embedder: HashingEmbedder,
    ) -> None:
        path.mkdir(parents=True, exist_ok=True)
        self.embedder = embedder
        self.client = chromadb.PersistentClient(path=str(path))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine",
                "embedding_model": embedder.model_name,
                "embedding_dim": embedder.dimensions,
            },
        )
        metadata = self.collection.metadata or {}
        existing_dim = metadata.get("embedding_dim")
        if existing_dim and int(existing_dim) != embedder.dimensions:
            raise ValueError(
                f"Collection dimension {existing_dim} does not match "
                f"configured {embedder.dimensions}; use a new collection."
            )
        existing_model = metadata.get("embedding_model")
        if (
            existing_model
            and existing_model != embedder.model_name
            and self.collection.count() > 0
        ):
            raise ValueError(
                f"Collection model {existing_model} does not match configured "
                f"{embedder.model_name}; use a new collection or re-create it."
            )

    def source_chunk_count(self, source_id: str) -> int:
        existing = self.collection.get(
            where={"source_id": source_id}, include=[]
        )
        return len(existing.get("ids") or [])

    def delete_source(self, source_id: str) -> int:
        existing = self.collection.get(
            where={"source_id": source_id}, include=[]
        )
        ids = existing.get("ids") or []
        if ids:
            self.collection.delete(ids=ids)
        return len(ids)

    def upsert(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        self.collection.upsert(
            ids=[chunk.id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            metadatas=[chunk.metadata for chunk in chunks],
            embeddings=self.embedder.embed([chunk.text for chunk in chunks]),
        )

    @staticmethod
    def _where(metadata_filter: dict[str, Any] | None) -> dict | None:
        if not metadata_filter:
            return None
        terms = [{key: value} for key, value in metadata_filter.items()]
        return terms[0] if len(terms) == 1 else {"$and": terms}

    def search(
        self,
        query: str,
        *,
        k: int,
        metadata_filter: dict[str, Any] | None = None,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        count = self.collection.count()
        if count == 0 or k <= 0:
            return []
        kwargs: dict[str, Any] = {
            "query_embeddings": self.embedder.embed([query]),
            # Retrieve a broader ANN candidate set, then apply a cheap lexical
            # gate. This suppresses hash-collision false positives without
            # question-specific rules and still returns at most top-k.
            "n_results": min(max(k * 4, k), count),
            "include": ["documents", "metadatas", "distances"],
        }
        where = self._where(metadata_filter)
        if where:
            kwargs["where"] = where
        result = self.collection.query(**kwargs)
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        ranked_candidates: list[SearchResult] = []
        meaningful_query = {
            token
            for token in tokenize(query)
            if token not in _QUERY_STOPWORDS and len(token) >= 3
        }
        for chunk_id, document, metadata, distance in zip(
            ids, documents, metadatas, distances
        ):
            score = max(-1.0, min(1.0, 1.0 - float(distance)))
            lexical_overlap = meaningful_query & set(tokenize(document))
            if score >= min_score and lexical_overlap:
                coverage = len(lexical_overlap) / max(1, len(meaningful_query))
                hybrid_score = 0.65 * score + 0.35 * coverage
                ranked_candidates.append(
                    SearchResult(
                        chunk=Chunk(
                            id=chunk_id,
                            text=document,
                            metadata=metadata or {},
                        ),
                        score=hybrid_score,
                    )
                )
        ranked_candidates.sort(key=lambda item: item.score, reverse=True)
        return ranked_candidates[:k]

    def all_chunks(self) -> list[Chunk]:
        result = self.collection.get(include=["documents", "metadatas"])
        return [
            Chunk(id=chunk_id, text=document, metadata=metadata or {})
            for chunk_id, document, metadata in zip(
                result.get("ids", []),
                result.get("documents", []),
                result.get("metadatas", []),
            )
        ]

    def count(self) -> int:
        return self.collection.count()

    def close(self) -> None:
        close = getattr(self.client, "close", None)
        if callable(close):
            close()
