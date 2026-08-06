#!/usr/bin/env python3
"""
Import backup data to a new server.

Usage:
    python scripts/import.py --from ./backup_20260805_120000
    python scripts/import.py --from ./backup_20260805_120000 --bot-api http://NEW-SERVER:8000
    python scripts/import.py --from ./backup_20260805_120000 --kb-api http://NEW-SERVER:8100 --kb-key NEW_KEY
    python scripts/import.py --from ./backup_20260805_120000 --only errors
    python scripts/import.py --from ./backup_20260805_120000 --only kb
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx kerak — pip install httpx")
    sys.exit(1)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Support Bot — ma'lumotlarni import qilish")
    p.add_argument("--from",    dest="src",     required=True,              help="Backup papkasi yo'li")
    p.add_argument("--bot-api", default="http://localhost:8000",            help="Yangi server Bot API URL")
    p.add_argument("--kb-api",  default="http://localhost:8100",            help="Yangi server KB API URL")
    p.add_argument("--kb-key",  default="",                                 help="Yangi server KB API key")
    p.add_argument("--only",    choices=["errors", "kb"], default=None,     help="Faqat bitta qismni import qilish")
    p.add_argument("--dry-run", action="store_true",                        help="Haqiqatda yozmasdan — tekshiruv rejimi")
    return p.parse_args()


def load(folder: Path, name: str) -> list | None:
    path = folder / name
    if not path.exists():
        print(f"  ⚠️  {name} topilmadi — o'tkazib yuboriladi")
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"  📂 {name} — {len(data)} ta yozuv o'qildi")
    return data


def import_errors(client: httpx.Client, bot_api: str, errors: list, dry_run: bool) -> None:
    ok = skip = fail = 0
    for e in errors:
        payload = {k: e[k] for k in (
            "title", "keywords", "description", "solution",
            "title_ru", "title_uz", "keywords_ru", "keywords_uz",
            "description_ru", "description_uz", "solution_ru", "solution_uz",
        ) if k in e}
        if dry_run:
            print(f"    [dry-run] POST /errors — {e.get('title', '?')}")
            ok += 1
            continue
        try:
            r = client.post(f"{bot_api}/errors", json=payload, timeout=15)
            if r.status_code == 201:
                ok += 1
            elif r.status_code == 409:
                skip += 1
            else:
                print(f"    ⚠️  {e.get('title','?')} — {r.status_code}: {r.text[:80]}")
                fail += 1
        except Exception as ex:
            print(f"    ❌ {e.get('title','?')} — {ex}")
            fail += 1
    print(f"  ✅ errors: {ok} import, {skip} mavjud, {fail} xatolik")


def import_kb(client: httpx.Client, kb_api: str, kb_key: str, entries: list, dry_run: bool) -> None:
    if not kb_key:
        print("  ⚠️  --kb-key berilmadi — KB import o'tkazib yuboriladi")
        return
    headers = {"X-API-Key": kb_key}
    ok = fail = 0
    for e in entries:
        # Faqat verified yozuvlarni ko'chiramiz (pending/rejected emas)
        if e.get("status") not in ("verified", "active", None):
            continue
        payload = {
            "title":       e.get("title") or e.get("query", ""),
            "description": e.get("description"),
            "solution":    e.get("solution", ""),
            "language":    e.get("language", "uz"),
            "source":      "migration",
            "status":      "verified",
            "is_shared":   e.get("is_shared", False),
        }
        if not payload["title"] or not payload["solution"]:
            continue
        if dry_run:
            print(f"    [dry-run] POST /kb/entries — {payload['title'][:50]}")
            ok += 1
            continue
        try:
            r = client.post(f"{kb_api}/kb/entries", headers=headers, json=payload, timeout=30)
            if r.status_code == 201:
                ok += 1
            else:
                print(f"    ⚠️  {payload['title'][:40]} — {r.status_code}: {r.text[:80]}")
                fail += 1
        except Exception as ex:
            print(f"    ❌ {payload['title'][:40]} — {ex}")
            fail += 1
    print(f"  ✅ kb_entries: {ok} import, {fail} xatolik")


def main() -> None:
    args = parse_args()
    folder = Path(args.src)

    if not folder.exists():
        print(f"❌ Papka topilmadi: {folder}")
        sys.exit(1)

    dry_label = " [DRY-RUN]" if args.dry_run else ""
    print(f"\n📥 Import{dry_label}: {folder.resolve()}\n")

    # Meta ma'lumot
    meta_path = folder / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        print(f"  📋 Eksport sanasi: {meta.get('exported_at','?')}")
        print(f"  📋 Manba Bot API:  {meta.get('bot_api','?')}")
        print()

    with httpx.Client() as client:
        # ── Errors ──────────────────────────────────────────────────────────────
        if args.only in (None, "errors"):
            print("1️⃣  Xatoliklar (errors)...")
            errors = load(folder, "errors.json")
            if errors:
                import_errors(client, args.bot_api, errors, args.dry_run)

        # ── KB ───────────────────────────────────────────────────────────────────
        if args.only in (None, "kb"):
            print("2️⃣  Knowledge Base (kb_entries)...")
            kb_entries = load(folder, "kb_entries.json")
            if kb_entries:
                import_kb(client, args.kb_api, args.kb_key, kb_entries, args.dry_run)

    print(f"\n✅ Import tugadi!\n")


if __name__ == "__main__":
    main()
