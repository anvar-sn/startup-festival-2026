import asyncio
from django.conf import settings
from django.core.management.base import BaseCommand

from core.bot_engine import run_polling_bot


class Command(BaseCommand):
    help = "Urganch Davlat Akademik Litseyi Startup Festivali Telegram botini ishga tushirish"

    def handle(self, *args, **options):
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        if not token:
            self.stderr.write(self.style.ERROR("TELEGRAM_BOT_TOKEN topilmadi!"))
            return

        self.stdout.write(self.style.SUCCESS("Telegram bot polling rejimida ishga tushirilmoqda..."))
        asyncio.run(run_polling_bot(token))
