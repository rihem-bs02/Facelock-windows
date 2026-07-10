import numpy as np

from facelook.matcher import normalize_embedding


def average_embeddings(embeddings: list[np.ndarray]) -> np.ndarray:
    """
    Average multiple embeddings into one stable embedding.

    This improves reliability compared to saving one frame only.
    """

    if not embeddings:
        raise ValueError("at least one embedding is required")

    vectors = [np.asarray(e, dtype=np.float32) for e in embeddings]

    stacked = np.stack(vectors, axis=0)
    average = np.mean(stacked, axis=0)

    return normalize_embedding(average)