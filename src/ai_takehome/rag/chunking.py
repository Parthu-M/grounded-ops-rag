from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from ai_takehome.rag.models import Chunk

_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class Chunker:
    size_words: int = 120
    overlap_words: int = 25

    def split(
        self,
        text: str,
        *,
        source_id: str,
        source: str,
        content_sha256: str,
        doc_type: str,
        topic: str,
    ) -> list[Chunk]:
        clean = _SPACE_RE.sub(" ", text).strip()
        words = clean.split()
        if not words:
            return []
        step = self.size_words - self.overlap_words
        chunks: list[Chunk] = []
        for index, start in enumerate(range(0, len(words), step)):
            window = words[start : start + self.size_words]
            if not window:
                break
            chunk_text = " ".join(window)
            identity = (
                f"{source_id}:{content_sha256}:{self.size_words}:"
                f"{self.overlap_words}:{index}:{chunk_text}"
            )
            chunk_id = "c_" + hashlib.sha256(
                identity.encode("utf-8")
            ).hexdigest()[:16]
            chunks.append(
                Chunk(
                    id=chunk_id,
                    text=chunk_text,
                    metadata={
                        "source_id": source_id,
                        "source": source,
                        "content_sha256": content_sha256,
                        "doc_type": doc_type,
                        "topic": topic,
                        "chunk_index": index,
                        "start_word": start,
                        "end_word": start + len(window),
                    },
                )
            )
            if start + self.size_words >= len(words):
                break
        return chunks

