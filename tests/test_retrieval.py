from __future__ import annotations

from app.memory_store import MemoryStore
from app.retrieval import LexicalRetriever


def test_lexical_retriever_finds_relevant_content(tmp_path):
    store = MemoryStore(tmp_path / "memory")
    note = store.long_term_dir / "knowledge.md"
    note.write_text("# Knowledge\n\nClaude Code runs in tmux.\n", encoding="utf-8")

    retriever = LexicalRetriever(store, store.index_dir / "index.json")
    results = retriever.search("tmux", k=3)
    assert results
    assert any("tmux" in r.snippet.lower() for r in results)
