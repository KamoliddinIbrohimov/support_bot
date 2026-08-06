from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from rapidfuzz import fuzz

from config.logger import logger
from config.settings import settings
from database.models import ErrorEntry


@dataclass(slots=True)
class MatchResult:
    error: ErrorEntry
    score: float
    matched_keyword: str


class ErrorFinderService:
    """OCR matnini xato bazasidagi kalit so'zlar bilan solishtiradi.

    Foydalanuvchi tilida keyword'lar bo'lmasa, rus tiliga fallback qiladi.
    """

    def __init__(self, threshold: int | None = None) -> None:
        self._threshold = threshold if threshold is not None else settings.FUZZY_MATCH_THRESHOLD

    def find_best(
        self,
        text: str,
        errors: Sequence[ErrorEntry],
        lang: str = "uz",
    ) -> MatchResult | None:
        text_norm = self._normalize(text)
        if not text_norm or not errors:
            return None

        best: MatchResult | None = None

        for err in errors:
            keywords = err.get_keywords(lang)
            for keyword in keywords:
                keyword_norm = self._normalize(keyword)
                if not keyword_norm:
                    continue

                partial = fuzz.partial_ratio(keyword_norm, text_norm)
                token_set = fuzz.token_set_ratio(keyword_norm, text_norm)
                score = max(partial, token_set)

                if best is None or score > best.score:
                    best = MatchResult(error=err, score=score, matched_keyword=keyword)

        if best is None:
            return None

        logger.debug(
            f"Best match: title={best.error.title!r} kw={best.matched_keyword!r} score={best.score:.1f}"
        )

        if best.score < self._threshold:
            return None
        return best

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.lower().split())
