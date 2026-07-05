import os
import numpy as np
from sentence_transformers import SentenceTransformer

# Loaded once at startup — free, runs locally, no API cost.
_model = SentenceTransformer("all-MiniLM-L6-v2")

SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", 0.80))


def embed(text: str) -> list[float]:
    vec = _model.encode(text, normalize_embeddings=True)
    return vec.tolist()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b))  # already normalized, so dot product == cosine similarity


def find_most_similar(embedding: list[float], past_failures: list[dict]) -> tuple[dict | None, float]:
    """
    past_failures: list of {"id": ..., "embedding": [...], ...} pulled from Supabase
    Returns (best_match_or_None, similarity_score)
    """
    best_match = None
    best_score = 0.0
    for failure in past_failures:
        score = cosine_similarity(embedding, failure["embedding"])
        if score > best_score:
            best_score = score
            best_match = failure

    if best_match and best_score >= SIMILARITY_THRESHOLD:
        return best_match, best_score
    return None, best_score
