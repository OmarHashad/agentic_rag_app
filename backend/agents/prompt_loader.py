from functools import lru_cache
from pathlib import Path

_PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.md"


@lru_cache(maxsize=1)
def load_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")
