from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

LONG_TERM_FILES = ("profile.md", "knowledge.md", "projects.md", "learnings.md")


def _ts() -> str:
    return datetime.now(UTC).isoformat()


def _clean(text: str) -> str:
    return text.replace("\x00", "").strip()


@dataclass
class InteractionEvent:
    source: str
    user_id: int
    chat_id: int
    user_text: str
    injected_text: str
    retrieved_snippets: list[str]


class MemoryStore:
    def __init__(self, memory_root: Path):
        self.memory_root = memory_root
        self.daily_dir = memory_root / "daily"
        self.long_term_dir = memory_root / "long_term"
        self.index_dir = memory_root / "index"
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        self.long_term_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_long_term_files()

    def _ensure_long_term_files(self) -> None:
        for file_name in LONG_TERM_FILES:
            p = self.long_term_dir / file_name
            if not p.exists():
                p.write_text(f"# {file_name.replace('.md', '').title()}\n\n", encoding="utf-8")

    def _daily_path(self) -> Path:
        return self.daily_dir / f"{datetime.now().date().isoformat()}.md"

    def log_interaction(self, event: InteractionEvent) -> None:
        snippets = "\n".join(f"- {s}" for s in event.retrieved_snippets) or "- (none)"
        entry = (
            f"\n## {_ts()}\n"
            f"- source: {event.source}\n"
            f"- user_id: {event.user_id}\n"
            f"- chat_id: {event.chat_id}\n\n"
            f"### User Message\n{_clean(event.user_text)}\n\n"
            f"### Retrieved Context\n{snippets}\n\n"
            f"### Injected Prompt\n{_clean(event.injected_text)}\n"
        )
        path = self._daily_path()
        with path.open("a", encoding="utf-8") as f:
            f.write(entry)

    def log_assistant_output(self, text: str) -> None:
        text = _clean(text)
        if not text:
            return
        entry = (
            f"\n### Assistant Output {_ts()}\n"
            f"{text}\n"
        )
        with self._daily_path().open("a", encoding="utf-8") as f:
            f.write(entry)

    def promote_fact(self, fact: str, target_file: str = "learnings.md") -> Path:
        target = self.long_term_dir / target_file
        if target.name not in LONG_TERM_FILES:
            target = self.long_term_dir / "learnings.md"
        line = f"- {_ts()} { _clean(fact) }\n"
        with target.open("a", encoding="utf-8") as f:
            f.write(line)
        return target

    def memory_files(self, scopes: Iterable[str] | None = None) -> list[Path]:
        scopes = set(scopes or ["daily", "long_term"])
        files: list[Path] = []
        if "daily" in scopes:
            files.extend(sorted(self.daily_dir.glob("*.md")))
        if "long_term" in scopes:
            files.extend(sorted(self.long_term_dir.glob("*.md")))
        return files
