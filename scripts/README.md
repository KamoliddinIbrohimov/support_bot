# Ma'lumotlarni ko'chirish (Backup & Migration)

## Tezkor ko'rsatma

### 1. Eksport (hozirgi serverdan)

```bash
# Faqat errors
python scripts/export.py

# errors + KB (KB key kerak)
python scripts/export.py --kb-key YOUR_KB_API_KEY

# Natija: backup_20260805_120000/ papkasi
```

### 2. Import (yangi serverga)

```bash
# Yangi server ishga tushgandan keyin
python scripts/import.py --from ./backup_20260805_120000 \
    --bot-api http://NEW-SERVER:8000 \
    --kb-api  http://NEW-SERVER:8100 \
    --kb-key  NEW_SERVER_KB_KEY

# Avval dry-run bilan tekshirish
python scripts/import.py --from ./backup_20260805_120000 --dry-run
```

### 3. To'liq PostgreSQL backup (Docker)

```bash
bash scripts/pg_backup.sh
# → backup_pg_20260805_120000/support_bot.sql
# → backup_pg_20260805_120000/kb.sql
```

### 4. PostgreSQL restore (yangi serverda)

```bash
# Yangi serverda Docker ishga tushgandan keyin
docker exec -i support_postgres psql -U postgres support_bot < backup_pg_20260805_120000/support_bot.sql
docker exec -i kb_postgres     psql -U postgres kb          < backup_pg_20260805_120000/kb.sql
```

---

## Qaysi usulni tanlash?

| Holat | Usul |
|---|---|
| Faqat xatoliklarni ko'chirish | `export.py` + `import.py` |
| Hamma ma'lumotlar (loglar bilan) | `pg_backup.sh` + pg restore |
| Boshqa platforma/OS | `export.py` + `import.py` |
| Bir xil Docker muhit | `pg_backup.sh` + pg restore |

---

## KB API key qayerdan topiladi?

`.env` faylidagi `KB_SEED_API_KEY` — xuddi shu key ishlatiladi.
