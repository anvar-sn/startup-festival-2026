from django.conf import settings

def site(request):
    return {
        "FESTIVAL_DATE": getattr(settings, "FESTIVAL_DATE", "2026-11-19T09:00:00+05:00"),
        "TELEGRAM_URL": getattr(settings, "TELEGRAM_URL", "https://t.me/UrDU_startup_bot"),
        "SITE_URL": getattr(settings, "SITE_URL", "http://localhost:8000"),
    }
