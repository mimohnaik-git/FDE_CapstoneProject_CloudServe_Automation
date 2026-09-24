"""Deterministic semantic retrieval over authoritative CloudServe documents."""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np

from src.config import settings


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS_PATH = PROJECT_ROOT / "data" / "raw" / "documentation.json"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_MIN_RELEVANCE_SCORE = 0.30


class DocumentCorpusError(ValueError):
    """Raised when the configured authoritative corpus is unusable."""


@dataclass(frozen=True)
class ChunkingConfig:
    """A reproducible, section-aware chunking configuration."""

    name: str
    max_chars: int
    overlap_chars: int


CHUNKING_CONFIGS = {
    # Chosen on development data: Recall@3 0.888 versus 0.875 for strategy_b.
    "strategy_a": ChunkingConfig("strategy_a", max_chars=480, overlap_chars=60),
    "strategy_b": ChunkingConfig("strategy_b", max_chars=900, overlap_chars=100),
}


@dataclass(frozen=True)
class _IndexState:
    chunks: List[Dict[str, Any]]
    embeddings: np.ndarray
    build_time_ms: float


def load_authoritative_documents(path: Path | str = DEFAULT_CORPUS_PATH) -> List[Dict[str, Any]]:
    """Load and strictly validate the sole retrieval corpus."""

    corpus_path = Path(path).resolve()
    try:
        raw = json.loads(corpus_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DocumentCorpusError(f"Unable to load documentation corpus {corpus_path}: {exc}") from exc
    if isinstance(raw, list) and len(raw) == 1 and isinstance(raw[0], list):
        raw = raw[0]
    if not isinstance(raw, list) or not raw:
        raise DocumentCorpusError("Documentation corpus must be a non-empty JSON list")

    required = ("doc_id", "title", "category", "content")
    documents: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for position, value in enumerate(raw):
        if not isinstance(value, dict):
            raise DocumentCorpusError(f"Document at position {position} is not an object")
        missing = [field for field in required if not isinstance(value.get(field), str) or not value[field].strip()]
        if missing:
            raise DocumentCorpusError(f"Document at position {position} has invalid fields: {', '.join(missing)}")
        doc_id = value["doc_id"].strip()
        if doc_id in seen:
            raise DocumentCorpusError(f"Duplicate document ID: {doc_id}")
        seen.add(doc_id)
        documents.append(dict(value))
    return documents


def _markdown_sections(text: str) -> List[tuple[str, str]]:
    """Split Markdown at headings while retaining headings in passages."""

    sections: List[tuple[str, str]] = []
    heading = "Document"
    lines: List[str] = []
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if match:
            if any(item.strip() for item in lines):
                sections.append((heading, "\n".join(lines).strip()))
            heading = match.group(1).strip()
            lines = [line]
        else:
            lines.append(line)
    if any(item.strip() for item in lines):
        sections.append((heading, "\n".join(lines).strip()))
    return sections


def _word_windows(text: str, max_chars: int, overlap_chars: int) -> List[str]:
    if max_chars <= 0 or overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("Chunk sizes require max_chars > overlap_chars >= 0")
    words = text.split()
    chunks: List[str] = []
    start = 0
    while start < len(words):
        end = start
        length = 0
        while end < len(words):
            added = len(words[end]) + (1 if end > start else 0)
            if end > start and length + added > max_chars:
                break
            length += added
            end += 1
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        retained = 0
        next_start = end
        while next_start > start and retained < overlap_chars:
            next_start -= 1
            retained += len(words[next_start]) + 1
        start = max(start + 1, next_start)
    return chunks


def chunk_document(text: str, config: ChunkingConfig) -> List[Dict[str, Any]]:
    """Chunk one article without crossing its semantic Markdown sections."""

    chunks: List[Dict[str, Any]] = []
    for section_index, (heading, section_text) in enumerate(_markdown_sections(text)):
        for part_index, passage in enumerate(_word_windows(section_text, config.max_chars, config.overlap_chars)):
            chunks.append(
                {
                    "section": heading,
                    "section_index": section_index,
                    "part_index": part_index,
                    "chunk_content": passage,
                }
            )
    return chunks


class DocumentationRetrievalEngine:
    """Lazy exact-cosine retrieval over a small in-memory embedding matrix."""

    _model_cache: Dict[str, Any] = {}
    _model_lock = threading.Lock()
    _index_cache: Dict[str, _IndexState] = {}
    _index_cache_lock = threading.Lock()

    def __init__(
        self,
        embedding_model: Optional[Any] = None,
        corpus_path: Path | str = DEFAULT_CORPUS_PATH,
        model_name: Optional[str] = None,
        chunking_strategy: str = "strategy_a",
        min_relevance_score: float = DEFAULT_MIN_RELEVANCE_SCORE,
    ):
        if chunking_strategy not in CHUNKING_CONFIGS:
            raise ValueError(f"Unknown chunking strategy: {chunking_strategy}")
        if not -1.0 <= min_relevance_score <= 1.0:
            raise ValueError("min_relevance_score must be between -1 and 1")
        configured_model = model_name or settings.EMBEDDING_MODEL or DEFAULT_EMBEDDING_MODEL
        self.model_name = (
            DEFAULT_EMBEDDING_MODEL if configured_model == "all-MiniLM-L6-v2" else configured_model
        )
        self.corpus_path = Path(corpus_path).resolve()
        self.embedding_model = embedding_model
        self._injected_embedding_model = embedding_model is not None
        self.chunking_config = CHUNKING_CONFIGS[chunking_strategy]
        self.min_relevance_score = float(min_relevance_score)
        self.documentation_cache: Dict[str, Dict[str, Any]] = {}
        self.last_error: Optional[str] = None
        self.index_build_time_ms: Optional[float] = None
        self._state: Optional[_IndexState] = None
        self._initialized = False
        self._initialize_lock = threading.Lock()

    def chunk_documentation_strategy_a(self, text: str, max_chars: int = 480, overlap: int = 60) -> List[str]:
        return [item["chunk_content"] for item in chunk_document(text, ChunkingConfig("strategy_a", max_chars, overlap))]

    def chunk_documentation_strategy_b(self, text: str, max_chars: int = 900, overlap: int = 100) -> List[str]:
        return [item["chunk_content"] for item in chunk_document(text, ChunkingConfig("strategy_b", max_chars, overlap))]

    @staticmethod
    def _encode(model: Any, texts: Sequence[str]) -> np.ndarray:
        try:
            values = model.encode(
                list(texts),
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
        except TypeError:
            values = model.encode(list(texts))
        array = np.asarray(values, dtype=np.float32)
        if array.ndim == 1:
            array = array.reshape(1, -1)
        norms = np.linalg.norm(array, axis=1, keepdims=True)
        return array / np.where(norms == 0, 1.0, norms)

    def _get_model(self) -> Any:
        if self.embedding_model is not None:
            return self.embedding_model
        with self._model_lock:
            if self.model_name not in self._model_cache:
                from sentence_transformers import SentenceTransformer

                self._model_cache[self.model_name] = SentenceTransformer(self.model_name)
            self.embedding_model = self._model_cache[self.model_name]
        return self.embedding_model

    def _source_path(self) -> str:
        try:
            return self.corpus_path.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            return str(self.corpus_path)

    def _build_chunks(self, documents: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        chunks: List[Dict[str, Any]] = []
        for document in documents:
            for item in chunk_document(str(document["content"]), self.chunking_config):
                digest = hashlib.sha256(item["chunk_content"].encode("utf-8")).hexdigest()[:12]
                chunk_id = (
                    f"{document['doc_id']}-{self.chunking_config.name}-"
                    f"{item['section_index']:02d}-{item['part_index']:02d}-{digest}"
                )
                chunks.append(
                    {
                        **item,
                        "chunk_id": chunk_id,
                        "document_id": str(document["doc_id"]),
                        "title": str(document["title"]),
                        "category": str(document["category"]),
                        "applies_to": str(document.get("applies_to", "")),
                    }
                )
        return chunks

    def _index_key(self, documents: Sequence[Mapping[str, Any]]) -> str:
        material = json.dumps(
            {
                "documents": documents,
                "model": self.model_name,
                "chunking": self.chunking_config.__dict__,
            },
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    def initialize_index(self, documents: Optional[List[Dict[str, Any]]] = None) -> None:
        """Explicitly build or reuse the process-local semantic index."""

        started = time.perf_counter()
        docs = documents if documents is not None else load_authoritative_documents(self.corpus_path)
        ids = [doc.get("doc_id") for doc in docs if isinstance(doc, dict)]
        if len(ids) != len(docs) or len(ids) != len(set(ids)):
            raise DocumentCorpusError("Caller-provided documents contain missing or duplicate IDs")
        for doc in docs:
            for field in ("doc_id", "title", "category", "content"):
                if not isinstance(doc.get(field), str) or not doc[field].strip():
                    raise DocumentCorpusError(f"Document {doc.get('doc_id', '<unknown>')} has invalid {field}")
        chunks = self._build_chunks(docs)
        if not chunks:
            raise DocumentCorpusError("Documentation corpus produced no indexable chunks")

        key = self._index_key(docs)
        state = None if self._injected_embedding_model else self._index_cache.get(key)
        if state is None:
            embeddings = self._encode(self._get_model(), [chunk["chunk_content"] for chunk in chunks])
            state = _IndexState(chunks=chunks, embeddings=embeddings, build_time_ms=(time.perf_counter() - started) * 1000.0)
            if not self._injected_embedding_model:
                with self._index_cache_lock:
                    self._index_cache.setdefault(key, state)
                    state = self._index_cache[key]
        self.documentation_cache = {str(doc["doc_id"]): dict(doc) for doc in docs}
        self._state = state
        self.index_build_time_ms = state.build_time_ms
        self.last_error = None
        self._initialized = True

    def _ensure_initialized(self) -> bool:
        if self._initialized:
            return self._state is not None
        with self._initialize_lock:
            if self._initialized:
                return self._state is not None
            try:
                self.initialize_index()
            except Exception as exc:
                self.last_error = type(exc).__name__
                self._state = None
                self._initialized = True
                return False
        return True

    def _generation_support_passages(
        self,
        document_id: str,
        primary_chunk_id: str,
        *,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return same-document Resolution chunks for grounded generation only."""

        if self._state is None or (limit is not None and limit <= 0):
            return []

        support: List[Dict[str, Any]] = []

        for chunk in self._state.chunks:
            if chunk.get("document_id") != document_id:
                continue

            if chunk.get("chunk_id") == primary_chunk_id:
                continue

            if str(chunk.get("section") or "").strip().lower() != "resolution":
                continue

            metadata = {
                "source_path": self._source_path(),
                "title": chunk["title"],
                "category": chunk["category"],
                "applies_to": chunk["applies_to"],
                "section": chunk["section"],
            }

            support.append(
                {
                    "document_id": document_id,
                    "chunk_id": chunk["chunk_id"],
                    "passage": chunk["chunk_content"],
                    "section": chunk["section"],
                    "title": chunk["title"],
                    "source": "authoritative_documentation",
                    "source_metadata": metadata,
                }
            )

            if limit is not None and len(support) >= limit:
                break

        return support

    def query_authoritative_knowledge(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Return distinct ranked document passages above the score floor."""

        if not isinstance(query, str) or not query.strip() or top_k <= 0:
            return []
        if not self._ensure_initialized():
            return []
        try:
            query_embedding = self._encode(self._get_model(), [query.strip()])[0]
            scores = self._state.embeddings @ query_embedding
            order = np.argsort(-scores, kind="stable")
            results: List[Dict[str, Any]] = []
            seen_documents: set[str] = set()
            for index in order:
                chunk = self._state.chunks[int(index)]
                document_id = chunk["document_id"]
                score = float(scores[int(index)])
                if score < self.min_relevance_score or document_id in seen_documents:
                    continue
                seen_documents.add(document_id)
                source_metadata = {
                    "source_path": self._source_path(),
                    "title": chunk["title"],
                    "category": chunk["category"],
                    "applies_to": chunk["applies_to"],
                    "section": chunk["section"],
                }
                results.append(
                    {
                        "document_id": document_id,
                        "doc_id": document_id,
                        "chunk_id": chunk["chunk_id"],
                        "passage": chunk["chunk_content"],
                        "chunk_content": chunk["chunk_content"],
                        "rank": len(results) + 1,
                        "similarity_score": score,
                        "relevance_score": score,
                        "title": chunk["title"],
                        "category": chunk["category"],
                        "section": chunk["section"],
                        "source": "authoritative_documentation",
                        "source_path": source_metadata["source_path"],
                        "source_metadata": source_metadata,
                        "supporting_passages": self._generation_support_passages(
                            document_id,
                            chunk["chunk_id"],
                        ),
                    }
                )
                if len(results) == top_k:
                    break
            self.last_error = None
            return results
        except Exception as exc:
            self.last_error = type(exc).__name__
            return []
