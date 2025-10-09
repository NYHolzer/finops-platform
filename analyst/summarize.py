from __future__ import annotations
from typing import List
from re
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

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
    """

    text = (text or "").strip()
    if not text:
        return []
    
    sents=[s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]
    if len(sents) <= k:
        return sents
    
    vec = TfidfVectorizer(stop_words="english", max_features=5000)
    X = vec.fit_transform(sents) # shape: {num_sents, num_terms}
    scores = np.asarray(X.sum(axis=1)).ravel() # sum weights per sentence

    # pick top-k by score, but preserve original order in the output
    top_idx = np.argsort(-scores)[:k]
    mask = [False] * len(sents)
    for i in top_idx:
        mask[int(i)] = True
    return [s for s, keep in zip(sents, mask) if keep]