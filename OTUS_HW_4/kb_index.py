from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any


def _read_text_with_fallback(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "cp1251", "windows-1251", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            return line.lstrip("#").strip() or fallback
        # Markdown link title in first line: [Title](url)
        m = re.match(r"^\[(.+?)\]\(.+?\)$", line)
        if m:
            return m.group(1).strip()
        return line[:160]
    return fallback


def _split_into_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    overlap = max(0, min(overlap, chunk_size - 1)) if chunk_size > 1 else 0

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
        current = ""

    for paragraph in paragraphs:
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            flush()

        if len(paragraph) <= chunk_size:
            current = paragraph
            continue

        step = max(1, chunk_size - overlap)
        start = 0
        while start < len(paragraph):
            part = paragraph[start : start + chunk_size].strip()
            if part:
                chunks.append(part)
            start += step

    if current:
        flush()

    return chunks


def _make_snippet(chunk_text: str, query: str, max_len: int = 280) -> str:
    text = re.sub(r"\s+", " ", chunk_text).strip()
    if len(text) <= max_len:
        return text

    tokens = [t for t in re.findall(r"\w+", query.lower()) if len(t) >= 3]
    lower = text.lower()
    pos = -1
    for token in tokens:
        pos = lower.find(token)
        if pos != -1:
            break

    if pos == -1:
        return text[: max_len - 1].rstrip() + "..."

    half = max_len // 2
    start = max(0, pos - half)
    end = min(len(text), start + max_len)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet.rstrip() + "..."
    return snippet


@dataclass(slots=True)
class DocumentRecord:
    doc_id: str
    path: str
    title: str
    size_bytes: int
    content: str


@dataclass(slots=True)
class ChunkRecord:
    chunk_id: str
    doc_id: str
    chunk_index: int
    text: str


class KnowledgeBaseIndex:
    def __init__(
        self,
        kb_dir: str | Path,
        *,
        chunk_size: int = 1400,
        chunk_overlap: int = 250,
        max_features: int = 25000,
        svd_components: int = 256,
    ) -> None:
        self.kb_dir = Path(kb_dir)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_features = max_features
        self.svd_components = svd_components

        self._lock = RLock()
        self._documents: dict[str, DocumentRecord] = {}
        self._chunks: list[ChunkRecord] = []

        self._vectorizer: Any = None
        self._svd: Any = None
        self._normalizer: Any = None
        self._search_matrix: Any = None
        self._cosine_similarity: Any = None
        self._model_kind: str = "uninitialized"
        self._built_at: str | None = None
        self._build_duration_ms: int | None = None

    def _ensure_deps(self) -> None:
        try:
            import numpy  # noqa: F401
            from sklearn.decomposition import TruncatedSVD  # noqa: F401
            from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: F401
            from sklearn.metrics.pairwise import cosine_similarity  # noqa: F401
            from sklearn.preprocessing import Normalizer  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "Missing dependencies for semantic search. Install: pip install -r requirements.txt"
            ) from exc

    def _load_documents(self) -> list[DocumentRecord]:
        if not self.kb_dir.exists():
            raise FileNotFoundError(f"Knowledge base folder not found: {self.kb_dir}")

        docs: list[DocumentRecord] = []
        for path in sorted(self.kb_dir.glob("*.md")):
            text = _clean_text(_read_text_with_fallback(path))
            if not text:
                continue
            docs.append(
                DocumentRecord(
                    doc_id=path.name,
                    path=str(path.resolve()),
                    title=_extract_title(text, path.stem),
                    size_bytes=path.stat().st_size,
                    content=text,
                )
            )
        return docs

    def build(self) -> dict[str, Any]:
        self._ensure_deps()

        from time import strftime

        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        from sklearn.preprocessing import Normalizer

        started = time.perf_counter()

        docs = self._load_documents()
        if not docs:
            raise RuntimeError(f"No .md files found in {self.kb_dir}")

        chunks: list[ChunkRecord] = []
        for doc in docs:
            doc_chunks = _split_into_chunks(
                doc.content, chunk_size=self.chunk_size, overlap=self.chunk_overlap
            )
            if not doc_chunks:
                doc_chunks = [doc.content]
            for i, chunk_text in enumerate(doc_chunks):
                chunks.append(
                    ChunkRecord(
                        chunk_id=f"{doc.doc_id}::chunk-{i}",
                        doc_id=doc.doc_id,
                        chunk_index=i,
                        text=chunk_text,
                    )
                )

        corpus = [chunk.text for chunk in chunks]
        vectorizer = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            ngram_range=(1, 2),
            max_features=self.max_features,
            token_pattern=r"(?u)\b\w\w+\b",
        )
        tfidf = vectorizer.fit_transform(corpus)

        use_svd = tfidf.shape[0] >= 3 and tfidf.shape[1] >= 3
        svd = None
        normalizer = None
        search_matrix = tfidf
        model_kind = "tfidf"

        if use_svd:
            max_possible_components = min(tfidf.shape[0] - 1, tfidf.shape[1] - 1)
            n_components = min(self.svd_components, max_possible_components)
            if n_components >= 2:
                svd = TruncatedSVD(n_components=n_components, random_state=42)
                normalizer = Normalizer(copy=False)
                search_matrix = normalizer.fit_transform(svd.fit_transform(tfidf))
                model_kind = f"lsa_tfidf_svd_{n_components}"

        build_duration_ms = int((time.perf_counter() - started) * 1000)

        with self._lock:
            self._documents = {doc.doc_id: doc for doc in docs}
            self._chunks = chunks
            self._vectorizer = vectorizer
            self._svd = svd
            self._normalizer = normalizer
            self._search_matrix = search_matrix
            self._cosine_similarity = cosine_similarity
            self._model_kind = model_kind
            self._built_at = strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self._build_duration_ms = build_duration_ms

        return self.stats()

    def _require_built(self) -> None:
        if self._vectorizer is None or self._search_matrix is None or not self._chunks:
            raise RuntimeError("Index is not built yet. Call build() first.")

    def stats(self) -> dict[str, Any]:
        with self._lock:
            docs = list(self._documents.values())
            total_chars = sum(len(doc.content) for doc in docs)
            return {
                "kb_dir": str(self.kb_dir.resolve()),
                "documents_count": len(docs),
                "chunks_count": len(self._chunks),
                "total_chars": total_chars,
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "max_features": self.max_features,
                "svd_components_requested": self.svd_components,
                "model_kind": self._model_kind,
                "built_at": self._built_at,
                "build_duration_ms": self._build_duration_ms,
            }

    def list_documents(
        self, *, limit: int = 20, offset: int = 0, name_contains: str | None = None
    ) -> dict[str, Any]:
        with self._lock:
            docs = list(self._documents.values())

        if name_contains:
            needle = name_contains.lower()
            docs = [
                d
                for d in docs
                if needle in d.doc_id.lower() or needle in d.title.lower()
            ]

        total = len(docs)
        offset = max(0, offset)
        limit = max(1, min(limit, 200))
        page = docs[offset : offset + limit]

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "items": [
                {
                    "doc_id": d.doc_id,
                    "title": d.title,
                    "path": d.path,
                    "size_bytes": d.size_bytes,
                    "content_length": len(d.content),
                }
                for d in page
            ],
        }

    def get_document(
        self, doc_id: str, *, include_content: bool = True, max_chars: int = 4000
    ) -> dict[str, Any]:
        with self._lock:
            doc = self._documents.get(doc_id)

        if doc is None:
            return {"found": False, "doc_id": doc_id}

        max_chars = max(200, min(max_chars, 200_000))
        content = doc.content if include_content else None
        truncated = False
        if include_content and content is not None and len(content) > max_chars:
            content = content[:max_chars]
            truncated = True

        return {
            "found": True,
            "document": {
                "doc_id": doc.doc_id,
                "title": doc.title,
                "path": doc.path,
                "size_bytes": doc.size_bytes,
                "content_length": len(doc.content),
                "content": content,
                "content_truncated": truncated,
            },
        }

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        min_score: float = 0.08,
        deduplicate_docs: bool = True,
    ) -> dict[str, Any]:
        query = (query or "").strip()
        if not query:
            return {
                "query": query,
                "top_k": top_k,
                "min_score": min_score,
                "results": [],
                "error": "Query is empty",
            }

        with self._lock:
            self._require_built()
            vectorizer = self._vectorizer
            svd = self._svd
            normalizer = self._normalizer
            search_matrix = self._search_matrix
            cosine_similarity = self._cosine_similarity
            chunks = list(self._chunks)
            docs = dict(self._documents)
            model_kind = self._model_kind

        query_vec = vectorizer.transform([query])
        if svd is not None and normalizer is not None:
            query_vec = normalizer.transform(svd.transform(query_vec))

        scores = cosine_similarity(query_vec, search_matrix).ravel()

        top_k = max(1, min(top_k, 50))
        min_score = max(-1.0, min(float(min_score), 1.0))

        ranked_idx = scores.argsort()[::-1]
        seen_docs: set[str] = set()
        results: list[dict[str, Any]] = []

        for idx in ranked_idx:
            score = float(scores[idx])
            if score < min_score:
                break

            chunk = chunks[int(idx)]
            if deduplicate_docs and chunk.doc_id in seen_docs:
                continue
            seen_docs.add(chunk.doc_id)

            doc = docs[chunk.doc_id]
            results.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "doc_id": doc.doc_id,
                    "title": doc.title,
                    "chunk_index": chunk.chunk_index,
                    "score": round(score, 6),
                    "snippet": _make_snippet(chunk.text, query),
                    "path": doc.path,
                }
            )
            if len(results) >= top_k:
                break

        return {
            "query": query,
            "top_k": top_k,
            "min_score": min_score,
            "deduplicate_docs": deduplicate_docs,
            "model_kind": model_kind,
            "results_count": len(results),
            "results": results,
        }
