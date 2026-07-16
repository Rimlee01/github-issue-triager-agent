"""
Chunking + embedding generation for the RAG pipeline.

Decision: we use LangChain's RecursiveCharacterTextSplitter with
language-aware separators for code files (splits on class/def boundaries
before falling back to lines) rather than naive fixed-size chunking.
This keeps related code together in a chunk instead of slicing a function
in half, which materially improves retrieval relevance for "find me the
file handling X" queries.

Embeddings use a local sentence-transformers model (all-MiniLM-L6-v2)
rather than an API-based embedding model:
  - Zero marginal cost / no network dependency for embedding hundreds of files
  - Fast enough for synchronous ingestion of a repo in seconds, not minutes
  - 384-dim vectors keep ChromaDB index size small
"""
from __future__ import annotations

from dataclasses import dataclass

from langchain.text_splitter import RecursiveCharacterTextSplitter, Language
from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import IngestedFile

logger = get_logger(__name__)
settings = get_settings()

_EXT_TO_LANGUAGE: dict[str, Language] = {
    ".py": Language.PYTHON,
    ".js": Language.JS,
    ".jsx": Language.JS,
    ".ts": Language.TS,
    ".tsx": Language.TS,
    ".go": Language.GO,
    ".java": Language.JAVA,
    ".rb": Language.RUBY,
    ".rs": Language.RUST,
    ".cpp": Language.CPP,
    ".c": Language.CPP,
    ".h": Language.CPP,
    ".hpp": Language.CPP,
}


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    metadata: dict


_embedding_model: HuggingFaceEmbeddings | None = None


def get_embedding_model() -> HuggingFaceEmbeddings:
    """Lazily-loaded singleton — avoids reloading the model weights per request."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("loading_embedding_model", model=settings.EMBEDDING_MODEL)
        _embedding_model = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
    return _embedding_model


def _splitter_for_path(path: str) -> RecursiveCharacterTextSplitter:
    for ext, lang in _EXT_TO_LANGUAGE.items():
        if path.endswith(ext):
            return RecursiveCharacterTextSplitter.from_language(
                language=lang,
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
            )
    # Fallback: markdown/text/config files get generic recursive splitting
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )


def chunk_file(file: IngestedFile, repo_id: str) -> list[DocumentChunk]:
    splitter = _splitter_for_path(file.path)
    raw_chunks = splitter.split_text(file.content)
    return [
        DocumentChunk(
            chunk_id=f"{repo_id}:{file.path}:{i}",
            text=chunk_text,
            metadata={
                "repo_id": repo_id,
                "source_type": "code",
                "file_path": file.path,
                "chunk_index": i,
            },
        )
        for i, chunk_text in enumerate(raw_chunks)
    ]


def chunk_issue(repo_id: str, number: int, title: str, body: str, url: str, labels: list[str]) -> DocumentChunk:
    """Issues are typically short enough to embed as a single chunk (title + body)."""
    text = f"Issue #{number}: {title}\n\n{body}"[: settings.CHUNK_SIZE * 2]
    return DocumentChunk(
        chunk_id=f"{repo_id}:issue:{number}",
        text=text,
        metadata={
            "repo_id": repo_id,
            "source_type": "issue",
            "issue_number": number,
            "title": title,
            "url": url,
            "labels": ",".join(labels),
        },
    )


def chunk_readme(repo_id: str, content: str) -> list[DocumentChunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
    )
    raw_chunks = splitter.split_text(content)
    return [
        DocumentChunk(
            chunk_id=f"{repo_id}:readme:{i}",
            text=chunk_text,
            metadata={"repo_id": repo_id, "source_type": "readme", "chunk_index": i},
        )
        for i, chunk_text in enumerate(raw_chunks)
    ]
