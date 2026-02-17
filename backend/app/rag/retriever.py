"""
Retriever in-memory com sentence-transformers.

Estratégia:
- Carrega chunks dos PDFs uma vez (singleton)
- Gera embeddings com all-MiniLM-L6-v2
- Busca por similaridade coseno
- Retorna top_k chunks mais relevantes

Ideal para poucos documentos (~12KB). Sem dependência de pgvector.
"""

import numpy as np
from sentence_transformers import SentenceTransformer

from app.rag.loader import load_and_chunk


# Singleton — inicializado no primeiro uso
_retriever_instance: "RAGRetriever | None" = None


class RAGRetriever:
    """Retriever in-memory com embeddings e similaridade coseno."""

    def __init__(self):
        print("🔄 Inicializando RAG Retriever...")

        # Carrega e chunkeia os PDFs
        self.chunks = load_and_chunk()

        if not self.chunks:
            print("⚠️ Nenhum chunk disponível para RAG")
            self.embeddings = np.array([])
            self.model = None
            return

        # Modelo de embeddings (leve, ~80MB)
        print("🧠 Carregando modelo de embeddings (all-MiniLM-L6-v2)...")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        # Gera embeddings de todos os chunks
        texts = [c["text"] for c in self.chunks]
        self.embeddings = self.model.encode(texts, normalize_embeddings=True)

        print(f"✅ RAG Retriever pronto: {len(self.chunks)} chunks, embeddings shape={self.embeddings.shape}")

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """Busca os top_k chunks mais relevantes para a query."""
        if self.model is None or len(self.chunks) == 0:
            return []

        # Embedding da query
        query_embedding = self.model.encode([query], normalize_embeddings=True)

        # Similaridade coseno (embeddings já normalizados → dot product)
        similarities = np.dot(self.embeddings, query_embedding.T).flatten()

        # Top K índices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score > 0.15:  # threshold mínimo de relevância
                results.append({
                    "text": self.chunks[idx]["text"],
                    "source": self.chunks[idx]["source"],
                    "score": score,
                })

        return results


def get_retriever() -> RAGRetriever:
    """Retorna a instância singleton do retriever."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = RAGRetriever()
    return _retriever_instance


def search_documents(query: str, top_k: int = 3) -> list[str]:
    """
    Busca documentos relevantes e retorna lista de textos.
    Interface simplificada para uso nos nodes do agente.
    """
    retriever = get_retriever()
    results = retriever.search(query, top_k=top_k)

    if not results:
        return []

    formatted = []
    for r in results:
        formatted.append(f"[Fonte: {r['source']}]\n{r['text']}")

    return formatted
