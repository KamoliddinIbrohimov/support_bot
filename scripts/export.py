#!/usr/bin/env python3
"""
Export all bot data to a timestamped backup folder.

Usage:
    python scripts/export.py
    python scripts/export.py --bot-api http://localhost:8000
    python scripts/export.py --kb-api http://localhost:8100 --kb-key YOUR_KEY
    python scripts/export.py --out ./my_backup
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx kerak — pip install httpx")
    sys.exit(1)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Support Bot — ma'lumotlarni eksport qilish")
    p.add_argument("--bot-api", default="http://localhost:8000", help="Bot API URL")
    p.add_argument("--kb-api",  default="http://localhost:8100",  help="KB API URL")
    p.add_argument("--kb-key",  default="",                       help="KB API key (X-API-Key)")
    p.add_argument("--out",     default="",                       help="Backup papkasi (default: backup_YYYYMMDD_HHMMSS)")
    return p.parse_args()


def save(folder: Path, name: str, data: list | dict) -> None:
    path = folder / name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"  ✅ {name} — {len(data) if isinstance(data, list) else 1} ta yozuv")


def export_errors(client: httpx.Client, bot_api: str) -> list:
    r = client.get(f"{bot_api}/errors", timeout=30)
    r.raise_for_status()
    return r.json()


def export_kb_entries(client: httpx.Client, kb_api: str, kb_key: str) -> list:
    if not kb_key:
        print("  ⚠️  --kb-key berilmadi — KB eksport o'tkazib yuboriladi")
        return []
    headers = {"X-API-Key": kb_key}
    all_entries: list = []
    offset = 0
    limit = 200
    while True:
        r = client.get(
            f"{kb_api}/kb/entries",
            headers=headers,
            params={"limit": limit, "offset": offset},
            timeout=30,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        all_entries.extend(batch)
        if len(batch) < limit:
            break
        offset += limit
    return all_entries


def main() -> None:
    args = parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = Path(args.out) if args.out else Path(f"backup_{timestamp}")
    folder.mkdir(parents=True, exist_ok=True)

    print(f"\n📦 Backup papkasi: {folder.resolve()}\n")

    with httpx.Client() as client:
        # ── Errors ──────────────────────────────────────────────────────────────
        print("1️⃣  Xatoliklar bazasi (errors)...")
        try:
            errors = export_errors(client, args.bot_api)
            save(folder, "errors.json", errors)
        except Exception as e:
            print(f"  ❌ errors eksport xatolik: {e}")

        # ── KB entries ───────────────────────────────────────────────────────────
        print("2️⃣  Knowledge Base yozuvlari (kb_entries)...")
        try:
            kb_entries = export_kb_entries(client, args.kb_api, args.kb_key)
            if kb_entries:
                save(folder, "kb_entries.json", kb_entries)
        except Exception as e:
            print(f"  ❌ KB eksport xatolik: {e}")

    # ── Meta ──────────────────────────────────────────────────────────────────
    meta = {
        "exported_at": datetime.now().isoformat(),
        "bot_api": args.bot_api,
        "kb_api": args.kb_api,
        "files": [f.name for f in folder.iterdir()],
    }
    save(folder, "meta.json", meta)

    print(f"\n✅ Eksport tugadi! Papka: {folder.resolve()}\n")


if __name__ == "__main__":
    main()
