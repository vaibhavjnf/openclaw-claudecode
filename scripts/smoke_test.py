from __future__ import annotations

import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.memory_store import InteractionEvent, MemoryStore
from app.retrieval import LexicalRetriever


def run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "memory"
        store = MemoryStore(root)
        store.log_interaction(
            InteractionEvent(
                source="smoke",
                user_id=1,
                chat_id=1,
                user_text="check memory",
                injected_text="Context:\n- none\n\nUser:\ncheck memory",
                retrieved_snippets=[],
            )
        )
        store.promote_fact("smoke fact", "learnings.md")
        retriever = LexicalRetriever(store, root / "index" / "lexical_index.json")
        hits = retriever.search("smoke", k=3)
        if not hits:
            raise RuntimeError("retrieval smoke test failed: no results")
    print("Smoke test passed")


if __name__ == "__main__":
    run()
