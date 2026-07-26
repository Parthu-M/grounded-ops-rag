from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from ai_takehome.rag.chunking import Chunker
from ai_takehome.rag.loaders import infer_topic, load_document
from ai_takehome.rag.store import ChromaStore

SUPPORTED_SUFFIXES = {".md", ".markdown", ".html", ".htm", ".pdf"}


def source_id_for(path: Path) -> str:
    source_key = str(path.resolve()).lower().replace("\\", "/")
    return "s_" + hashlib.sha256(source_key.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class IngestResult:
    source: str
    source_id: str
    content_sha256: str
    chunks_written: int


class Ingestor:
    def __init__(self, store: ChromaStore, chunker: Chunker) -> None:
        self.store = store
        self.chunker = chunker

    def ingest_file(self, path: Path, *, base: Path | None = None) -> IngestResult:
        path = path.resolve()
        text, doc_type = load_document(path)
        if not text.strip():
            raise ValueError(
                f"No extractable text was found in {path.name!r}. "
                "Scanned PDFs require OCR before ingestion."
            )
        content_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        try:
            source = path.relative_to((base or path.parent).resolve()).as_posix()
        except ValueError:
            source = path.as_posix()
        source_id = source_id_for(path)
        chunks = self.chunker.split(
            text,
            source_id=source_id,
            source=source,
            content_sha256=content_sha,
            doc_type=doc_type,
            topic=infer_topic(path, text),
        )
        # Delete-before-upsert removes obsolete chunks when content or chunking
        # configuration changed; an identical re-ingest retains the same count.
        self.store.delete_source(source_id)
        self.store.upsert(chunks)
        return IngestResult(
            source=source,
            source_id=source_id,
            content_sha256=content_sha,
            chunks_written=len(chunks),
        )

    def ingest_path(self, path: Path) -> list[IngestResult]:
        path = path.resolve()
        if path.is_file():
            return [self.ingest_file(path)]
        files = sorted(
            candidate
            for candidate in path.rglob("*")
            if candidate.is_file()
            and candidate.suffix.lower() in SUPPORTED_SUFFIXES
        )
        return [self.ingest_file(candidate, base=path) for candidate in files]
