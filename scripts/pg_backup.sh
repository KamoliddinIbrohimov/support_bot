#!/bin/bash
# To'liq PostgreSQL backup (ikkala baza)
# Ishlatish: bash scripts/pg_backup.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT="backup_pg_${TIMESTAMP}"
mkdir -p "$OUT"

echo "📦 PostgreSQL backup: $OUT"

# Bot DB
echo "1️⃣  Bot DB (support_bot)..."
docker exec support_postgres pg_dump -U postgres support_bot > "$OUT/support_bot.sql"
echo "  ✅ support_bot.sql"

# KB DB (pgvector — embeddings bilan)
echo "2️⃣  KB DB (kb)..."
docker exec kb_postgres pg_dump -U postgres kb > "$OUT/kb.sql"
echo "  ✅ kb.sql"

echo ""
echo "✅ Backup tayyor: $OUT/"
echo "   Yangi serverga ko'chirish:"
echo "   scp -r $OUT user@NEW-SERVER:/opt/support/"
