import numpy as np


def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    embedding = np.asarray(embedding, dtype=np.float32)

    norm = np.linalg.norm(embedding)

    if norm == 0:
        raise ValueError("zero embedding cannot be normalized")

    return embedding / norm


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = normalize_embedding(a)
    b = normalize_embedding(b)

    return float(np.dot(a, b))


def is_match(
    live_embedding: np.ndarray,
    stored_embedding: np.ndarray,
    threshold: float
) -> tuple[bool, float]:
    similarity = cosine_similarity(live_embedding, stored_embedding)
    return similarity >= threshold, similarity