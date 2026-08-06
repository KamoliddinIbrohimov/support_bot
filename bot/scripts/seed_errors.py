"""Test uchun namunaviy xatoliklarni bazaga qo'shadigan skript.

Ishlatish:
    python -m scripts.seed_errors
"""
from __future__ import annotations

import asyncio

from config.logger import logger, setup_logging
from database.connection import get_session
from database.repositories import ErrorRepository


SAMPLE_ERRORS = [
    {
        "title": "Fiscal connection error",
        "keywords": [
            "нет соединения",
            "connection failed",
            "сервер недоступен",
            "код 104",
        ],
        "description": "Fiskal server bilan aloqa uzilgan.",
        "solution": "FiscalDriveAPI xizmatini restart qiling, internet aloqasini tekshiring.",
    },
    {
        "title": "Printer not found",
        "keywords": [
            "printer not found",
            "принтер не найден",
            "устройство не обнаружено",
        ],
        "description": "Chek printeri tizim tomonidan topilmadi.",
        "solution": "USB kabelni tekshiring, printer drayveri o'rnatilganini tasdiqlang.",
    },
    {
        "title": "Database timeout",
        "keywords": [
            "database timeout",
            "connection timed out",
            "истекло время ожидания",
        ],
        "description": "Ma'lumotlar bazasiga so'rov muddati o'tib ketdi.",
        "solution": "Server yukini tekshiring, PostgreSQL servisini restart qiling.",
    },
]


async def main() -> None:
    setup_logging()
    async with get_session() as session:
        repo = ErrorRepository(session)
        existing = list(await repo.list_all())
        if existing:
            logger.info(f"Bazada allaqachon {len(existing)} ta yozuv bor. Chetlab o'tildi.")
            return

        for item in SAMPLE_ERRORS:
            entry = await repo.create(**item)
            logger.info(f"Qo'shildi #{entry.id}: {entry.title}")


if __name__ == "__main__":
    asyncio.run(main())
