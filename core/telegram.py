import json
import logging
import requests
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)

BOT_TOKEN = getattr(settings, "TELEGRAM_BOT_TOKEN", "9260594956:AAH5Ny0ByaH1r8xx_oTGaIaKoRSb7ZXmcrM")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_telegram_request(method: str, payload: dict) -> dict:
    """Telegram Bot API ga so'rov yuborish."""
    url = f"{API_URL}/{method}"
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if not data.get("ok"):
            logger.warning("Telegram API xatosi (%s): %s", method, data.get("description"))
        return data
    except Exception as e:
        logger.error("Telegramga ulanishda xatolik (%s): %s", method, e)
        return {"ok": False, "error": str(e)}


def get_active_admin_chat_ids() -> list[int]:
    """Barcha faol adminlarning chat_id lari ro'yxatini qaytaradi."""
    chat_ids = set()
    # Sozlamalardagi asosiy adminlar
    for cid in getattr(settings, "TELEGRAM_ADMIN_IDS", []):
        try:
            chat_ids.add(int(cid))
        except (ValueError, TypeError):
            pass

    # Bazadagi adminlar
    try:
        from core.models import TelegramAdmin
        for admin in TelegramAdmin.objects.filter(is_active=True, notify_on_application=True):
            chat_ids.add(admin.chat_id)
    except Exception as e:
        logger.debug("TelegramAdmin bazadan o'qilmadi: %s", e)

    return list(chat_ids)


def notify_admins_new_application(application) -> int:
    """Yangi ariza kelganda barcha adminlarga inline tugmali xabar yuboradi."""
    project = getattr(application, "project", None)
    participant = getattr(application, "participant", None)
    if not project or not participant:
        return 0

    site_url = getattr(settings, "SITE_URL", "http://localhost:8000").rstrip("/")
    status_url = f"{site_url}{reverse('status')}?number={application.number}"

    files_summary = []
    files = project.files.all()
    presentations = files.filter(kind="presentation").count()
    documents = files.filter(kind="document").count()
    images = files.filter(kind="image").count()
    videos = files.filter(kind="video").count()

    if presentations: files_summary.append("📊 Taqdimot")
    if documents: files_summary.append("📄 Hujjat")
    if images: files_summary.append(f"🖼 {images} ta rasm")
    if videos: files_summary.append("🎥 Demo video")
    files_text = ", ".join(files_summary) if files_summary else "Yuklanmagan"

    tg_username = f"@{participant.telegram_username.lstrip('@')}" if participant.telegram_username else "Ko'rsatilmagan"

    text = (
        f"🚀 <b>YANGI ARIZA QABUL QILINDI!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>Ariza raqami:</b> <code>{application.number}</code>\n"
        f"👤 <b>Ishtirokchi:</b> <b>{participant.full_name()}</b>\n"
        f"🎓 <b>Guruh:</b> {participant.group} · {participant.study_direction}\n"
        f"📞 <b>Telefon:</b> <code>{participant.phone}</code>\n"
        f"✈️ <b>Telegram:</b> {tg_username}\n\n"
        f"💡 <b>LOYIHA:</b>\n"
        f"🏷 <b>Yo'nalish:</b> {project.category.name}\n"
        f"📌 <b>Nomi:</b> <b>{project.title}</b>\n"
        f"📝 <b>Qisqacha:</b> {project.summary[:300]}{'...' if len(project.summary) > 300 else ''}\n\n"
        f"📎 <b>Materiallar:</b> {files_text}\n"
    )
    if project.link:
        text += f"🔗 <b>Havola:</b> <a href=\"{project.link}\">{project.link}</a>\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━━\n🕒 <i>{application.created_at.strftime('%d.%m.%Y %H:%M')}</i>"

    # Inline tugmalar
    inline_keyboard = [
        [
            {"text": "✅ Tasdiqlash", "callback_data": f"app:approved:{application.id}"},
            {"text": "❌ Rad etish", "callback_data": f"app:rejected:{application.id}"},
        ],
        [
            {"text": "⏳ Ko'rib chiqish", "callback_data": f"app:review:{application.id}"},
            {"text": "📋 To'liq matn", "callback_data": f"app:details:{application.id}"},
        ]
    ]

    # Telegram faqat to'liq public domenli URLlarni qabul qiladi (localhost da xatolik bermasligi uchun)
    if not ("localhost" in site_url or "127.0.0.1" in site_url):
        inline_keyboard.append([{"text": "🌐 Saytda tekshirish", "url": status_url}])

    keyboard = {"inline_keyboard": inline_keyboard}

    sent_count = 0
    admin_ids = get_active_admin_chat_ids()
    for cid in admin_ids:
        res = send_telegram_request("sendMessage", {
            "chat_id": cid,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": keyboard,
            "disable_web_page_preview": True
        })
        if res.get("ok"):
            sent_count += 1

    return sent_count


def send_message_to_user(chat_id: int, text: str, reply_markup=None):
    """Foydalanuvchiga xabar yuborish."""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return send_telegram_request("sendMessage", payload)
