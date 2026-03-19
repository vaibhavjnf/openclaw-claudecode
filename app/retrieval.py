from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.memory_store import MemoryStore

TOKEN_RE = re.compile(r"[a-zA-Z0-9_]{2,}")


def tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text)]


def chunk_markdown(content: str, max_chars: int = 800) -> list[str]:
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for para in paragraphs:
        if size + len(para) > max_chars and current:
            chunks.append("\n\n".join(current))
            current, size = [], 0
        current.append(para)
        size += len(para)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


@dataclass
class SearchResult:
    path: str
    score: float
    snippet: str


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class RetrieverProvider(Protocol):
    def search(self, query: str, k: int = 5, scopes: list[str] | None = None) -> list[SearchResult]:
        ...


class LexicalRetriever:
    def __init__(self, memory_store: MemoryStore, index_path: Path):
        self.memory_store = memory_store
        self.index_path = index_path
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

    def _rebuild_index(self, scopes: list[str] | None = None) -> dict:
        docs: list[dict] = []
        files_meta: dict[str, float] = {}
        for path in self.memory_store.memory_files(scopes=scopes):
            try:
                raw = path.read_text(encoding="utf-8")
            except OSError:
                continue
            files_meta[str(path)] = path.stat().st_mtime
            for chunk in chunk_markdown(raw):
                tokens = tokenize(chunk)
                if not tokens:
                    continue
                tf: dict[str, int] = {}
                for t in tokens:
                    tf[t] = tf.get(t, 0) + 1
                docs.append(
                    {
                        "path": str(path),
                        "snippet": chunk[:1200],
                        "tf": tf,
                        "len": len(tokens),
                    }
                )
        index = {"files_meta": files_meta, "docs": docs}
        self.index_path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
        return index

    def _load_or_build(self, scopes: list[str] | None = None) -> dict:
        if not self.index_path.exists():
            return self._rebuild_index(scopes=scopes)
        try:
            index = json.loads(self.index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return self._rebuild_index(scopes=scopes)
        current_meta: dict[str, float] = {}
        for path in self.memory_store.memory_files(scopes=scopes):
            try:
                current_meta[str(path)] = path.stat().st_mtime
            except OSError:
                continue
        if index.get("files_meta") != current_meta:
            return self._rebuild_index(scopes=scopes)
        return index

    def search(self, query: str, k: int = 5, scopes: list[str] | None = None) -> list[SearchResult]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        index = self._load_or_build(scopes=scopes)
        docs: list[dict] = index.get("docs", [])
        if not docs:
            return []

        doc_count = len(docs)
        avg_len = sum(d.get("len", 0) for d in docs) / max(doc_count, 1)

        df: dict[str, int] = {}
        for d in docs:
            for token in d.get("tf", {}).keys():
                df[token] = df.get(token, 0) + 1

        results: list[SearchResult] = []
        k1 = 1.2
        b = 0.75
        for d in docs:
            score = 0.0
            doc_len = max(1, d.get("len", 1))
            tf_map: dict[str, int] = d.get("tf", {})
            for token in query_tokens:
                tf = tf_map.get(token, 0)
                if tf == 0:
                    continue
                token_df = df.get(token, 0)
                idf = math.log(1 + (doc_count - token_df + 0.5) / (token_df + 0.5))
                score += idf * ((tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / max(avg_len, 1))))
            if score > 0:
                results.append(
                    SearchResult(
                        path=d.get("path", ""),
                        score=score,
                        snippet=d.get("snippet", "")[:700],
                    )
                )
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:k]
