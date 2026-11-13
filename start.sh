#!/usr/bin/env bash
set -o errexit

# Telegram botni orqa fonda ishga tushirish
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
    echo "Telegram Bot orqa fonda ishga tushirilmoqda..."
    python manage.py runbot &
fi

# Gunicorn veb-serverini ishga tushirish
echo "Gunicorn veb-server ishga tushirilmoqda (Port: ${PORT:-8000})..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4 --timeout 120
