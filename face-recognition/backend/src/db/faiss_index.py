"""
src/db/faiss_index.py

Wraps a FAISS index for fast nearest-neighbor search over face embeddings.

Design choice: IndexFlatIP (Flat = exact search, IP = inner product).
Since our embeddings are L2-normalized (normed_embedding), inner product IS
cosine similarity. At a few-hundred-to-low-thousands scale, exact flat search
is fast enough (sub-millisecond) that we don't need an approximate index (IVF/HNSW).
If you ever scale to 100k+ people, we'd revisit this -- not a concern at your scale.

Postgres (embeddings table) stays the source of truth for rebuilding this index
from scratch if needed. This file is an in-memory index that gets saved/loaded
from disk between runs.
"""

import os
import numpy as np
import faiss

EMBEDDING_DIM = 512  # buffalo_l / ArcFace output size


class FaceIndex:
    def __init__(self, index_path: str = "models/pretrained/face_index.faiss"):
        self.index_path = index_path
        self.dim = EMBEDDING_DIM

        if os.path.exists(index_path):
            self.index = faiss.read_index(index_path)
        else:
            self.index = faiss.IndexIDMap(faiss.IndexFlatIP(self.dim))

    def add(self, faiss_id: int, normed_embedding: np.ndarray):
        """
        faiss_id: a unique integer ID (use the same id as embeddings.faiss_index_id
                  in Postgres, so the two stay in sync).
        normed_embedding: 512-d L2-normalized vector (face.normed_embedding).
        """
        vec = normed_embedding.astype(np.float32).reshape(1, -1)
        ids = np.array([faiss_id], dtype=np.int64)
        self.index.add_with_ids(vec, ids)

    def search(self, query_embedding: np.ndarray, top_k: int = 1):
        """
        Returns list of (faiss_id, similarity_score) tuples, best match first.
        similarity_score is cosine similarity (-1 to 1, higher = more similar)
        since our vectors are normalized and we use inner product.
        """
        vec = query_embedding.astype(np.float32).reshape(1, -1)
        scores, ids = self.index.search(vec, top_k)
        results = [(int(ids[0][i]), float(scores[0][i])) for i in range(top_k) if ids[0][i] != -1]
        return results

    def remove(self, faiss_id: int):
        """Remove a single embedding by its faiss_id (e.g. when deleting a person)."""
        self.index.remove_ids(np.array([faiss_id], dtype=np.int64))

    def save(self):
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path)

    def total_count(self) -> int:
        return self.index.ntotal

    def rebuild_from_postgres(self, session):
        """
        Wipes and rebuilds the FAISS index entirely from the embeddings table
        in Postgres. Use this for disaster recovery, or after bulk edits.
        """
        from db.postgres import Embedding  # local import to avoid circular import

        self.index = faiss.IndexIDMap(faiss.IndexFlatIP(self.dim))
        rows = session.query(Embedding).all()
        for row in rows:
            vec = np.array(row.embedding, dtype=np.float32).reshape(1, -1)
            ids = np.array([row.faiss_index_id], dtype=np.int64)
            self.index.add_with_ids(vec, ids)
        self.save()
        print(f"Rebuilt FAISS index from Postgres: {len(rows)} embeddings loaded.")