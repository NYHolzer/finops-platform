from __future__ import annotations

import re
from typing import List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# TfidfVectorizer converts text into numerical importance scores

# We use regex to split the text into sentences which then make each setences its own document for scoring.
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def top_sentences_tfidf(text: str, k: int = 3) -> List[str]:
    """
    Very simpl extractive summarizer:
    - split into sentences
    - TF-IDF on sentences (as docs)
    - score = sum of tf-idf weights per sentence
    - return top-k sentences in original order

    Robustness: if removing English stopwords empties the vocabulary,
    we retry without stopword removal.
    """

    text = (text or "").strip()
    if not text:
        return []

    sentences = [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]
    if len(sentences) <= k:
        return sentences

    def _score_with_vectorizer(vec: TfidfVectorizer) -> np.ndarray:
        X = vec.fit_transform(sentences)
        return np.asarray(X.sum(axis=1)).ravel()

    # TF-IDF rewards words that are frequent in one sentence but rare overall
    # First pass: standard English stopwords
    vec = TfidfVectorizer(stop_words="english", max_features=5000)
    try:
        scores = _score_with_vectorizer(vec)
    except ValueError as e:
        # Common when sentences are mostly numerals/short words (e.g., "One. Two.")
        # Retry with no stopword removal.
        if "empty vocabulary" not in str(e):
            raise
        vec = TfidfVectorizer(stop_words=None, max_features=5000)
        scores = _score_with_vectorizer(vec)

    # Indices of top-k highest scores
    top_idx = np.argsort(-scores)[:k]
    keep = set(int(i) for i in top_idx)

    # Preserve original order for readability
    return [s for i, s in enumerate(sentences) if i in keep]
