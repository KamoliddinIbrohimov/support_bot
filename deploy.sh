#!/bin/bash
set -e

echo "=== Deploy boshlandi: $(date) ==="

cd "$(dirname "$0")"

# Mavjud containerlarni to'xtatib, yangi image build qilib ishga tushirish
docker compose down --remove-orphans
docker compose up -d --build --remove-orphans

# Admin panel
echo "Admin panel ishga tushirilmoqda..."
cd admin-panel
docker compose up -d --build --remove-orphans
cd ..

echo "=== Deploy tugadi: $(date) ==="
docker compose ps
