from __future__ import annotations

import re
from collections.abc import Mapping

_ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")
_LATIN_RE = re.compile(r"[A-Za-z]")


def _combine_text(value: str | Mapping[str, str] | None) -> str:
    if value is None:
        return ""
    if isinstance(value, Mapping):
        return "\n".join(str(item) for item in value.values() if item)
    return str(value)


def detect_language(text: str | Mapping[str, str] | None) -> str:
    combined = _combine_text(text)
    if not combined.strip():
        return "english"

    arabic_count = len(_ARABIC_RE.findall(combined))
    latin_count = len(_LATIN_RE.findall(combined))

    if arabic_count == 0:
        return "english"
    if latin_count == 0:
        return "arabic"
    return "arabic" if arabic_count >= latin_count else "english"
