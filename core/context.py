from django.conf import settings


def site(request):
    iso_date = getattr(settings, "FESTIVAL_DATE", "2026-11-19T09:00:00+05:00")
    display_date = "19-Noyabr, 2026"
    day_month = "19-noyabr"
    display_time = "09:00"
    location = "Urganch"

    try:
        from core.models import FestivalSetting

        cfg = FestivalSetting.get_solo()
        iso_date = cfg.iso_date()
        display_date = cfg.display_date()
        day_month = cfg.display_day_month()
        display_time = cfg.display_time()
        location = cfg.location or "Urganch"
    except Exception:
        pass

    return {
        "FESTIVAL_DATE": iso_date,
        "FESTIVAL_DATE_DISPLAY": display_date,
        "FESTIVAL_DAY_MONTH": day_month,
        "FESTIVAL_TIME": display_time,
        "FESTIVAL_LOCATION": location,
        "TELEGRAM_URL": getattr(settings, "TELEGRAM_URL", "https://t.me/UrDU_startup_bot"),
        "SITE_URL": getattr(settings, "SITE_URL", "http://localhost:8000"),
    }
