"""
ChromaDB vector store wrapper.

Decision: one Chroma collection per repository (not one giant shared
collection) so that:
  - Semantic search for repo A never leaks results from repo B
  - We can drop/re-ingest a single repo's collection independently
  - Collection name doubles as a natural repo_id namespace

We use the PersistentClient so embeddings survive process restarts —
important for a "real" deployment where repo ingestion is expensive
and shouldn't be redone on every API server restart.
"""
from __future__ import annotations

import re

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.embeddings import DocumentChunk, get_embedding_model

logger = get_logger(__name__)
settings = get_settings()

_chroma_client: chromadb.ClientAPI | None = None


def get_chroma_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


def collection_name_for_repo(repo_id: str) -> str:
    """Chroma collection names must be alphanumeric/underscore/hyphen, 3-63 chars."""
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", repo_id)
    return f"{settings.CHROMA_COLLECTION_PREFIX}{safe}"[:63]


class RepoVectorStore:
    """Wraps a single repo's Chroma collection for ingestion + semantic search."""

    def __init__(self, repo_id: str):
        self.repo_id = repo_id
        self.collection_name = collection_name_for_repo(repo_id)
        self._client = get_chroma_client()
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"repo_id": repo_id},
        )

    def reset(self) -> None:
        """Drops and recreates the collection — used when re-ingesting a repo."""
        try:
            self._client.delete_collection(self.collection_name)
        except Exception:
            pass
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"repo_id": self.repo_id},
        )

    def add_chunks(self, chunks: list[DocumentChunk], batch_size: int = 64) -> int:
        if not chunks:
            return 0
        embedder = get_embedding_model()
        total = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c.text for c in batch]
            vectors = embedder.embed_documents(texts)
            self._collection.add(
                ids=[c.chunk_id for c in batch],
                embeddings=vectors,
                documents=texts,
                metadatas=[c.metadata for c in batch],
            )
            total += len(batch)
        logger.info("chunks_indexed", repo_id=self.repo_id, count=total)
        return total

    def query(
        self,
        query_text: str,
        top_k: int | None = None,
        source_type: str | None = None,
    ) -> list[dict]:
        """Semantic search within this repo's collection.

        Returns a list of {text, metadata, distance, similarity} dicts,
        sorted by relevance (highest similarity first).
        """
        embedder = get_embedding_model()
        query_vector = embedder.embed_query(query_text)

        where = {"source_type": source_type} if source_type else None

        results = self._collection.query(
            query_embeddings=[query_vector],
            n_results=top_k or settings.RAG_TOP_K,
            where=where,
        )

        if not results["ids"] or not results["ids"][0]:
            return []

        out = []
        for doc, meta, dist in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        ):
            # Chroma's default distance is squared L2 on normalized embeddings;
            # convert to an intuitive 0-1 similarity score for the frontend/agents.
            similarity = max(0.0, 1.0 - (dist / 2.0))
            out.append({"text": doc, "metadata": meta, "similarity": similarity})
        return out

    def count(self) -> int:
        return self._collection.count()
