"""Versioned prompts, one Markdown file per draft kind.

The first line of each file is `version: N`; the rest is the instruction text.
"""

from functools import cache
from pathlib import Path

PROMPTS = Path(__file__).resolve().parent


@cache
def load_prompt(kind: str) -> tuple[str, str]:
    """(version, instructions) for a draft kind. Warning steps share one file per step."""
    path = PROMPTS / f"{kind}.md"
    text = path.read_text()
    first, _, body = text.partition("\n")
    if not first.startswith("version:"):
        raise ValueError(f"{path.name} must start with a version line")
    return first.split(":", 1)[1].strip(), body.strip()
