import numpy as np
from typing import Dict, Any, List
import re

class VectorIndex:
    def __init__(self, chunks: List[Dict[str, Any]]):
        self.chunks = chunks
        self.vectors = []
        self._build_index()

    def _get_simple_embedding(self, text: str) -> np.ndarray:
        """Generates normalized TF-IDF / char-n-gram frequency vector fallback for fast embeddings."""
        words = re.findall(r'\w+', text.lower())
        vec = np.zeros(256)
        for w in words:
            idx = sum(ord(c) for c in w) % 256
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def _build_index(self):
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            texts = [c["text"] for c in self.chunks]
            embeddings = model.encode(texts)
            for i, c in enumerate(self.chunks):
                c["embedding"] = embeddings[i].tolist()
                self.vectors.append(embeddings[i])
        except Exception:
            # Fallback to TF-IDF vectorizer if sentence-transformers model is not cached
            for c in self.chunks:
                vec = self._get_simple_embedding(c["text"])
                c["embedding"] = vec.tolist()
                self.vectors.append(vec)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Searches vector index and returns closest chunks with similarity score."""
        if not self.chunks or not self.vectors:
            return []
            
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            query_vec = model.encode([query])[0]
        except Exception:
            query_vec = self._get_simple_embedding(query)

        query_norm = np.linalg.norm(query_vec)
        if query_norm > 0:
            query_vec = query_vec / query_norm

        results = []
        for i, doc_vec in enumerate(self.vectors):
            doc_norm = np.linalg.norm(doc_vec)
            sim = float(np.dot(query_vec, doc_vec)) if doc_norm > 0 else 0.0
            
            chunk_copy = dict(self.chunks[i])
            chunk_copy["score"] = round(float(sim), 4)
            results.append(chunk_copy)

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
