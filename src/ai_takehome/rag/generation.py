from __future__ import annotations

import re
from typing import Protocol

import numpy as np

from ai_takehome.common import estimate_tokens, tokenize
from ai_takehome.rag.embeddings import HashingEmbedder
from ai_takehome.rag.models import (
    GenerationResult,
    SearchResult,
    TokenUsage,
)

NO_CONTEXT_ANSWER = (
    "I don't have enough relevant context in the indexed documents to answer."
)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
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


def _stem(token: str) -> str:
    for suffix in ("ments", "ment", "ingly", "edly", "ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    return token


class Generator(Protocol):
    def generate(
        self, question: str, contexts: list[SearchResult]
    ) -> GenerationResult: ...


class ExtractiveGenerator:
    """Key-free generator that quotes the best supported corpus sentence."""

    model_name = "local/extractive-v1"

    def __init__(self, embedder: HashingEmbedder) -> None:
        self.embedder = embedder

    def generate(
        self, question: str, contexts: list[SearchResult]
    ) -> GenerationResult:
        if not contexts:
            return GenerationResult(
                answer=NO_CONTEXT_ANSWER,
                used_chunk_ids=[],
                usage=TokenUsage(
                    input_tokens=estimate_tokens(question),
                    output_tokens=estimate_tokens(NO_CONTEXT_ANSWER),
                    total_tokens=estimate_tokens(question)
                    + estimate_tokens(NO_CONTEXT_ANSWER),
                    estimated=True,
                ),
            )
        query_tokens = set(tokenize(question)) - _STOPWORDS
        query_terms = {_stem(token) for token in query_tokens}
        wants_price = bool(query_tokens & {"price", "cost", "much", "overage"})
        raw_candidates: list[tuple[str, str, int, float]] = []
        for rank, result in enumerate(contexts):
            for sentence in _SENTENCE_RE.split(result.chunk.text):
                clean = sentence.strip(" \n#*-")
                if len(clean) < 12:
                    continue
                raw_candidates.append(
                    (clean, result.chunk.id, rank, result.score)
                )
        if not raw_candidates:
            return GenerationResult(
                answer=NO_CONTEXT_ANSWER, used_chunk_ids=[]
            )
        query_vector = np.asarray(self.embedder.embed([question])[0])
        sentence_vectors = self.embedder.embed(
            [item[0] for item in raw_candidates]
        )
        candidates: list[tuple[float, str, str]] = []
        for (clean, chunk_id, rank, chunk_score), vector in zip(
            raw_candidates, sentence_vectors
        ):
            sentence_tokens = set(tokenize(clean)) - _STOPWORDS
            sentence_terms = {_stem(token) for token in sentence_tokens}
            overlap = len(query_terms & sentence_terms)
            coverage = overlap / max(1, len(query_terms))
            density = overlap / max(1, len(sentence_terms))
            vector_score = float(query_vector @ np.asarray(vector))
            numeric_price_signal = (
                1.0
                if wants_price
                and (
                    any(char.isdigit() for char in clean)
                    or any(
                        token in sentence_tokens
                        for token in {"cent", "cents", "dollar", "dollars"}
                    )
                )
                else 0.0
            )
            score = (
                0.50 * vector_score
                + 0.25 * coverage
                + 0.10 * density
                + 0.10 * chunk_score
                + 0.05 * numeric_price_signal
                - rank * 0.001
            )
            candidates.append((score, clean, chunk_id))
        _, sentence, chunk_id = max(candidates, key=lambda item: item[0])
        answer = f"{sentence} [{chunk_id}]"
        input_text = question + "\n" + "\n".join(
            result.chunk.text for result in contexts
        )
        input_tokens = estimate_tokens(input_text)
        output_tokens = estimate_tokens(answer)
        return GenerationResult(
            answer=answer,
            used_chunk_ids=[chunk_id],
            usage=TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                estimated=True,
            ),
        )


class OpenAIGenerator:
    def __init__(self, model: str) -> None:
        from openai import OpenAI

        self.model_name = model
        self.client = OpenAI()

    def generate(
        self, question: str, contexts: list[SearchResult]
    ) -> GenerationResult:
        if not contexts:
            return GenerationResult(
                answer=NO_CONTEXT_ANSWER, used_chunk_ids=[]
            )
        context_text = "\n\n".join(
            f"[{result.chunk.id}] {result.chunk.text}" for result in contexts
        )
        prompt = (
            "Answer only from CONTEXT. Cite every factual claim with the exact "
            "chunk ID in square brackets. If context is insufficient, reply "
            f'exactly: "{NO_CONTEXT_ANSWER}"\n\n'
            f"QUESTION:\n{question}\n\nCONTEXT:\n{context_text}"
        )
        response = self.client.responses.create(
            model=self.model_name,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise grounded QA assistant. Never use "
                        "unstated outside knowledge."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        answer = response.output_text.strip()
        valid_ids = {result.chunk.id for result in contexts}
        used_ids = [
            chunk_id
            for chunk_id in re.findall(r"\[(c_[a-f0-9]{16})\]", answer)
            if chunk_id in valid_ids
        ]
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        return GenerationResult(
            answer=answer,
            used_chunk_ids=list(dict.fromkeys(used_ids)),
            usage=TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                estimated=False,
            ),
        )


def build_generator(
    provider: str, model: str, embedder: HashingEmbedder
) -> Generator:
    if provider == "extractive":
        return ExtractiveGenerator(embedder)
    if provider == "openai":
        return OpenAIGenerator(model)
    raise ValueError(f"Unsupported GENERATOR_PROVIDER: {provider}")
