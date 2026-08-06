from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import easyocr
import numpy as np

from bot.services.ai_client import vision_complete
from config.logger import logger
from config.settings import settings

# Global semaphore — bir vaqtda faqat 1 ta EasyOCR call
# Guruhlardan parallel kelgan rasmlar navbatda kutadi, RAM oshib ketmaydi
_ocr_semaphore = asyncio.Semaphore(1)

# AI OCR fallback threshold
_AI_FALLBACK_THRESHOLD = 0.5


async def easyocr_only(image_path: str | Path) -> tuple[str, float]:
    """EasyOCR faqat — AI fallback yo'q. Qaytaradi: (text, confidence)."""
    path = Path(image_path)
    try:
        service = OCRService()
        async with _ocr_semaphore:
            logger.info(f"EasyOCR navbatga kirdi: {path.name}")
            result = await service.recognize(str(path))
            logger.info(
                f"EasyOCR: text_len={len(result.text)} conf={result.confidence:.2f}"
            )
            return result.text, result.confidence
    except Exception as exc:
        logger.warning(f"EasyOCR xatolik: {exc}")
        return "", 0.0


async def claude_ocr(image_path: str | Path) -> str:
    """AI vision OCR — Gemini/Anthropic orqali rasm matnini o'qiydi."""
    if not settings.vision_enabled:
        return ""
    result = await vision_complete(
        system="You extract text from images exactly as written.",
        user_text=(
            "Extract ALL visible text from this image exactly as written. "
            "Include error messages, dialog boxes, status bars, corner notifications, "
            "and any text anywhere in the image. "
            "Return only the extracted text, nothing else."
        ),
        image_path=Path(image_path),
        max_tokens=600,
    )
    if result:
        logger.info(f"AI OCR: {len(result)} chars extracted")
    return result


async def ocr_with_fallback(image_path: str | Path) -> tuple[str, str]:
    """Asosiy OCR pipeline: EasyOCR → AI fallback.

    Returns: (text, source) — source = 'easyocr' | 'ai' | 'empty'
    """
    path = Path(image_path)

    # ── 1. EasyOCR (semaphore orqali — navbat bilan) ─────────────────────────
    easyocr_text = ""
    easyocr_conf = 0.0
    try:
        service = OCRService()
        async with _ocr_semaphore:
            logger.info(f"EasyOCR navbatga kirdi: {path.name}")
            result = await service.recognize(str(path))
            easyocr_text = result.text
            easyocr_conf = result.confidence
            logger.info(
                f"EasyOCR: text_len={len(easyocr_text)} conf={easyocr_conf:.2f}"
            )
    except Exception as exc:
        logger.warning(f"EasyOCR xatolik: {exc}")

    # ── 2. Natija yaxshi bo'lsa — qaytarish ──────────────────────────────────
    if easyocr_text and easyocr_conf >= _AI_FALLBACK_THRESHOLD:
        return easyocr_text, "easyocr"

    # ── 3. AI fallback — loyqa rasm yoki past confidence ─────────────────────
    logger.info(
        f"EasyOCR weak (text={bool(easyocr_text)}, conf={easyocr_conf:.2f}) "
        f"— AI OCR ga o'tilmoqda"
    )
    ai_text = await claude_ocr(path)
    if ai_text:
        return ai_text, "ai"

    # Ikkisi ham bo'sh bo'lsa — easyocr natijasini qaytaramiz (yaxshisi yo'q)
    return easyocr_text, "empty"


@dataclass(slots=True)
class OCRResult:
    text: str
    confidence: float
    raw: list[Any]

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "confidence": round(self.confidence, 2)}


class OCRService:
    """EasyOCR singleton — butun bot bo'yicha bitta reader."""

    _reader: easyocr.Reader | None = None
    _lock = asyncio.Lock()

    def __init__(
        self,
        languages: list[str] | None = None,
        use_gpu: bool | None = None,
        min_confidence: float | None = None,
    ) -> None:
        self._languages = languages or settings.OCR_LANGUAGES
        self._use_gpu = settings.OCR_USE_GPU if use_gpu is None else use_gpu
        self._min_confidence = (
            settings.OCR_MIN_CONFIDENCE if min_confidence is None else min_confidence
        )

    async def _get_reader(self) -> easyocr.Reader:
        if OCRService._reader is not None:
            return OCRService._reader
        async with OCRService._lock:
            if OCRService._reader is None:
                logger.info(
                    f"EasyOCR reader yuklanmoqda: langs={self._languages}, gpu={self._use_gpu}"
                )
                loop = asyncio.get_running_loop()
                OCRService._reader = await loop.run_in_executor(
                    None,
                    lambda: easyocr.Reader(
                        self._languages, gpu=self._use_gpu, verbose=False
                    ),
                )
                logger.info("EasyOCR reader tayyor.")
        return OCRService._reader

    async def recognize(self, image: str | Path | np.ndarray) -> OCRResult:
        reader = await self._get_reader()
        loop = asyncio.get_running_loop()
        source: Any = str(image) if isinstance(image, (str, Path)) else image
        try:
            raw = await loop.run_in_executor(
                None,
                lambda: reader.readtext(
                    source,
                    detail=1,
                    paragraph=False,
                    text_threshold=0.6,
                    low_text=0.3,
                    contrast_ths=0.05,
                    adjust_contrast=0.7,
                ),
            )
        except Exception as exc:
            logger.exception(f"OCR xatolik: {exc}")
            return OCRResult(text="", confidence=0.0, raw=[])
        return self._to_result(raw)

    def _to_result(self, raw: list[Any]) -> OCRResult:
        filtered = [item for item in raw if item[2] >= self._min_confidence]
        if not filtered:
            filtered = raw
        text_parts = [item[1].strip() for item in filtered if item[1].strip()]
        confidences = [float(item[2]) for item in filtered]
        text = " ".join(text_parts).strip()
        avg_conf = float(np.mean(confidences)) if confidences else 0.0
        return OCRResult(text=text, confidence=avg_conf, raw=raw)
