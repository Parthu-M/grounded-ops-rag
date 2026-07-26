from __future__ import annotations

from typing import Sequence

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.preprocessing import normalize


class HashingEmbedder:
    """Stateless, deterministic local embedding for reproducible evaluation.

    This is a lexical n-gram embedding, not a semantic foundation-model
    embedding. It is intentionally honest and key-free for the product demo.
    """

    def __init__(self, dimensions: int = 768) -> None:
        self.model_name = "local/hash-hybrid-ngram-v1"
        self.dimensions = dimensions
        word_dimensions = dimensions // 2
        char_dimensions = dimensions - word_dimensions
        self._word_vectorizer = HashingVectorizer(
            n_features=word_dimensions,
            alternate_sign=False,
            norm=None,
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b[a-zA-Z0-9][a-zA-Z0-9_-]+\b",
        )
        self._char_vectorizer = HashingVectorizer(
            n_features=char_dimensions,
            alternate_sign=False,
            norm=None,
            lowercase=True,
            analyzer="char_wb",
            ngram_range=(3, 5),
        )

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        word = self._word_vectorizer.transform(texts).astype("float32")
        char = self._char_vectorizer.transform(texts).astype("float32")
        # Give lexical and morphology-sensitive channels equal total weight.
        word = normalize(word, norm="l2")
        char = normalize(char, norm="l2")
        matrix = np.hstack((word.toarray(), char.toarray()))
        matrix = normalize(matrix, norm="l2").astype("float32")
        return matrix.tolist()
