from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"
SUPPORTED = {"uz", "ru"}
DEFAULT_LANG = "uz"


@lru_cache(maxsize=8)
def _load(lang: str) -> dict[str, str]:
    path = LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        path = LOCALES_DIR / f"{DEFAULT_LANG}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def t(key: str, lang: str = DEFAULT_LANG) -> str:
    """Return localized string. Falls back to DEFAULT_LANG if key missing."""
    if lang not in SUPPORTED:
        lang = DEFAULT_LANG
    catalog = _load(lang)
    if key in catalog:
        return catalog[key]
    fallback = _load(DEFAULT_LANG)
    return fallback.get(key, key)
