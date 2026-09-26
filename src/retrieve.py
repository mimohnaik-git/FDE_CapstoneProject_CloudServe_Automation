"""Official-KB retrieval (A4).

Deterministic cosine similarity over section-level passages. The submitted
runtime selects TF-IDF explicitly. MiniLM remains available only when selected
explicitly and its optional dependency is installed; backend selection never
changes silently. The backend in use is always reported so metrics are not
mixed."""
from __future__ import annotations

import json
import importlib
import re
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion

from .schemas import Passage


class RetrievalError(RuntimeError):
    pass


def load_kb(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    articles = data["articles"] if isinstance(data, dict) else data
    if not articles:
        raise RetrievalError("knowledge base is empty")
    return articles


def chunk_articles(articles: list[dict]) -> list[dict]:
    """One passage per article section. Articles without sections become a
    single 'Body' passage."""
    chunks = []
    for a in articles:
        sections = a.get("sections") or _markdown_sections(
            a.get("content") or a.get("body", ""))
        plans = a.get("plans") or _plans_from_applies_to(a.get("applies_to", ""))
        for s in sections:
            text = (s.get("text") or "").strip()
            if not text:
                continue
            chunks.append({
                "doc_id": a["doc_id"], "title": a.get("title", ""),
                "section": s.get("heading", "Body"), "text": text,
                "plans": plans,
            })
    return chunks


def _markdown_sections(content: str) -> list[dict]:
    """Split the official Markdown articles on level-two headings.

    Keeping numbered resolution steps together avoids returning fragments that
    retrieve well but are unsafe or incomplete as an answer.
    """
    if not content or not content.strip():
        return []
    sections: list[dict] = []
    heading = "Body"
    body: list[str] = []
    for line in content.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            text = "\n".join(body).strip()
            if text:
                sections.append({"heading": heading, "text": text})
            heading, body = match.group(1).strip(), []
        elif not line.startswith("# ") and not line.lower().startswith("**applies to:**"):
            body.append(line)
    text = "\n".join(body).strip()
    if text:
        sections.append({"heading": heading, "text": text})
    return sections


def _plans_from_applies_to(value: str) -> list[str]:
    text = value.lower()
    if "all plan" in text:
        return []
    return [p for p in ("standard", "business", "enterprise") if p in text]


class _TfidfBackend:
    name = "tfidf"

    def fit(self, docs):
        self.vec = FeatureUnion([
            ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                     sublinear_tf=True)),
        ])
        m = self.vec.fit_transform(docs)
        return self._norm(np.asarray(getattr(m, "toarray")()))

    def encode(self, texts):
        m = self.vec.transform(texts)
        return self._norm(np.asarray(getattr(m, "toarray")()))

    @staticmethod
    def _norm(m):
        n = np.linalg.norm(m, axis=1, keepdims=True)
        n[n == 0] = 1.0
        return m / n


class _MiniLMBackend:
    def __init__(self, model_name):
        # Optional dependency: loaded only when the MiniLM backend is selected.
        module: Any = importlib.import_module("sentence_transformers")
        SentenceTransformer = module.SentenceTransformer
        self.name = model_name
        self.model = SentenceTransformer(model_name)

    def fit(self, docs):
        return self.encode(docs)

    def encode(self, texts):
        return np.asarray(self.model.encode(texts, normalize_embeddings=True,
                                            show_progress_bar=False))


class Retriever:
    def __init__(self, articles: list[dict], model_name: str,
                 allow_fallback: bool = True, backend: str | None = None):
        self.chunks = chunk_articles(articles)
        if not self.chunks:
            raise RetrievalError("no retrievable passages in KB")
        self.backend = self._make_backend(model_name, allow_fallback, backend)
        # Development-only selection showed that explicit title/heading weight
        # plus word+character evidence improves document retrieval. Repetition
        # is deterministic and keeps the backend simple and auditable.
        docs = [f"{c['title']}. {c['title']}. {c['section']}. {c['section']}. {c['text']}"
                for c in self.chunks]
        self.matrix = self.backend.fit(docs)

    @staticmethod
    def _make_backend(model_name, allow_fallback, forced):
        if forced == "tfidf":
            return _TfidfBackend()
        if forced in ("minilm", model_name):
            return _MiniLMBackend(model_name)
        raise RetrievalError(f"unsupported or unspecified retrieval backend: {forced!r}")

    @property
    def backend_name(self) -> str:
        return self.backend.name

    def search(self, query: str, k: int = 5,
               threshold: float | None = None) -> list[Passage]:
        if not query.strip():
            return []
        q = self.backend.encode([query])[0]
        scores = self.matrix @ q
        # Deterministic tie-break: score desc, then doc_id, then section.
        order = sorted(range(len(scores)),
                       key=lambda i: (-round(float(scores[i]), 6),
                                      self.chunks[i]["doc_id"], self.chunks[i]["section"]))
        out = []
        seen_docs = set()
        for i in order:
            if threshold is not None and float(scores[i]) < threshold:
                continue
            c = self.chunks[i]
            # Document-level top-k: one strong passage per document prevents
            # several sections of one article consuming the full ranking.
            if c["doc_id"] in seen_docs:
                continue
            seen_docs.add(c["doc_id"])
            out.append(Passage(doc_id=c["doc_id"], title=c["title"], section=c["section"],
                               text=c["text"], score=round(float(scores[i]), 4),
                               plans=list(c["plans"])))
            if len(out) == k:
                break
        return out

    def passages_for(self, doc_id: str, section_prefix: str | None = None) -> list[Passage]:
        return [Passage(doc_id=c["doc_id"], title=c["title"], section=c["section"],
                        text=c["text"], score=0.0, plans=list(c["plans"]))
                for c in self.chunks
                if c["doc_id"] == doc_id and
                (section_prefix is None or c["section"].lower().startswith(section_prefix.lower()))]

    def doc_ranking(self, passages: list[Passage]) -> list[str]:
        """Unique doc IDs in rank order (for Recall@k / MRR at document level)."""
        seen, out = set(), []
        for p in passages:
            if p.doc_id not in seen:
                seen.add(p.doc_id)
                out.append(p.doc_id)
        return out
