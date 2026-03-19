from __future__ import annotations

from app.memory_store import InteractionEvent, MemoryStore


def test_memory_store_logs_and_promotes(tmp_path):
    store = MemoryStore(tmp_path / "memory")
    event = InteractionEvent(
        source="telegram",
        user_id=1,
        chat_id=2,
        user_text="hello",
        injected_text="Context:\n- sample\n\nUser:\nhello",
        retrieved_snippets=["sample"],
    )
    store.log_interaction(event)
    daily_files = list((tmp_path / "memory" / "daily").glob("*.md"))
    assert daily_files, "daily log file should be created"
    content = daily_files[0].read_text(encoding="utf-8")
    assert "User Message" in content
    assert "hello" in content

    target = store.promote_fact("important fact", "learnings.md")
    assert target.exists()
    assert "important fact" in target.read_text(encoding="utf-8")
