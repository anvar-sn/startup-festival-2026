"""Startup Festivali 2026 — Telegram Bot dvijogi (Webhook va Polling uchun yagona modul)."""
from __future__ import annotations

import asyncio
import calendar
import datetime
import hashlib
import logging
import re
from typing import Any

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command as TgCommand, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    BotCommandScopeDefault,
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    Update,
)
from asgiref.sync import sync_to_async
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PostgreSQL asosidagi aiogram FSM xotirasi (Vercel serverless uchun Redis'siz)
# ---------------------------------------------------------------------------
class DjangoORMStorage(BaseStorage):
    """aiogram FSM holati va ma'lumotlarini Django ORM (Neon PostgreSQL) da saqlaydi."""

    @staticmethod
    def _make_key(key: StorageKey) -> str:
        return f"{key.bot_id}:{key.chat_id}:{key.user_id}:{key.destiny}"

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        raw_key = self._make_key(key)
        state_val = state.state if isinstance(state, State) else state

        @sync_to_async
        def _op():
            from core.models import TelegramFSMState

            obj, created = TelegramFSMState.objects.get_or_create(
                key=raw_key,
                defaults={"state": state_val, "data": {}},
            )
            if not created:
                if state_val is None and not obj.data:
                    obj.delete()
                else:
                    obj.state = state_val
                    obj.save(update_fields=["state", "updated_at"])

        await _op()

    async def get_state(self, key: StorageKey) -> str | None:
        raw_key = self._make_key(key)

        @sync_to_async
        def _op():
            from core.models import TelegramFSMState

            obj = TelegramFSMState.objects.filter(key=raw_key).only("state").first()
            return obj.state if obj else None

        return await _op()

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        raw_key = self._make_key(key)
        payload = dict(data or {})

        @sync_to_async
        def _op():
            from core.models import TelegramFSMState

            obj, created = TelegramFSMState.objects.get_or_create(
                key=raw_key,
                defaults={"state": None, "data": payload},
            )
            if not created:
                if not payload and obj.state is None:
                    obj.delete()
                else:
                    obj.data = payload
                    obj.save(update_fields=["data", "updated_at"])

        await _op()

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        raw_key = self._make_key(key)

        @sync_to_async
        def _op():
            from core.models import TelegramFSMState

            obj = TelegramFSMState.objects.filter(key=raw_key).only("data").first()
            return dict(obj.data) if obj and isinstance(obj.data, dict) else {}

        return await _op()

    async def close(self) -> None:
        return None


# ---------------------------------------------------------------------------
# FSM holatlari
# ---------------------------------------------------------------------------
class BotStates(StatesGroup):
    waiting_for_app_number = State()
    waiting_for_broadcast = State()
    waiting_for_festival_date = State()


class ApplyStates(StatesGroup):
    full_name = State()
    birth_date = State()
    phone = State()
    group_info = State()
    category = State()
    project_title = State()
    project_summary = State()
    project_link = State()
    project_file = State()
    confirm = State()


# ---------------------------------------------------------------------------
# Yordamchi funksiyalar
# ---------------------------------------------------------------------------
def get_webhook_secret() -> str:
    secret = getattr(settings, "SECRET_KEY", "startup-festival-2026")
    return hashlib.sha256(f"festival-tg-webhook:{secret}".encode("utf-8")).hexdigest()[:48]


def parse_date_input(text: str) -> str | None:
    text = text.strip()
    m = re.match(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{4})$", text)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime.date(year, month, day).isoformat()
        except ValueError:
            return None
    m2 = re.match(r"^(\d{4})[./-](\d{1,2})[./-](\d{1,2})$", text)
    if m2:
        year, month, day = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        try:
            return datetime.date(year, month, day).isoformat()
        except ValueError:
            return None
    return None


def parse_festival_datetime(text: str, base_dt: datetime.datetime) -> datetime.datetime | None:
    """Admin kiritgan festival sanasini tahlil qiladi.

    Qo'llab-quvvatlanadigan formatlar:
    - 25.12.2026
    - 25.12.2026 10:30
    - 2026-12-25
    - 2026-12-25 14:00
    """
    from core.models import get_tashkent_tz

    raw = re.sub(r"\s+", " ", (text or "").strip())
    tz = get_tashkent_tz()
    default_hour = base_dt.hour
    default_minute = base_dt.minute

    # DD.MM.YYYY [HH:MM]
    m1 = re.match(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{4})(?:\s+(\d{1,2}):(\d{2}))?$", raw)
    if m1:
        day, month, year = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
        hour = int(m1.group(4)) if m1.group(4) is not None else default_hour
        minute = int(m1.group(5)) if m1.group(5) is not None else default_minute
        try:
            return datetime.datetime(year, month, day, hour, minute, tzinfo=tz)
        except ValueError:
            return None

    # YYYY-MM-DD [HH:MM]
    m2 = re.match(r"^(\d{4})[./-](\d{1,2})[./-](\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?$", raw)
    if m2:
        year, month, day = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        hour = int(m2.group(4)) if m2.group(4) is not None else default_hour
        minute = int(m2.group(5)) if m2.group(5) is not None else default_minute
        try:
            return datetime.datetime(year, month, day, hour, minute, tzinfo=tz)
        except ValueError:
            return None

    return None


def shift_datetime_months(dt: datetime.datetime, months: int) -> datetime.datetime:
    month_idx = dt.month - 1 + months
    year = dt.year + month_idx // 12
    month = month_idx % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return dt.replace(year=year, month=month, day=min(dt.day, last_day))


def clean_phone_number(raw: str) -> str:
    cleaned = re.sub(r"[^\d+]", "", raw.strip())
    if not cleaned.startswith("+"):
        if cleaned.startswith("998"):
            cleaned = "+" + cleaned
        elif len(cleaned) == 9:
            cleaned = "+998" + cleaned
        else:
            cleaned = "+" + cleaned
    return cleaned


def is_valid_public_url(url: str) -> bool:
    if not url:
        return False
    u = url.lower()
    return not ("localhost" in u or "127.0.0.1" in u or "0.0.0.0" in u) and (
        u.startswith("http://") or u.startswith("https://")
    )


def get_site_url() -> str:
    return getattr(settings, "SITE_URL", "https://startup-festival-2026.vercel.app").rstrip("/")


# ---------------------------------------------------------------------------
# DB operatsiyalari (sync_to_async)
# ---------------------------------------------------------------------------
@sync_to_async
def get_festival_date_info() -> dict:
    from core.models import FestivalSetting

    cfg = FestivalSetting.get_solo()
    return {
        "iso": cfg.iso_date(),
        "local_dt": cfg.local_dt(),
        "display_date": cfg.display_date(),
        "display_day_month": cfg.display_day_month(),
        "display_time": cfg.display_time(),
        "display_full": cfg.display_full(),
        "location": cfg.location or "Urganch",
        "updated_by": cfg.updated_by,
    }


@sync_to_async
def update_festival_date_db(new_dt: datetime.datetime, admin_name: str) -> dict:
    from core.models import AuditLog, FestivalSetting

    cfg = FestivalSetting.get_solo()
    old_full = cfg.display_full()
    cfg.festival_date = new_dt
    cfg.updated_by = admin_name[:128]
    cfg.save(update_fields=["festival_date", "updated_by", "updated_at"])

    new_full = cfg.display_full()
    AuditLog.objects.create(
        action="tg_festival_date_changed",
        target="FestivalSetting",
        details=f"Festival sanasi ko'chirildi: {old_full} -> {new_full} (Admin: {admin_name})",
    )
    return {
        "old_full": old_full,
        "new_full": new_full,
        "display_date": cfg.display_date(),
        "display_day_month": cfg.display_day_month(),
        "display_time": cfg.display_time(),
        "location": cfg.location or "Urganch",
    }


@sync_to_async
def get_categories_list():
    from core.models import Category

    return list(Category.objects.all().order_by("order").values("id", "name", "icon"))


@sync_to_async
def check_phone_exists(phone: str) -> bool:
    from core.models import Participant

    return Participant.objects.filter(phone=phone).exists()


@sync_to_async
def save_bot_application(
    data: dict,
    user_id: int,
    username: str | None,
) -> tuple[bool, str, str]:
    from core.models import Application, Category, Participant, Project, ProjectFile
    from core.telegram import notify_admins_new_application

    full_name_raw = data.get("full_name", "").strip()
    parts = full_name_raw.split()
    if len(parts) >= 3:
        last_name, first_name = parts[0], parts[1]
        middle_name = " ".join(parts[2:])
    elif len(parts) == 2:
        last_name, first_name = parts[0], parts[1]
        middle_name = ""
    else:
        last_name = parts[0] if parts else "Ishtirokchi"
        first_name = parts[0] if parts else "Ishtirokchi"
        middle_name = ""

    b_date_str = data.get("birth_date")
    birth_date = None
    if b_date_str:
        try:
            birth_date = datetime.date.fromisoformat(b_date_str)
        except Exception:
            birth_date = None

    phone = clean_phone_number(data.get("phone", ""))

    existing_part = Participant.objects.filter(phone=phone).first()
    if existing_part and hasattr(existing_part, "application"):
        return (
            False,
            existing_part.application.number,
            f"Bu telefon raqami ({phone}) bilan allaqachon ariza topshirilgan!",
        )

    group_raw = data.get("group_info", "").strip()
    if "," in group_raw:
        g_parts = [p.strip() for p in group_raw.split(",", 1)]
        group, study_direction = g_parts[0], g_parts[1]
    elif "(" in group_raw and ")" in group_raw:
        group = group_raw.split("(")[0].strip()
        study_direction = group_raw.split("(")[1].replace(")", "").strip()
    else:
        group = group_raw or "Litsey o'quvchisi"
        study_direction = "Umumiy ta'lim"

    tg_username = (username or "").lstrip("@")

    try:
        participant, _ = Participant.objects.update_or_create(
            phone=phone,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "middle_name": middle_name,
                "birth_date": birth_date,
                "group": group,
                "study_direction": study_direction,
                "telegram_username": tg_username,
            },
        )
    except Exception as e:
        logger.error("Participant yaratishda xato: %s", e)
        return False, "", f"Ishtirokchini saqlashda xatolik: {e}"

    cat_id = data.get("category_id")
    try:
        category = Category.objects.get(id=cat_id)
    except Exception:
        category = Category.objects.first()

    summary_text = data.get("project_summary", "").strip()
    title_text = data.get("project_title", "").strip()
    link_text = data.get("project_link", "").strip()

    try:
        project, _ = Project.objects.update_or_create(
            participant=participant,
            defaults={
                "category": category,
                "title": title_text,
                "summary": summary_text,
                "problem": summary_text,
                "goal": "Startap g'oyasini litseyda muvaffaqiyatli amalga oshirish",
                "novelty": "Zamonaviy yondashuv va avtomatlashtirish",
                "mechanism": "Dasturiy yoki texnik yechim asosida ishlaydi",
                "future": "Kelgusida rivojlantirish va amaliyotga keng tatbiq etish",
                "link": link_text,
            },
        )
    except Exception as e:
        logger.error("Project yaratishda xato: %s", e)
        return False, "", f"Loyihani saqlashda xatolik: {e}"

    file_meta = data.get("project_file")
    if isinstance(file_meta, dict) and file_meta.get("file_id"):
        try:
            ProjectFile.objects.create(
                project=project,
                kind="presentation",
                telegram_file_id=file_meta["file_id"],
                telegram_file_type=file_meta.get("file_type", "document"),
                original_name=file_meta.get("name", "taqdimot.pdf"),
                file_size=int(file_meta.get("size") or 0),
            )
        except Exception as e:
            logger.warning("ProjectFile saqlashda xatolik: %s", e)

    try:
        app, _ = Application.objects.get_or_create(
            participant=participant,
            defaults={"status": Application.Status.NEW},
        )
    except Exception as e:
        logger.error("Application yaratishda xato: %s", e)
        return False, "", f"Arizani yaratishda xatolik: {e}"

    try:
        notify_admins_new_application(app)
    except Exception as e:
        logger.warning("Adminlarga xabar yuborishda xato: %s", e)

    return True, app.number, "Muvaffaqiyatli saqlandi!"


def is_admin(user_id: int, username: str | None = None) -> bool:
    admin_ids = getattr(settings, "TELEGRAM_ADMIN_IDS", [7647505439, 6150570776])
    if user_id in admin_ids:
        return True

    admin_usernames = getattr(settings, "TELEGRAM_ADMIN_USERNAMES", ["mrbekii", "anvar_sn"])
    if username and username.lower().lstrip("@") in [u.lower() for u in admin_usernames]:
        return True

    from core.models import TelegramAdmin

    return TelegramAdmin.objects.filter(chat_id=user_id, is_active=True).exists()


@sync_to_async
def register_user(chat_id: int, username: str | None, full_name: str) -> bool:
    from core.models import TelegramAdmin, TelegramSubscriber

    is_adm = False
    admin_ids = getattr(settings, "TELEGRAM_ADMIN_IDS", [7647505439, 6150570776])
    admin_usernames = getattr(settings, "TELEGRAM_ADMIN_USERNAMES", ["mrbekii", "anvar_sn"])
    clean_username = (username or "").lower().lstrip("@")

    if chat_id in admin_ids or (clean_username and clean_username in [u.lower() for u in admin_usernames]):
        is_adm = True
        TelegramAdmin.objects.update_or_create(
            chat_id=chat_id,
            defaults={
                "username": clean_username,
                "full_name": full_name or "",
                "is_active": True,
                "notify_on_application": True,
            },
        )
    else:
        is_adm = TelegramAdmin.objects.filter(chat_id=chat_id, is_active=True).exists()

    TelegramSubscriber.objects.update_or_create(
        chat_id=chat_id,
        defaults={
            "username": clean_username,
            "first_name": full_name or "",
        },
    )
    return is_adm


@sync_to_async
def get_stats() -> dict:
    from core.models import Application, Category, Participant

    total_apps = Application.objects.count()
    new_apps = Application.objects.filter(status="new").count()
    review_apps = Application.objects.filter(status="review").count()
    approved_apps = Application.objects.filter(status="approved").count()
    rejected_apps = Application.objects.filter(status="rejected").count()
    total_participants = Participant.objects.count()

    categories_stats = []
    for cat in Category.objects.all().order_by("order"):
        c_count = Application.objects.filter(participant__project__category=cat).count()
        categories_stats.append((cat.name, c_count))

    return {
        "total": total_apps,
        "new": new_apps,
        "review": review_apps,
        "approved": approved_apps,
        "rejected": rejected_apps,
        "participants": total_participants,
        "categories": categories_stats,
    }


@sync_to_async
def find_application(number: str):
    from core.models import Application

    num = number.strip().upper()
    return (
        Application.objects.filter(number=num)
        .select_related("participant", "participant__project", "participant__project__category")
        .first()
    )


@sync_to_async
def get_application_details_with_files(app_id: int):
    from core.models import Application

    app = (
        Application.objects.select_related(
            "participant", "participant__project", "participant__project__category"
        )
        .prefetch_related("participant__project__files")
        .filter(id=app_id)
        .first()
    )
    if not app:
        return None, []
    pr = getattr(app, "participant", None) and getattr(app.participant, "project", None)
    tg_files = []
    if pr:
        for pf in pr.files.all():
            if pf.telegram_file_id:
                tg_files.append(
                    {
                        "file_id": pf.telegram_file_id,
                        "file_type": pf.telegram_file_type or "document",
                        "name": pf.original_name or "taqdimot",
                    }
                )
    return app, tg_files


@sync_to_async
def update_application_status(app_id: int, new_status: str, admin_name: str) -> tuple[bool, str]:
    from core.models import Application, AuditLog

    try:
        app = Application.objects.get(id=app_id)
        old_status = app.get_status_display()
        app.status = new_status
        app.reviewed_by = admin_name
        app.save(update_fields=["status", "reviewed_by", "updated_at"])

        AuditLog.objects.create(
            action=f"tg_{new_status}",
            target=app.number,
            details=f"Status o'zgartirildi: {old_status} -> {app.get_status_display()} (Admin: {admin_name})",
        )
        return True, app.number
    except Exception as e:
        logger.error("Ariza statusini yangilashda xatolik: %s", e)
        return False, str(e)


@sync_to_async
def get_recent_applications(limit=6):
    from core.models import Application

    return list(
        Application.objects.select_related(
            "participant", "participant__project", "participant__project__category"
        ).order_by("-created_at")[:limit]
    )


@sync_to_async
def get_all_subscribers_chat_ids():
    from core.models import TelegramSubscriber

    return list(TelegramSubscriber.objects.values_list("chat_id", flat=True))


@sync_to_async
def get_excel_file():
    from core.excel import generate_applications_excel

    return generate_applications_excel().getvalue()


# ---------------------------------------------------------------------------
# Klaviaturalar
# ---------------------------------------------------------------------------
def get_main_keyboard(is_admin_user: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="📝 Botda ariza topshirish"), KeyboardButton(text="🌐 Saytda ariza topshirish")],
        [KeyboardButton(text="🔍 Ariza holati"), KeyboardButton(text="⏱ 7 daqiqa qoidasi (Pitch)")],
        [KeyboardButton(text="📅 Kun tartibi"), KeyboardButton(text="🎯 7 ta Yo'nalish")],
        [KeyboardButton(text="⚖️ 100 ballik mezonlar"), KeyboardButton(text="🏆 G'oliblarni taqdirlash & Sovrinlar")],
        [KeyboardButton(text="📜 To'liq Nizom"), KeyboardButton(text="📞 Tashkiliy qo'mita")],
    ]
    if is_admin_user:
        buttons.insert(0, [KeyboardButton(text="⚡️ Admin Boshqaruv Paneli")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_admin_inline_keyboard() -> InlineKeyboardMarkup:
    site_url = get_site_url()
    rows = [
        [
            InlineKeyboardButton(text="📊 Statistika", callback_data="admin:stats"),
            InlineKeyboardButton(text="📥 Excel hisobot (.xlsx)", callback_data="admin:excel"),
        ],
        [
            InlineKeyboardButton(text="📑 Oxirgi arizalar", callback_data="admin:recent"),
            InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="admin:broadcast"),
        ],
        [
            InlineKeyboardButton(text="📅 Festival sanasini ko‘chirish", callback_data="admin:change_date"),
        ],
    ]
    if is_valid_public_url(site_url):
        rows.append([InlineKeyboardButton(text="🌐 Saytga o'tish", url=site_url)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_date_shift_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏩ +1 kun", callback_data="date_shift:days:1"),
                InlineKeyboardButton(text="⏩ +3 kun", callback_data="date_shift:days:3"),
                InlineKeyboardButton(text="⏩ +7 kun", callback_data="date_shift:days:7"),
            ],
            [
                InlineKeyboardButton(text="⏩ +14 kun", callback_data="date_shift:days:14"),
                InlineKeyboardButton(text="⏩ +1 oy", callback_data="date_shift:months:1"),
            ],
            [
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin:cancel_date"),
            ],
        ]
    )


def get_after_date_change_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Barcha foydalanuvchilarga yangi sanani e'lon qilish",
                    callback_data="admin:notify_date_change",
                )
            ],
            [
                InlineKeyboardButton(text="📅 Yana o‘zgartirish", callback_data="admin:change_date"),
                InlineKeyboardButton(text="👑 Admin menyu", callback_data="admin:menu"),
            ],
        ]
    )


# ---------------------------------------------------------------------------
# Bot va Dispatcher qurish
# ---------------------------------------------------------------------------
DEFAULT_COMMANDS = [
    BotCommand(command="start", description="🚀 Festival bosh menyusi"),
    BotCommand(command="apply", description="📝 Ariza topshirish (Startap pasporti)"),
    BotCommand(command="status", description="🔍 Ariza holatini tekshirish"),
    BotCommand(command="pitch", description="⏱ 7 daqiqa qoidasi"),
    BotCommand(command="domains", description="🎯 7 ta innovatsion yo‘nalish"),
    BotCommand(command="criteria", description="⚖️ 100 ballik baholash mezonlari"),
    BotCommand(command="schedule", description="📅 Kun tartibi va jadval"),
    BotCommand(command="rules", description="📜 To‘liq Nizom qoidalari"),
    BotCommand(command="help", description="📞 Tashkiliy qo‘mita"),
]


def build_router() -> Router:
    router = Router(name="festival_bot")

    # ---------------- START ----------------
    @router.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext, bot: Bot):
        await state.clear()
        u = message.from_user
        full_name = u.full_name or u.first_name
        is_adm = await register_user(u.id, u.username, full_name)
        f_info = await get_festival_date_info()

        if is_adm:
            try:
                admin_cmds = [
                    BotCommand(command="admin", description="⚡️ Admin Boshqaruv Paneli"),
                    BotCommand(command="setdate", description="📅 Festival sanasini ko‘chirish"),
                    BotCommand(command="stats", description="📊 Festival statistikasi"),
                    BotCommand(command="excel", description="📥 Excel hisobot (.xlsx)"),
                    BotCommand(command="start", description="🚀 Bosh menyu"),
                    BotCommand(command="apply", description="📝 Ariza topshirish"),
                    BotCommand(command="status", description="🔍 Ariza holati"),
                    BotCommand(command="help", description="📞 Tashkiliy qo‘mita"),
                ]
                await bot.set_my_commands(admin_cmds, scope=BotCommandScopeChat(chat_id=u.id))
            except Exception:
                pass

        site_url = get_site_url()
        reg_url = f"{site_url}{reverse('register')}"

        status_note = (
            "👑 <b>Sizning maqomingiz:</b> Tashkiliy qo‘mita mas'uli (Admin)\n"
            "<i>(Siz uchun '⚡️ Admin Boshqaruv Paneli' faollashtirildi)</i>\n"
            if is_adm
            else "🎓 <b>Sizning maqomingiz:</b> Ishtirokchi\n"
            "<i>(Startapingiz pasportini to‘ldiring va festivalda g‘olib bo‘ling!)</i>\n"
        )

        greeting = (
            f"Assalomu alaykum, <b>{full_name}</b>!\n\n"
            f"🏛 <b>Abu Rayhon Beruniy nomidagi Urganch davlat akademik litseyi</b>\n"
            f"🚀 <b>“STARTUP LOYIHALAR FESTIVALI – 2026”</b> rasmiy axborot botiga xush kelibsiz!\n\n"
            f"📅 <b>Festival sanasi:</b> <b>{f_info['display_full']}</b> ({f_info['location']})\n"
            f"{status_note}"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>“Sening bitta g‘oyang — Yangi O‘zbekiston sari bir qadam!”</i>\n\n"
            f"📌 <b>Asosiy qoidalar:</b>\n"
            f"• Ishtirok <b>individual</b> tartibda o'tkaziladi (jamoaviy emas).\n"
            f"• Har bir o'quvchi faqat <b>bitta shaxsiy loyiha</b> taqdim etadi.\n"
            f"• Himoya uchun har bir ishtirokchiga <b>jami 7 daqiqa</b> ajratiladi.\n"
            f"• Baholash <b>100 ballik shkala</b> asosida xolis amalga oshiriladi.\n\n"
            f"Quyidagi tugmalar orqali festival nizomi bilan tanishishingiz yoki arizangizni topshirishingiz mumkin."
        )

        rows = [
            [InlineKeyboardButton(text="📝 Botda ariza topshirish", callback_data="start_apply_now")],
            [InlineKeyboardButton(text="🔍 Ariza holatini tekshirish", callback_data="user:check_status")],
        ]
        if is_valid_public_url(reg_url):
            rows.insert(1, [InlineKeyboardButton(text="🌐 Saytda ariza topshirish", url=reg_url)])
        if is_valid_public_url(site_url):
            rows.append([InlineKeyboardButton(text="🌐 Rasmiy web sayt", url=site_url)])
        inline_kb = InlineKeyboardMarkup(inline_keyboard=rows)

        await message.answer(greeting, reply_markup=get_main_keyboard(is_adm))
        await message.answer("Tezkor amallar:", reply_markup=inline_kb)

    # ---------------- ADMIN PANEL ----------------
    async def _send_admin_panel(target_message: Message):
        f_info = await get_festival_date_info()
        updated_note = f"\n<i>(Oxirgi o‘zgartirish: {f_info['updated_by']})</i>" if f_info.get("updated_by") else ""
        await target_message.answer(
            "👑 <b>STARTUP FESTIVAL – 2026: ADMIN BOSHQARUV PANELI</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 <b>Joriy festival sanasi:</b> <b>{f_info['display_full']}</b> ({f_info['location']}){updated_note}\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Quyidagi tugmalar orqali barcha jarayonlarni boshqaring:",
            reply_markup=get_admin_inline_keyboard(),
        )

    @router.message(F.text == "⚡️ Admin Boshqaruv Paneli")
    @router.message(TgCommand("admin"))
    async def cmd_admin(message: Message, state: FSMContext):
        u = message.from_user
        if not await sync_to_async(is_admin)(u.id, u.username):
            await message.answer(
                "🔒 <b>Kechirasiz, sizda adminlik huquqi mavjud emas.</b>\n"
                "Bu bo‘lim faqat tashkiliy qo‘mita mas'ullari uchun."
            )
            return
        await state.clear()
        await _send_admin_panel(message)

    @router.callback_query(F.data == "admin:menu")
    async def cb_admin_menu(callback: CallbackQuery, state: FSMContext):
        u = callback.from_user
        if not await sync_to_async(is_admin)(u.id, u.username):
            await callback.answer("🔒 Ruxsat yo'q", show_alert=True)
            return
        await state.clear()
        await callback.answer()
        await _send_admin_panel(callback.message)

    # ---------------- FESTIVAL SANASINI KO'CHIRISH (ADMIN) ----------------
    async def _prompt_change_date(target_message: Message, state: FSMContext):
        f_info = await get_festival_date_info()
        await state.set_state(BotStates.waiting_for_festival_date)
        text = (
            "📅 <b>FESTIVAL SANASINI KO‘CHIRISH</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>Hozirgi sana:</b> <b>{f_info['display_full']}</b>\n\n"
            "Yangi sanani kiritishning <b>2 xil usuli</b> bor:\n"
            "1️⃣ Pastdagi <b>tezkor tugmalardan</b> birini bosing (`+1 kun`, `+7 kun`, `+1 oy`...);\n"
            "2️⃣ Yoki yangi sanani chatga yozib yuboring:\n"
            "   • <code>25.12.2026</code> <i>(soat 09:00 saqlanadi)</i>\n"
            "   • <code>25.12.2026 10:30</code> <i>(aniq soat bilan)</i>\n"
            "   • <code>2026-12-25 09:00</code>\n\n"
            "💡 <i>Sana o‘zgartirilishi bilan rasmiy veb-saytdagi taymer, jadval va botdagi barcha ma'lumotlar avtomatik yangilanadi!</i>"
        )
        await target_message.answer(text, reply_markup=get_date_shift_keyboard())

    @router.message(TgCommand("setdate"))
    async def cmd_set_date(message: Message, state: FSMContext):
        u = message.from_user
        if not await sync_to_async(is_admin)(u.id, u.username):
            await message.answer("🔒 Bu buyruq faqat adminlar uchun.")
            return
        await _prompt_change_date(message, state)

    @router.callback_query(F.data == "admin:change_date")
    async def cb_admin_change_date(callback: CallbackQuery, state: FSMContext):
        u = callback.from_user
        if not await sync_to_async(is_admin)(u.id, u.username):
            await callback.answer("🔒 Ruxsat yo'q", show_alert=True)
            return
        await callback.answer()
        await _prompt_change_date(callback.message, state)

    @router.callback_query(F.data == "admin:cancel_date")
    async def cb_admin_cancel_date(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.answer("Bekor qilindi")
        await callback.message.answer(
            "❌ Festival sanasini o‘zgartirish bekor qilindi.",
            reply_markup=get_admin_inline_keyboard(),
        )

    @router.callback_query(F.data.startswith("date_shift:"))
    async def cb_date_shift(callback: CallbackQuery, state: FSMContext):
        u = callback.from_user
        if not await sync_to_async(is_admin)(u.id, u.username):
            await callback.answer("🔒 Ruxsat yo'q", show_alert=True)
            return

        parts = callback.data.split(":")
        unit, amount = parts[1], int(parts[2])
        f_info = await get_festival_date_info()
        cur_dt = f_info["local_dt"]
        if unit == "days":
            new_dt = cur_dt + datetime.timedelta(days=amount)
        else:
            new_dt = shift_datetime_months(cur_dt, amount)

        admin_name = f"@{u.username}" if u.username else (u.full_name or str(u.id))
        res = await update_festival_date_db(new_dt, admin_name)
        await state.clear()
        await callback.answer("✅ Sana ko‘chirildi!")
        await callback.message.answer(
            "✅ <b>FESTIVAL SANASI MUVAFFAQIYATLI KO‘CHIRILDI!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔴 <b>Eski sana:</b> <s>{res['old_full']}</s>\n"
            f"🟢 <b>Yangi sana:</b> <b>{res['new_full']}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🌐 Veb-saytdagi jonli taymer va botdagi barcha sanalar darhol yangilandi!\n\n"
            "Barcha bot foydalanuvchilariga yangi sana haqida xabar yuborasizmi?",
            reply_markup=get_after_date_change_keyboard(),
        )

    @router.message(BotStates.waiting_for_festival_date)
    async def handle_festival_date_text(message: Message, state: FSMContext):
        u = message.from_user
        if not await sync_to_async(is_admin)(u.id, u.username):
            await state.clear()
            return

        raw = (message.text or "").strip()
        if raw in {"❌ Bekor qilish", "/cancel", "Bekor qilish"}:
            await state.clear()
            await message.answer(
                "❌ Festival sanasini o‘zgartirish bekor qilindi.",
                reply_markup=get_main_keyboard(True),
            )
            return

        f_info = await get_festival_date_info()
        new_dt = parse_festival_datetime(raw, f_info["local_dt"])
        if not new_dt:
            await message.answer(
                "⚠️ <b>Sana formati noto‘g‘ri!</b>\n\n"
                "Iltimos, quyidagi formatlardan birida kiriting:\n"
                "• <code>25.12.2026</code>\n"
                "• <code>25.12.2026 10:30</code>\n"
                "• <code>2026-12-25 09:00</code>\n\n"
                "Yoki bekor qilish uchun /cancel yozing.",
                reply_markup=get_date_shift_keyboard(),
            )
            return

        admin_name = f"@{u.username}" if u.username else (u.full_name or str(u.id))
        res = await update_festival_date_db(new_dt, admin_name)
        await state.clear()
        await message.answer(
            "✅ <b>FESTIVAL SANASI MUVAFFAQIYATLI KO‘CHIRILDI!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔴 <b>Eski sana:</b> <s>{res['old_full']}</s>\n"
            f"🟢 <b>Yangi sana:</b> <b>{res['new_full']}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🌐 Veb-saytdagi jonli taymer va botdagi barcha sanalar darhol yangilandi!\n\n"
            "Barcha bot foydalanuvchilariga yangi sana haqida xabar yuborasizmi?",
            reply_markup=get_after_date_change_keyboard(),
        )

    @router.callback_query(F.data == "admin:notify_date_change")
    async def cb_notify_date_change(callback: CallbackQuery, bot: Bot):
        u = callback.from_user
        if not await sync_to_async(is_admin)(u.id, u.username):
            await callback.answer("🔒 Ruxsat yo'q", show_alert=True)
            return

        f_info = await get_festival_date_info()
        sub_ids = await get_all_subscribers_chat_ids()
        await callback.answer("E'lon yuborilmoqda...")

        announcement = (
            "📢 <b>MUHIM E'LON: FESTIVAL SANASI YANGILANDI!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🏛 <b>Urganch davlat akademik litseyi — STARTUP FESTIVALI 2026</b>\n\n"
            f"📅 <b>Yangi sana:</b> <b>{f_info['display_full']}</b>\n"
            f"📍 <b>Manzil:</b> {f_info['location']} (litsey binosi)\n\n"
            "💡 Loyihangiz va taqdimotingizni yangi sanagacha yanada mukammal tayyorlashingiz mumkin!"
        )

        sent_ok = 0
        for cid in sub_ids:
            try:
                await bot.send_message(chat_id=cid, text=announcement)
                sent_ok += 1
                await asyncio.sleep(0.03)
            except Exception:
                pass

        await callback.message.answer(
            f"✅ Yangi sana e'loni yuborildi!\nQabul qildi: <b>{sent_ok} / {len(sub_ids)}</b> nafar foydalanuvchi.",
            reply_markup=get_admin_inline_keyboard(),
        )

    # ---------------- STATISTIKA / EXCEL / OXIRGI ARIZALAR / E'LON ----------------
    @router.message(TgCommand("stats"))
    async def cmd_stats(message: Message):
        u = message.from_user
        if not await sync_to_async(is_admin)(u.id, u.username):
            return
        stats = await get_stats()
        f_info = await get_festival_date_info()
        cat_text = "\n".join([f"  • {c[0]}: <b>{c[1]} ta</b>" for c in stats["categories"]])
        msg = (
            "📊 <b>STARTUP FESTIVALI – 2026 STATISTIKASI</b>\n"
            f"📅 <b>Sana:</b> {f_info['display_full']}\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 <b>Jami ishtirokchilar:</b> {stats['participants']} nafar\n"
            f"📋 <b>Jami arizalar:</b> {stats['total']} ta\n\n"
            f"📌 <b>Holatlar bo'yicha:</b>\n"
            f"  🟢 Tasdiqlangan: <b>{stats['approved']} ta</b>\n"
            f"  🟡 Ko'rib chiqilmoqda: <b>{stats['review']} ta</b>\n"
            f"  🔵 Yangi yuborilgan: <b>{stats['new']} ta</b>\n"
            f"  🔴 Rad etilgan: <b>{stats['rejected']} ta</b>\n\n"
            f"🏷 <b>Yo'nalishlar bo'yicha arizalar:</b>\n{cat_text}\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )
        await message.answer(msg, reply_markup=get_admin_inline_keyboard())

    @router.message(TgCommand("excel"))
    async def cmd_excel(message: Message):
        u = message.from_user
        if not await sync_to_async(is_admin)(u.id, u.username):
            return
        try:
            excel_bytes = await get_excel_file()
            document = BufferedInputFile(excel_bytes, filename="Startup_Festival_2026_Arizalar.xlsx")
            await message.answer_document(
                document,
                caption="📊 <b>Barcha arizalar to'liq ro'yxati (Excel jadval)</b>",
            )
        except Exception as e:
            logger.error("Excel yuborishda xatolik: %s", e)
            await message.answer(f"❌ Excel tayyorlashda xatolik yuz berdi: {e}")

    @router.callback_query(F.data == "admin:stats")
    async def admin_stats_cb(callback: CallbackQuery):
        u = callback.from_user
        if not await sync_to_async(is_admin)(u.id, u.username):
            await callback.answer("🔒 Ruxsat yo'q", show_alert=True)
            return
        stats = await get_stats()
        f_info = await get_festival_date_info()
        cat_text = "\n".join([f"  • {c[0]}: <b>{c[1]} ta</b>" for c in stats["categories"]])

        msg = (
            "📊 <b>STARTUP FESTIVALI – 2026 STATISTIKASI</b>\n"
            f"📅 <b>Sana:</b> {f_info['display_full']}\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 <b>Jami ishtirokchilar:</b> {stats['participants']} nafar\n"
            f"📋 <b>Jami arizalar:</b> {stats['total']} ta\n\n"
            f"📌 <b>Holatlar bo'yicha:</b>\n"
            f"  🟢 Tasdiqlangan: <b>{stats['approved']} ta</b>\n"
            f"  🟡 Ko'rib chiqilmoqda: <b>{stats['review']} ta</b>\n"
            f"  🔵 Yangi yuborilgan: <b>{stats['new']} ta</b>\n"
            f"  🔴 Rad etilgan: <b>{stats['rejected']} ta</b>\n\n"
            f"🏷 <b>Yo'nalishlar bo'yicha arizalar:</b>\n{cat_text}\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )
        await callback.message.answer(msg, reply_markup=get_admin_inline_keyboard())
        await callback.answer()

    @router.callback_query(F.data == "admin:excel")
    async def admin_excel_cb(callback: CallbackQuery):
        u = callback.from_user
        if not await sync_to_async(is_admin)(u.id, u.username):
            await callback.answer("🔒 Ruxsat yo'q", show_alert=True)
            return
        await callback.answer("Excel fayl tayyorlanmoqda...")
        try:
            excel_bytes = await get_excel_file()
            document = BufferedInputFile(excel_bytes, filename="Startup_Festival_2026_Arizalar.xlsx")
            await callback.message.answer_document(
                document,
                caption="📊 <b>Barcha arizalar to'liq ro'yxati (Excel jadval)</b>",
            )
        except Exception as e:
            logger.error("Excel yuborishda xatolik: %s", e)
            await callback.message.answer(f"❌ Excel tayyorlashda xatolik yuz berdi: {e}")

    @router.callback_query(F.data == "admin:recent")
    async def admin_recent_cb(callback: CallbackQuery):
        u = callback.from_user
        if not await sync_to_async(is_admin)(u.id, u.username):
            await callback.answer("🔒 Ruxsat yo'q", show_alert=True)
            return
        recent_apps = await get_recent_applications(limit=6)
        if not recent_apps:
            await callback.message.answer("Hozircha hech qanday ariza kelib tushmagan.")
            await callback.answer()
            return

        text = "📑 <b>SO'NGGI KELIB TUSHGAN ARIZALAR:</b>\n\n"
        keyboard_buttons = []
        for app in recent_apps:
            p = app.participant
            pr = getattr(app, "project", None)
            st_icon = {"new": "🔵", "review": "🟡", "approved": "🟢", "rejected": "🔴"}.get(app.status, "⚪️")
            text += (
                f"{st_icon} <b>{app.number}</b> | {p.last_name} {p.first_name[:1]}.\n"
                f"   💡 {pr.title[:35] if pr else '-'}\n"
                f"   🎓 {p.group} · {app.get_status_display()}\n\n"
            )
            keyboard_buttons.append(
                [InlineKeyboardButton(text=f"Ko'rish: {app.number}", callback_data=f"app:details:{app.id}")]
            )

        kb = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await callback.message.answer(text, reply_markup=kb)
        await callback.answer()

    @router.callback_query(F.data == "admin:broadcast")
    async def admin_broadcast_prompt(callback: CallbackQuery, state: FSMContext):
        u = callback.from_user
        if not await sync_to_async(is_admin)(u.id, u.username):
            await callback.answer("🔒 Ruxsat yo'q", show_alert=True)
            return
        await state.set_state(BotStates.waiting_for_broadcast)
        await callback.message.answer(
            "📢 <b>Barcha bot foydalanuvchilariga e'lon yuborish:</b>\n\n"
            "Iltimos, yubormoqchi bo'lgan xabaringizni yozing.\n"
            "Bekor qilish uchun /cancel deb yozing."
        )
        await callback.answer()

    @router.message(BotStates.waiting_for_broadcast)
    async def handle_broadcast_send(message: Message, state: FSMContext):
        if message.text and message.text.startswith("/cancel"):
            await state.clear()
            await message.answer("E'lon bekor qilindi.")
            return

        sub_ids = await get_all_subscribers_chat_ids()
        sent_ok = 0
        await message.answer(f"⏳ E'lon {len(sub_ids)} nafar foydalanuvchiga yuborilmoqda...")

        for cid in sub_ids:
            try:
                await message.copy_to(chat_id=cid)
                sent_ok += 1
                await asyncio.sleep(0.03)
            except Exception:
                pass

        await state.clear()
        await message.answer(f"✅ E'lon muvaffaqiyatli tarqatildi!\nQabul qildi: <b>{sent_ok} / {len(sub_ids)}</b>")

    # ---------------- ARIZA STATUSI VA FAYLLAR (ADMIN CALLBACK) ----------------
    @router.callback_query(F.data.startswith("app:"))
    async def handle_app_callback(callback: CallbackQuery, bot: Bot):
        parts = callback.data.split(":")
        action = parts[1]
        app_id = int(parts[2])

        u = callback.from_user
        if not await sync_to_async(is_admin)(u.id, u.username):
            await callback.answer("🔒 Ruxsat yo'q", show_alert=True)
            return
        admin_name = f"@{u.username}" if u.username else u.full_name

        if action in ("approved", "rejected", "review"):
            ok, res = await update_application_status(app_id, action, admin_name)
            status_titles = {
                "approved": "✅ TASDIQLANDI",
                "rejected": "❌ RAD ETILDI",
                "review": "⏳ KO'RIB CHIQILMOQDA",
            }
            new_title = status_titles.get(action, action.upper())

            if ok:
                site_url = get_site_url()
                updated_rows = [
                    [
                        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"app:approved:{app_id}"),
                        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"app:rejected:{app_id}"),
                    ],
                    [
                        InlineKeyboardButton(text="⏳ Ko'rib chiqish", callback_data=f"app:review:{app_id}"),
                        InlineKeyboardButton(text="📋 To'liq matn", callback_data=f"app:details:{app_id}"),
                    ],
                ]
                status_full_url = f"{site_url}{reverse('status')}?number={res}"
                if is_valid_public_url(status_full_url):
                    updated_rows.append([InlineKeyboardButton(text="🌐 Saytda ko'rish", url=status_full_url)])
                updated_kb = InlineKeyboardMarkup(inline_keyboard=updated_rows)

                await callback.answer(f"Status yangilandi: {new_title}")
                try:
                    await callback.message.edit_reply_markup(reply_markup=updated_kb)
                except Exception:
                    pass
                await callback.message.reply(
                    f"Ariza <b>{res}</b> holati <b>{new_title}</b>ga o'zgartirildi!\n(Mas'ul: {admin_name})"
                )
            else:
                await callback.answer(f"Xatolik: {res}", show_alert=True)

        elif action == "details":
            app, tg_files = await get_application_details_with_files(app_id)
            if not app:
                await callback.answer("Ariza topilmadi!", show_alert=True)
                return

            p = app.participant
            pr = getattr(app, "project", None)
            detail_text = (
                f"📋 <b>ARIZA TAFSILOTLARI: {app.number}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Ishtirokchi:</b> {p.full_name()}\n"
                f"📞 <b>Telefon:</b> {p.phone}\n"
                f"🎓 <b>Guruh:</b> {p.group} · {p.study_direction}\n"
                f"📊 <b>Holati:</b> {app.get_status_display()}\n\n"
                f"💡 <b>Loyiha nomi:</b> {pr.title if pr else '-'}\n"
                f"🏷 <b>Yo'nalish:</b> {pr.category.name if pr and pr.category else '-'}\n\n"
                f"🎯 <b>Maqsadi:</b>\n{pr.goal if pr else '-'}\n\n"
                f"⚠️ <b>Muammo:</b>\n{pr.problem if pr else '-'}\n\n"
                f"✨ <b>Yangilik va afzalligi:</b>\n{pr.novelty if pr else '-'}\n\n"
                f"⚙️ <b>Ishlash mexanizmi:</b>\n{pr.mechanism if pr else '-'}\n\n"
                f"🚀 <b>Kelajak istiqboli:</b>\n{pr.future if pr else '-'}\n"
            )
            if pr and pr.link:
                detail_text += f"\n🔗 <b>Havola:</b> {pr.link}"

            kb_rows = []
            if tg_files:
                kb_rows.append(
                    [InlineKeyboardButton(text="📎 Taqdimot faylini ko‘rish", callback_data=f"app:file:{app_id}")]
                )

            await callback.message.answer(
                detail_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows) if kb_rows else None,
            )
            await callback.answer()

        elif action == "file":
            app, tg_files = await get_application_details_with_files(app_id)
            if not app or not tg_files:
                await callback.answer("Telegram fayli topilmadi.", show_alert=True)
                return
            await callback.answer("Fayl yuborilmoqda...")
            for fitem in tg_files:
                try:
                    caption = f"📎 <b>{app.number}</b> — {fitem['name']}"
                    if fitem["file_type"] == "photo":
                        await bot.send_photo(callback.message.chat.id, fitem["file_id"], caption=caption)
                    else:
                        await bot.send_document(callback.message.chat.id, fitem["file_id"], caption=caption)
                except Exception as e:
                    logger.warning("Faylni yuborib bo'lmadi: %s", e)

    # ---------------- NIZOM ASOSIDAGI TUGMALAR ----------------
    @router.message(F.text.in_({"⏱ 7 daqiqa qoidasi (Pitch)", "7 daqiqa", "/pitch"}))
    async def handle_pitch_rule(message: Message):
        text = (
            "⏱ <b>LOYIHANI HIMOYASI — 7 DAQIQALIK TARTIB:</b>\n"
            "<i>(Nizomning 8-bandi talabi)</i>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "⏳ Har bir ishtirokchiga loyiha himoyasi uchun jami <b>7 daqiqa</b> ajratiladi:\n\n"
            "1️⃣ <b>2 daqiqa — Tanishuv va G'oya</b>\n"
            "   Ishtirokchi o'zini tanishtiradi, loyiha g'oyasi, uning maqsadi va qaysi dolzarb muammoni hal etishini qisqa bayon qiladi.\n\n"
            "2️⃣ <b>3 daqiqa — Prototip / MVP namoyishi</b>\n"
            "   Loyiha ishlash jarayoni, dastur kodi, elektronika sxemasi, tayyor maket yoki amaliy natija jonli namoyish etiladi.\n\n"
            "3️⃣ <b>2 daqiqa — Savol-javob</b>\n"
            "   Hakamlar hay'ati a'zolarining texnik va amaliy savollariga mustaqil hamda ilmiy asoslangan javob berish.\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 <i>Eslatma: Amaliy prototip yoki ishlaydigan namuna mavjudligi baholashda eng katta ustunlik beradi!</i>"
        )
        await message.answer(text)

    @router.message(F.text.in_({"📅 Kun tartibi", "/schedule"}))
    async def handle_schedule(message: Message):
        f_info = await get_festival_date_info()
        text = (
            f"📅 <b>FESTIVAL KUNIDAGI VAQT JADVALI ({f_info['display_date']}):</b>\n"
            "<i>(Nizomning 7-bandi namunaviy dasturi)</i>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 <b>Sana va boshlanish:</b> <b>{f_info['display_full']}</b> ({f_info['location']})\n\n"
            "⏰ <b>09:00 – 09:30</b> — Ishtirokchilarni ro'yxatga olish va stendlarga joylashtirish\n"
            "⏰ <b>09:30 – 09:45</b> — Festivalning tantanali ochilishi\n"
            "⏰ <b>09:45 – 10:00</b> — Shartlar va baholash mezonlari bilan tanishtirish\n"
            "⏰ <b>10:00 – 11:00</b> — Startup loyihalar ko'rgazmasi va dastlabki tanishuv\n"
            "⏰ <b>11:00 – 12:30</b> — Ishtirokchilarning individual loyiha himoyasi (7 daqiqalik pitch)\n"
            "⏰ <b>12:30 – 13:00</b> — Hakamlar hay'ati tomonidan yakuniy baholash\n"
            "⏰ <b>13:00 – 13:30</b> — Natijalarni e'lon qilish va g'oliblarni taqdirlash\n"
            "⏰ <b>13:30 – 13:45</b> — Festivalning yopilishi va suratga tushish\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )
        await message.answer(text)

    @router.message(F.text.in_({"🎯 7 ta Yo'nalish", "/domains", "/yonalishlar"}))
    async def handle_domains_btn(message: Message):
        text = (
            "🎯 <b>FESTIVALNING 7 TA YO'NALISHI:</b>\n"
            "<i>(Nizomning 4-bandi)</i>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "1. 💻 <b>IT va dasturlash</b>\n"
            "   Veb-saytlar, mobil ilovalar, dasturiy mahsulotlar va axborot tizimlari.\n\n"
            "2. 🤖 <b>Sun’iy intellekt</b>\n"
            "   AI yordamchilari, ma’lumotlarni tahlil qilish, tasvir va matn bilan ishlash yechimlari.\n\n"
            "3. 🦾 <b>Robototexnika va elektronika</b>\n"
            "   Robotlar, Arduino, ESP32, aqlli qurilmalar va avtomatlashtirish.\n\n"
            "4. 📚 <b>Ta’lim texnologiyalari</b>\n"
            "   Elektron ta’lim platformalari, interaktiv darsliklar va o‘quv vositalari.\n\n"
            "5. 🌿 <b>Ekologiya va yashil texnologiyalar</b>\n"
            "   Energiya tejash, chiqindilarni qayta ishlash va ekologik yechimlar.\n\n"
            "6. 🤝 <b>Ijtimoiy innovatsiyalar</b>\n"
            "   Ta’lim, sog‘liqni saqlash, xavfsizlik va jamiyatdagi muammolarga yechimlar.\n\n"
            "7. 💼 <b>Biznes va tadbirkorlik</b>\n"
            "   Yangi mahsulotlar, xizmatlar, biznes g‘oyalar va daromad modellari.\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )
        await message.answer(text)

    @router.message(F.text.in_({"⚖️ 100 ballik mezonlar", "/criteria", "/mezonlar"}))
    async def handle_criteria_btn(message: Message):
        text = (
            "⚖️ <b>BAHOLASH MEZONLARI (JAMI 100 BALL):</b>\n"
            "<i>(Nizomning 9-bandi rasmiy jadvali)</i>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ <b>Loyihaning yangiligi va innovatsionligi:</b> 20 ball\n"
            "2️⃣ <b>Muammoning dolzarbligi:</b> 15 ball\n"
            "3️⃣ <b>Amaliy ahamiyati:</b> 20 ball\n"
            "4️⃣ <b>Ishlaydigan prototip yoki namoyish mavjudligi:</b> 15 ball\n"
            "5️⃣ <b>Texnik bajarilishi va ishlash sifati:</b> 10 ball\n"
            "6️⃣ <b>Taqdimot va himoya qilish mahorati:</b> 10 ball\n"
            "7️⃣ <b>Kelajakdagi rivojlanish imkoniyati:</b> 10 ball\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🏆 <b>JAMI: 100 BALL</b>\n\n"
            "⚖️ <i>Hakamlar hay'ati litsey rahbariyati, fan o'qituvchilari va soha mutaxassislaridan iborat bo'ladi.</i>"
        )
        await message.answer(text)

    @router.message(F.text.in_({"🏆 G'oliblarni taqdirlash & Sovrinlar", "🏆 Sovrinli o'rinlar", "/sovrinlar"}))
    async def handle_prizes_and_noms(message: Message):
        text = (
            "🏆 <b>G'OLIBLARNI TAQDIRLASH VA SOVRINLAR JAMG'ARMASI:</b>\n"
            "<i>(Nizomning 10-bandi)</i>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Festival yakunida hakamlar hay'atining 100 ballik baholash natijalariga ko‘ra eng yuqori natija qayd etgan 3 ta eng kuchli startap loyihasi taqdirlanadi:\n\n"
            "🥇 <b>I o‘rin (Oltin / Bosh sovrin)</b>\n"
            "🎁 <b>Qimmatbaho Bosh Sovrin</b>\n"
            "• 1-darajali Diplom va maxsus kubok\n"
            "• Loyihani amaliyotga tatbiq etish va inkubatsiya ko‘magi\n\n"
            "🥈 <b>II o‘rin (Kumush sovrindor)</b>\n"
            "🎁 <b>Qimmatbaho maxsus sovg‘a</b>\n"
            "• 2-darajali Diplom va statuetka\n"
            "• Respublika miqyosidagi tanlovlarga tavsiya\n\n"
            "🥉 <b>III o‘rin (Bronza sovrindor)</b>\n"
            "🎁 <b>Maxsus sovg‘alar to‘plami</b>\n"
            "• 3-darajali Diplom va sertifikat\n"
            "• Homiylar va litsey esdalik sovg‘alari\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "ℹ️ <i>Taqdirlash marosimi festival yakunida litseyning faollar zalida tantanali tarzda o‘tkaziladi.</i>"
        )
        await message.answer(text)

    @router.message(F.text.in_({"📜 To'liq Nizom", "/rules", "/nizom"}))
    async def handle_full_rules(message: Message):
        text = (
            "📜 <b>FESTIVAL O'TKAZISH TARTIBI (NIZOMI):</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "<b>1. Umumiy qoidalar:</b> Litseyda startap madaniyatini shakllantirish, faqat individual ishtirok.\n"
            "<b>2. Ishtirok shartlari:</b> Litseyning barcha o'quvchilari qatnasha oladi. 1 o'quvchi — 1 shaxsiy loyiha. Plagiat taqiqlanadi.\n"
            "<b>3. Loyiha talablari:</b> Maqsad, muammo, yangilik, mexanizm, kelajak rejasi, taqdimot va prototip.\n"
            "<b>4. Bosqichlar:</b> Qabul -> Tayyorlash -> Ko'rgazma -> 7 daqiqalik himoya -> Baholash -> Taqdirlash.\n"
            "<b>5. Himoya:</b> 2 daqiqa tanishtiruv + 3 daqiqa prototip namoyishi + 2 daqiqa savol-javob.\n"
            "<b>6. Baholash:</b> 7 ta mezon asosida 100 ballik shkala.\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Batafsil ma'lumot saytimizda joylashtirilgan."
        )
        await message.answer(text)

    @router.message(F.text == "🔍 Ariza holati")
    @router.message(TgCommand("status"))
    @router.callback_query(F.data == "user:check_status")
    async def prompt_check_status(event: Message | CallbackQuery, state: FSMContext):
        await state.set_state(BotStates.waiting_for_app_number)
        text = (
            "🔍 <b>Ariza holatini tekshirish</b>\n\n"
            "Iltimos, arizangiz raqamini kiriting (masalan: <code>SLF26-00001</code>):"
        )
        if isinstance(event, CallbackQuery):
            await event.message.answer(text)
            await event.answer()
        else:
            await event.answer(text)

    @router.message(BotStates.waiting_for_app_number)
    async def process_app_number(message: Message, state: FSMContext | None = None):
        num = (message.text or "").strip().upper()
        app = await find_application(num)
        if state is not None:
            await state.clear()

        if not app:
            await message.answer(
                f"❌ <b>{num}</b> raqamli ariza topilmadi.\n\n"
                "Iltimos, ariza raqamingiz to‘g‘riligini tekshiring yoki qayta urinib ko‘ring."
            )
            return

        st_colors = {
            "new": ("🔵 Yangi qabul qilingan", "Arizangiz ekspertlarimiz tomonidan dastlabki ko‘rib chiqish navbatida."),
            "review": ("🟡 Ko'rib chiqilmoqda", "Arizangiz hakamlar hay'ati ekspertizasiga topshirilgan."),
            "approved": ("🟢 TASDIQLANGAN", "Tabriklaymiz! Loyihangiz saralashdan o‘tib, festival final bosqichiga tavsiya etildi."),
            "rejected": ("🔴 Rad etilgan", "Loyiha belgilangan mezonlarga to'liq mos kelmaganligi sababli qabul qilinmadi."),
        }
        status_title, status_desc = st_colors.get(app.status, (app.get_status_display(), ""))
        pr = getattr(app, "project", None)

        resp_text = (
            f"📋 <b>ARIZA PASPORTI: {app.number}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Ishtirokchi:</b> {app.participant.last_name} {app.participant.first_name}\n"
            f"🎓 <b>Guruh:</b> {app.participant.group}\n"
            f"💡 <b>Loyiha:</b> {pr.title if pr else '-'}\n"
            f"🏷 <b>Yo'nalish:</b> {pr.category.name if pr and pr.category else '-'}\n\n"
            f"📊 <b>Joriy holati:</b> <b>{status_title}</b>\n"
            f"ℹ️ {status_desc}\n\n"
            f"🕒 <b>Yuborilgan vaqt:</b> {app.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        )
        if app.admin_notes:
            resp_text += f"\n💬 <b>Hakamlar izohi:</b> <i>{app.admin_notes}</i>\n"

        site_url = get_site_url()
        status_full_url = f"{site_url}{reverse('status')}?number={app.number}"
        if is_valid_public_url(status_full_url):
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🌐 Saytda to'liq ko'rish", url=status_full_url)]]
            )
            await message.answer(resp_text, reply_markup=kb)
        else:
            await message.answer(resp_text)

    @router.message(F.text.regexp(r"^SLF26-\d{5}$"))
    async def quick_status_check(message: Message, state: FSMContext):
        await process_app_number(message, state)

    # ---------------- BEKOR QILISH ----------------
    @router.message(F.text.in_({"❌ Bekor qilish", "/cancel", "Bekor qilish"}))
    async def handle_cancel(message: Message, state: FSMContext):
        await state.clear()
        u = message.from_user
        is_adm = await sync_to_async(is_admin)(u.id, u.username)
        await message.answer(
            "❌ Amaliyot bekor qilindi. Bosh menyudasiz.",
            reply_markup=get_main_keyboard(is_adm),
        )

    # ---------------- SAYTDA ARIZA TOPSHIRISH ----------------
    @router.message(F.text.in_({"🌐 Saytda ariza topshirish", "🚀 Ariza topshirish (Web)", "/web"}))
    async def handle_apply_web(message: Message):
        site_url = get_site_url()
        reg_url = f"{site_url}{reverse('register')}"
        kb_rows = [[InlineKeyboardButton(text="📝 Botda to'ldirish", callback_data="start_apply_now")]]
        if is_valid_public_url(reg_url):
            kb_rows.insert(0, [InlineKeyboardButton(text="🌐 Saytda to'ldirish (Web)", url=reg_url)])

        await message.answer(
            "🚀 <b>ARIZA TOPSHIRISH IMKONIYATLARI:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Siz festivalda ishtirok etish uchun arizangizni <b>2 xil qulay usulda</b> topshirishingiz mumkin:\n\n"
            "1️⃣ <b>Bot orqali:</b> Shu yerning o‘zida savollarga javob berib, 2 daqiqada ariza yuborish;\n"
            "2️⃣ <b>Rasmiy veb-sayt orqali:</b> Kompyuter yoki brauzerda pasport rasmiylashtirish.\n\n"
            f"🌐 Sayt manzili: <code>{reg_url}</code>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
        )

    # ---------------- BOT ORQALI ARIZA TOPSHIRISH (FSM WIZARD) ----------------
    @router.message(F.text.in_({"📝 Botda ariza topshirish", "📝 Bot orqali ariza topshirish", "/apply", "/ariza", "/register"}))
    @router.callback_query(F.data == "start_apply_now")
    async def start_apply_flow(event: Message | CallbackQuery, state: FSMContext):
        await state.clear()
        await state.set_state(ApplyStates.full_name)

        cancel_kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
            resize_keyboard=True,
        )
        msg_text = (
            "📝 <b>STARTAP LOYIHALAR FESTIVALI – 2026</b>\n"
            "<i>Arizani Telegram bot orqali rasmiylashtirish</i>\n\n"
            "Arizani to‘ldirish atigi 2-3 daqiqa vaqt oladi.\n"
            "Jarayonni istalgan payt to‘xtatish uchun pastdagi <b>«❌ Bekor qilish»</b> tugmasini bosishingiz mumkin.\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>1-QADAM: Familiya, Ism va Sharifingiz</b>\n\n"
            "Iltimos, to‘liq F.I.SH ni kiriting:\n"
            "<i>Misol: Berdiyev Jasur Otabek o‘g‘li</i>"
        )
        if isinstance(event, CallbackQuery):
            await event.message.answer(msg_text, reply_markup=cancel_kb)
            await event.answer()
        else:
            await event.answer(msg_text, reply_markup=cancel_kb)

    @router.message(ApplyStates.full_name)
    async def process_apply_full_name(message: Message, state: FSMContext):
        text = (message.text or "").strip()
        if text in {"❌ Bekor qilish", "/cancel", "Bekor qilish"}:
            return await handle_cancel(message, state)

        if len(text.split()) < 2:
            await message.answer(
                "⚠️ Iltimos, kamida Familiya va Ismingizni to‘liq kiriting:\n"
                "<i>Misol: Berdiyev Jasur Otabek o‘g‘li</i>"
            )
            return

        await state.update_data(full_name=text)
        await state.set_state(ApplyStates.birth_date)
        skip_kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="⏭ O‘tkazib yuborish")],
                [KeyboardButton(text="❌ Bekor qilish")],
            ],
            resize_keyboard=True,
        )
        await message.answer(
            f"Tushunarli, <b>{text}</b>!\n\n"
            "📅 <b>2-QADAM: Tug‘ilgan sana (Ixtiyoriy)</b>\n"
            "Tug‘ilgan kuningiz, oyingiz va yilingizni kiriting (yoki pastdagi <b>«⏭ O‘tkazib yuborish»</b> tugmasini bosing):\n"
            "<i>Misol: 15.04.2008 yoki 2008-04-15</i>",
            reply_markup=skip_kb,
        )

    @router.message(ApplyStates.birth_date)
    async def process_apply_birth_date(message: Message, state: FSMContext):
        text = (message.text or "").strip()
        if text in {"❌ Bekor qilish", "/cancel", "Bekor qilish"}:
            return await handle_cancel(message, state)

        if text in {"⏭ O‘tkazib yuborish", "O'tkazib yuborish", "Keyingisi", "/skip"}:
            parsed_date = None
        else:
            parsed_date = parse_date_input(text)
            if not parsed_date:
                await message.answer(
                    "⚠️ Sanani to‘g‘ri formatda kiriting (kun.oy.yil) yoki <b>«⏭ O‘tkazib yuborish»</b> tugmasini bosing:\n"
                    "<i>Misol: 15.04.2008 yoki 2008-04-15</i>"
                )
                return

        await state.update_data(birth_date=parsed_date)
        await state.set_state(ApplyStates.phone)

        phone_kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)],
                [KeyboardButton(text="❌ Bekor qilish")],
            ],
            resize_keyboard=True,
        )
        await message.answer(
            "📱 <b>3-QADAM: Bog‘lanish uchun telefon raqami (Asosiy / Majburiy)</b>\n\n"
            "Pastdagi <b>«📱 Raqamni yuborish»</b> tugmasini bosing yoki telefon raqamingizni yozing:\n"
            "<i>Misol: +998901234567</i>",
            reply_markup=phone_kb,
        )

    @router.message(ApplyStates.phone)
    async def process_apply_phone(message: Message, state: FSMContext):
        if message.text in {"❌ Bekor qilish", "/cancel", "Bekor qilish"}:
            return await handle_cancel(message, state)

        phone_raw = message.contact.phone_number if message.contact else (message.text or "").strip()
        phone = clean_phone_number(phone_raw)
        if len(re.sub(r"\D", "", phone)) < 9:
            await message.answer(
                "⚠️ Iltimos, to‘g‘ri telefon raqam kiriting:\n"
                "<i>Misol: +998901234567</i>"
            )
            return

        if await check_phone_exists(phone):
            u = message.from_user
            is_adm = await sync_to_async(is_admin)(u.id, u.username)
            await state.clear()
            await message.answer(
                f"⚠️ <b>{phone}</b> raqami bilan allaqachon ariza topshirilgan!\n\n"
                "Arizangiz holatini tekshirish uchun <b>«🔍 Ariza holati»</b> tugmasidan foydalanishingiz mumkin.",
                reply_markup=get_main_keyboard(is_adm),
            )
            return

        await state.update_data(phone=phone)
        await state.set_state(ApplyStates.group_info)

        skip_group_kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="⏭ O‘tkazib yuborish")],
                [KeyboardButton(text="❌ Bekor qilish")],
            ],
            resize_keyboard=True,
        )
        await message.answer(
            "🎓 <b>4-QADAM: Litsey guruhi va yo‘nalishingiz (Ixtiyoriy)</b>\n\n"
            "Guruh raqami yoki yo‘nalishingizni yozing (yoki <b>«⏭ O‘tkazib yuborish»</b> tugmasini bosing):\n"
            "<i>Misol: 24-01 guruhi (Aniq fanlar)</i>",
            reply_markup=skip_group_kb,
        )

    @router.message(ApplyStates.group_info)
    async def process_apply_group(message: Message, state: FSMContext):
        text = (message.text or "").strip()
        if text in {"❌ Bekor qilish", "/cancel", "Bekor qilish"}:
            return await handle_cancel(message, state)

        group_val = "" if text in {"⏭ O‘tkazib yuborish", "O'tkazib yuborish", "Keyingisi", "/skip"} else text
        await state.update_data(group_info=group_val)
        await state.set_state(ApplyStates.category)

        categories = await get_categories_list()
        inline_buttons = [
            [InlineKeyboardButton(text=f"🎯 {cat['name']}", callback_data=f"cat_select:{cat['id']}")]
            for cat in categories
        ]
        await message.answer(
            "🎯 <b>5-QADAM: Startap loyihangiz yo‘nalishi</b>\n\n"
            "Loyihangiz qaysi soha yoki yo‘nalishga mansub? Quyidagilardan birini tanlang:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_buttons),
        )

    @router.callback_query(ApplyStates.category, F.data.startswith("cat_select:"))
    async def process_apply_category_cb(callback: CallbackQuery, state: FSMContext):
        cat_id = int(callback.data.split(":")[1])
        categories = await get_categories_list()
        selected_cat = next((c for c in categories if c["id"] == cat_id), None)
        cat_name = selected_cat["name"] if selected_cat else "Umumiy yo'nalish"

        await state.update_data(category_id=cat_id, category_name=cat_name)
        await state.set_state(ApplyStates.project_title)
        await callback.answer(f"Tanlandi: {cat_name}")

        await callback.message.answer(
            f"🏷 <b>Tanlangan yo‘nalish:</b> {cat_name}\n\n"
            "💡 <b>6-QADAM: Startap loyihangizning to‘liq nomi</b>\n\n"
            "Startapingiz nomini kiriting:\n"
            "<i>Misol: SmartEdu — Litsey o‘quvchilari uchun sun'iy intellektga asoslangan adaptiv ta’lim tizimi</i>"
        )

    @router.message(ApplyStates.project_title)
    async def process_apply_project_title(message: Message, state: FSMContext):
        text = (message.text or "").strip()
        if text in {"❌ Bekor qilish", "/cancel", "Bekor qilish"}:
            return await handle_cancel(message, state)

        if len(text) < 3:
            await message.answer("⚠️ Iltimos, loyihangiz nomini to‘liqroq yozing (kamida 3 ta belgi):")
            return

        await state.update_data(project_title=text)
        await state.set_state(ApplyStates.project_summary)
        skip_sum_kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="⏭ O‘tkazib yuborish")],
                [KeyboardButton(text="❌ Bekor qilish")],
            ],
            resize_keyboard=True,
        )
        await message.answer(
            f"Ajoyib nom: <b>{text}</b>!\n\n"
            "📝 <b>7-QADAM: Loyihaning qisqacha tavsifi (Ixtiyoriy)</b>\n\n"
            "Loyihangiz haqida ma’lumot bering (muammo, g‘oya, afzallik) yoki <b>«⏭ O‘tkazib yuborish»</b> tugmasini bosing:\n"
            "<i>(Barchasini bitta xabarda yozishingiz mumkin)</i>",
            reply_markup=skip_sum_kb,
        )

    @router.message(ApplyStates.project_summary)
    async def process_apply_project_summary(message: Message, state: FSMContext):
        text = (message.text or "").strip()
        if text in {"❌ Bekor qilish", "/cancel", "Bekor qilish"}:
            return await handle_cancel(message, state)

        summary_val = "" if text in {"⏭ O‘tkazib yuborish", "O'tkazib yuborish", "Keyingisi", "/skip"} else text
        await state.update_data(project_summary=summary_val)
        await state.set_state(ApplyStates.project_link)

        skip_kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="⏭ O‘tkazib yuborish")],
                [KeyboardButton(text="❌ Bekor qilish")],
            ],
            resize_keyboard=True,
        )
        await message.answer(
            "🔗 <b>8-QADAM: Loyiha havolasi (Ixtiyoriy)</b>\n\n"
            "Startapingizning veb-sayti, GitHub ombori, demo video (YouTube) yoki Google Drive havolasi bormi?\n\n"
            "Agar havola bo‘lsa, yuboring.\n"
            "Agar hozircha havola bo‘lmasa, pastdagi <b>«⏭ O‘tkazib yuborish»</b> tugmasini bosing:",
            reply_markup=skip_kb,
        )

    @router.message(ApplyStates.project_link)
    async def process_apply_project_link(message: Message, state: FSMContext):
        text = (message.text or "").strip()
        if text in {"❌ Bekor qilish", "/cancel", "Bekor qilish"}:
            return await handle_cancel(message, state)

        link = "" if text in {"⏭ O‘tkazib yuborish", "O'tkazib yuborish", "/skip"} else text
        await state.update_data(project_link=link)
        await state.set_state(ApplyStates.project_file)

        cancel_kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
            resize_keyboard=True,
        )
        await message.answer(
            "📎 <b>9-QADAM: Loyiha taqdimot slaydi (Majburiy)</b>\n\n"
            "Loyihangizning taqdimot slaydi faylini (PDF yoki PPTX) hujjat sifatida jo‘nating.\n"
            "<i>(Himoya jarayonida hakamlar hay’atiga ushbu slayd orqali loyihangizni namoyish qilasiz)</i>",
            reply_markup=cancel_kb,
        )

    @router.message(ApplyStates.project_file)
    async def process_apply_project_file(message: Message, state: FSMContext):
        if (message.text or "") in {"❌ Bekor qilish", "/cancel", "Bekor qilish"}:
            return await handle_cancel(message, state)

        if not message.document and not message.photo:
            await message.answer(
                "⚠️ <b>Loyiha taqdimot slaydi (PDF yoki PPTX) yuklanishi majburiy!</b>\n\n"
                "Iltimos, taqdimot faylingizni Telegram orqali yuboring (fayl yoki slayd rasmi):"
            )
            return

        if message.document:
            fname = message.document.file_name or "taqdimot.pdf"
            fsize = int(message.document.file_size or 0)
            file_meta = {
                "file_id": message.document.file_id,
                "file_type": "document",
                "name": fname,
                "size": fsize,
            }
            file_info_text = f"📄 {fname} ({round(fsize / 1024)} KB)"
        else:
            photo = message.photo[-1]
            fsize = int(photo.file_size or 0)
            file_meta = {
                "file_id": photo.file_id,
                "file_type": "photo",
                "name": "taqdimot_slayd.jpg",
                "size": fsize,
            }
            file_info_text = "🖼 Taqdimot slayd rasmi"

        await state.update_data(project_file=file_meta)
        await state.set_state(ApplyStates.confirm)
        data = await state.get_data()

        summary_msg = (
            "📋 <b>ARIZA MA’LUMOTLARINI TEKSHIRING VA TASDIQLANG:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Ishtirokchi:</b> <b>{data.get('full_name')}</b>\n"
            f"📅 <b>Tug‘ilgan sana:</b> {data.get('birth_date') or 'Ko‘rsatilmagan'}\n"
            f"📱 <b>Telefon:</b> <code>{data.get('phone')}</code>\n"
            f"🎓 <b>Litsey guruhi:</b> {data.get('group_info') or 'Ko‘rsatilmagan'}\n"
            f"🏷 <b>Yo‘nalish:</b> {data.get('category_name')}\n\n"
            f"💡 <b>Startap nomi:</b> <b>{data.get('project_title')}</b>\n"
            f"📝 <b>Qisqacha tavsif:</b> {data.get('project_summary', '')[:250]}{'...' if len(data.get('project_summary', '')) > 250 else ''}\n"
            f"🔗 <b>Havola:</b> {data.get('project_link') or 'Ko‘rsatilmagan'}\n"
            f"📎 <b>Biriktirilgan fayl:</b> {file_info_text}\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Barcha ma’lumotlar to‘g‘rimi? Arizani topshirishni tasdiqlaysizmi?"
        )

        confirm_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Tasdiqlash va Yuborish", callback_data="apply:confirm")],
                [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="apply:cancel")],
            ]
        )
        await message.answer(summary_msg, reply_markup=confirm_kb)

    @router.callback_query(ApplyStates.confirm, F.data == "apply:confirm")
    async def confirm_apply_callback(callback: CallbackQuery, state: FSMContext):
        await callback.answer("Ariza bazaga saqlanmoqda...")
        data = await state.get_data()
        u = callback.from_user

        ok, app_number, msg = await save_bot_application(data, u.id, u.username)
        await state.clear()
        is_adm = await sync_to_async(is_admin)(u.id, u.username)

        if not ok:
            await callback.message.answer(
                f"❌ <b>Arizani saqlashda xatolik yuz berdi:</b>\n{msg}",
                reply_markup=get_main_keyboard(is_adm),
            )
            return

        f_info = await get_festival_date_info()
        site_url = get_site_url()
        status_url = f"{site_url}{reverse('status')}?number={app_number}"

        success_text = (
            "🎉 <b>TABRIKLAYMIZ! ARIZANGIZ MUVAFFAQIYATLI QABUL QILINDI!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <b>Ariza raqamingiz:</b> <code>{app_number}</code>\n"
            f"👤 <b>Ishtirokchi:</b> {data.get('full_name')}\n"
            f"💡 <b>Startap:</b> {data.get('project_title')}\n"
            f"🏷 <b>Yo‘nalish:</b> {data.get('category_name')}\n"
            f"📊 <b>Boshlang‘ich holati:</b> 🔵 Qabul qilindi (Ko'rib chiqilmoqda)\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📌 <b>MUHIM ESLATMALAR:</b>\n"
            f"• Arizangiz holatini istalgan payt <b>«🔍 Ariza holati»</b> tugmasi orqali yoki <code>{app_number}</code> deb yozib tekshirishingiz mumkin.\n"
            f"• Festival <b>{f_info['display_full']}</b> kuni Urganch davlat akademik litseyi binosida bo‘lib o‘tadi.\n"
            "• Himoya uchun har bir ishtirokchiga <b>jami 7 daqiqa</b> (2 daqiqa tanishtiruv + 3 daqiqa namoyish + 2 daqiqa savol-javob) beriladi.\n\n"
            "<i>Sizga festivalda muvaffaqiyat va yuksak g‘alabalar tilaymiz!</i>"
        )

        kb_rows = []
        if is_valid_public_url(status_url):
            kb_rows.append([InlineKeyboardButton(text="🌐 Saytda ariza pasportini ko'rish", url=status_url)])

        await callback.message.answer(
            success_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows) if kb_rows else None,
        )
        await callback.message.answer("Asosiy menyu:", reply_markup=get_main_keyboard(is_adm))

    @router.callback_query(ApplyStates.confirm, F.data == "apply:cancel")
    async def cancel_apply_callback(callback: CallbackQuery, state: FSMContext):
        u = callback.from_user
        await state.clear()
        is_adm = await sync_to_async(is_admin)(u.id, u.username)
        await callback.answer("Ariza bekor qilindi.")
        await callback.message.answer(
            "❌ Ariza bekor qilindi. Bosh menyudasiz.",
            reply_markup=get_main_keyboard(is_adm),
        )

    @router.message(F.text.in_({"📞 Tashkiliy qo'mita", "/help", "/contact"}))
    async def handle_contact_btn(message: Message):
        text = (
            "📞 <b>FESTIVAL TASHKILIY QO‘MITASI:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🏛 <b>Muassasa:</b> Abu Rayhon Beruniy nomidagi Urganch davlat akademik litseyi\n\n"
            "👨‍💻 <b>Mas’ul tashkilotchilar:</b>\n"
            "  • Behruz — @mrbekii (+998 97 091 67 89)\n"
            "  • Anvar — @anvar_sn\n\n"
            "🤖 <b>Rasmiy bot:</b> @UrDU_startup_bot\n"
            "📍 <b>Manzil:</b> Xorazm viloyati, Urganch shahri"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💬 @mrbekii bilan bog'lanish", url="https://t.me/mrbekii")],
                [InlineKeyboardButton(text="💬 @anvar_sn bilan bog'lanish", url="https://t.me/anvar_sn")],
            ]
        )
        await message.answer(text, reply_markup=kb)

    return router


def create_bot(token: str | None = None) -> Bot:
    bot_token = token or getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    return Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=DjangoORMStorage())
    dp.include_router(build_router())
    return dp


# ---------------------------------------------------------------------------
# Webhook va Polling ishga tushirish nuqtalari
# ---------------------------------------------------------------------------
async def process_webhook_update(payload: dict) -> None:
    """Vercel / Django Webhook so'rovini qayta ishlaydi."""
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not token:
        return
    bot = create_bot(token)
    dp = create_dispatcher()
    try:
        update = Update.model_validate(payload, context={"bot": bot})
        await dp.feed_update(bot, update)
    finally:
        await bot.session.close()


async def setup_telegram_webhook(webhook_url: str) -> dict:
    """Telegram webhook va buyruqlarini o'rnatadi."""
    bot = create_bot()
    try:
        await asyncio.wait_for(
            bot.set_webhook(
                url=webhook_url,
                secret_token=get_webhook_secret(),
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=False,
            ),
            timeout=15.0,
        )
        try:
            await asyncio.wait_for(
                bot.set_my_commands(DEFAULT_COMMANDS, scope=BotCommandScopeDefault()),
                timeout=12.0,
            )
        except Exception:
            logger.warning("Bot buyruqlarini yuklashda xatolik", exc_info=True)
        info = await asyncio.wait_for(bot.get_webhook_info(), timeout=10.0)
        return {
            "ok": True,
            "url": info.url,
            "pending_update_count": info.pending_update_count,
            "last_error_message": info.last_error_message,
        }
    finally:
        await bot.session.close()


async def run_polling_bot(token: str) -> None:
    """Lokal ishga tushirish uchun polling rejimi."""
    bot = create_bot(token)
    dp = create_dispatcher()
    try:
        try:
            await bot.set_my_commands(DEFAULT_COMMANDS, scope=BotCommandScopeDefault())
        except Exception as e:
            logger.warning("Bot buyruqlarini o'rnatishda xatolik: %s", e)
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        await bot.session.close()
