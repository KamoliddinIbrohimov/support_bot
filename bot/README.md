# Telegram Support Automation Bot

Screenshotdan xatolik matnini OCR orqali o'qib, PostgreSQL bazasidan mos yechim chiqaruvchi Telegram bot.

## Stack
- **Python 3.12**, `aiogram 3.x`, `FastAPI`
- **PostgreSQL** + `SQLAlchemy 2.0` (async) + `Alembic`
- **EasyOCR** (rus/ingliz) + **OpenCV** (grayscale, denoise, CLAHE)
- **RapidFuzz** (keyword matching, threshold sozlanadi)
- **Docker + docker-compose**
- `loguru` logging (fayl + konsol, rotatsiya)

## Struktura
```
support_bot/
├── bot/
│   ├── main.py                 # Bot entry point
│   ├── handlers/
│   │     ├── commands.py       # /start, /help, /errors
│   │     ├── admin.py          # /add_error FSM, /cancel
│   │     └── photo.py          # rasm -> OCR -> match -> javob
│   ├── services/
│   │     ├── ocr_service.py    # EasyOCR async wrapper
│   │     ├── image_processor.py# OpenCV preprocess
│   │     └── error_finder.py   # RapidFuzz matching
│   ├── keyboards/
│   ├── states/                 # FSM states
│   └── utils/                  # storage, formatters
├── api/
│   ├── main.py                 # FastAPI app
│   └── schemas.py
├── database/
│   ├── models.py               # errors, ocr_logs
│   ├── connection.py           # async engine + session
│   ├── repositories.py
│   └── migrations/             # Alembic
├── config/
│   ├── settings.py             # pydantic-settings
│   └── logger.py               # loguru
├── storage/images/             # yuklangan rasmlar
├── scripts/seed_errors.py      # namunaviy data
├── docker-compose.yml
├── Dockerfile
├── alembic.ini
├── requirements.txt
└── .env.example
```

## Ishga tushirish

### 1. `.env` fayl
```bash
cp .env.example .env
# BOT_TOKEN va ADMIN_IDS ni to'ldiring
```

### 2. Docker orqali
```bash
docker-compose up --build
```
- `bot` — polling rejimida ishlaydi, avtomatik `alembic upgrade head` bajaradi.
- `api` — `http://localhost:8000/docs` da Swagger UI.
- `postgres` — port `5432`.

### 3. Namunaviy xatoliklar
```bash
docker-compose exec bot python -m scripts.seed_errors
```

## Bot logikasi

1. Rasm keldi → `storage/images/YYYY-MM-DD/{chat}_{user}_{time}.jpg` saqlanadi.
2. OpenCV: grayscale → fastNlMeansDenoising → CLAHE → Otsu threshold.
3. EasyOCR (`ru`, `en`) → matn + confidence.
4. RapidFuzz (`partial_ratio` + `token_set_ratio`, max) — bazadagi barcha `keywords` bilan solishtiradi.
5. Agar `score >= FUZZY_MATCH_THRESHOLD` (default `70`) — yechim javob qilinadi.
6. Har bir rasm `ocr_logs` jadvaliga yoziladi.

## Admin komandalar
- `/add_error` — 3 bosqichli FSM (title → keywords → solution).
- `/errors` — bazadagi barcha xatoliklar ro'yxati.
- `/cancel` — FSM ni to'xtatadi.

## API (FastAPI)
- `GET /health`
- `GET /errors` — ro'yxat
- `POST /errors` — yangi qo'shish
- `GET /errors/{id}`
- `DELETE /errors/{id}`
- `GET /logs?limit=50`

## Migrations
```bash
# yangi revision yaratish
docker-compose exec bot alembic revision --autogenerate -m "message"

# qo'llash
docker-compose exec bot alembic upgrade head
```

## Test misol

Screenshot: `Ошибка соединения с сервером код 104`

Bot javobi:
```
⚠️ Xatolik aniqlandi

Muammo:
Fiscal connection error

Screenshotdan o'qilgan:
Ошибка соединения с сервером код 104

Yechim:
FiscalDriveAPI restart qiling, internetni tekshiring

Aniqlik: 92%
```
