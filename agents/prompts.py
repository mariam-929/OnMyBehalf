"""Load prompt text from `prompts/*.md` — the files are the source of truth, not string literals.

The prompts live in Markdown because they are a graded artefact (the brief requires the system
prompt on screen during the demo and an iteration log). Duplicating them as Python strings would
guarantee the two drift, and the version demoed would not be the version documented.

Each file has `## System` and optional `## Few-shot examples` sections; the loader returns
everything from `## System` onward, so few-shot examples travel with the prompt.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


@lru_cache(maxsize=8)
def load_prompt(name: str, version: str = "v1") -> str:
    """Return the system prompt (plus few-shot examples) from prompts/{name}_{version}.md."""
    path = PROMPT_DIR / f"{name}_{version}.md"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^##\s*System\s*$", text, re.M)
    if not m:
        return text.strip()
    body = text[m.end():]
    # drop a trailing "## Notes"-style section if one follows the few-shot block
    body = re.split(r"^##\s*(?:Notes|Changelog|Iteration)\b", body, flags=re.M)[0]
    return body.strip()
