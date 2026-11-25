import datetime
import os
import uuid
from zoneinfo import ZoneInfo
from django.conf import settings
from django.db import models
from django.utils import timezone


UZ_MONTHS = {
    1: "Yanvar",
    2: "Fevral",
    3: "Mart",
    4: "Aprel",
    5: "May",
    6: "Iyun",
    7: "Iyul",
    8: "Avgust",
    9: "Sentabr",
    10: "Oktabr",
    11: "Noyabr",
    12: "Dekabr",
}


def get_tashkent_tz():
    try:
        return ZoneInfo(getattr(settings, "TIME_ZONE", "Asia/Tashkent"))
    except Exception:
        return datetime.timezone(datetime.timedelta(hours=5))


def default_festival_date():
    raw = getattr(settings, "FESTIVAL_DATE", "2026-11-19T09:00:00+05:00")
    try:
        dt = datetime.datetime.fromisoformat(raw)
        if timezone.is_naive(dt):
            dt = dt.replace(tzinfo=get_tashkent_tz())
        return dt
    except Exception:
        return datetime.datetime(2026, 11, 19, 9, 0, tzinfo=get_tashkent_tz())


class FestivalSetting(models.Model):
    """Festival sanasi va umumiy sozlamalari (bot admin paneli va sayt uchun yagona manba)."""

    festival_date = models.DateTimeField("Festival sanasi va vaqti", default=default_festival_date)
    location = models.CharField("O'tkazilish joyi", max_length=160, default="Urganch")
    updated_by = models.CharField("Oxirgi o'zgartirgan", max_length=128, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Festival sozlamasi"
        verbose_name_plural = "Festival sozlamalari"

    @classmethod
    def get_solo(cls) -> "FestivalSetting":
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "festival_date": default_festival_date(),
                "location": "Urganch",
            },
        )
        return obj

    def local_dt(self) -> datetime.datetime:
        dt = self.festival_date
        tz = get_tashkent_tz()
        if timezone.is_naive(dt):
            return dt.replace(tzinfo=tz)
        return dt.astimezone(tz)

    def iso_date(self) -> str:
        return self.local_dt().isoformat()

    def display_date(self) -> str:
        dt = self.local_dt()
        month = UZ_MONTHS.get(dt.month, str(dt.month))
        return f"{dt.day}-{month}, {dt.year}"

    def display_day_month(self) -> str:
        dt = self.local_dt()
        month = UZ_MONTHS.get(dt.month, str(dt.month)).lower()
        return f"{dt.day}-{month}"

    def display_time(self) -> str:
        return self.local_dt().strftime("%H:%M")

    def display_full(self) -> str:
        return f"{self.display_date()} · soat {self.display_time()}"

    def __str__(self):
        return f"Festival: {self.display_full()} ({self.location})"


class TelegramFSMState(models.Model):
    """Vercel serverless muhiti uchun PostgreSQL asosidagi aiogram FSM xotirasi."""

    key = models.CharField(max_length=180, primary_key=True)
    state = models.CharField(max_length=180, null=True, blank=True)
    data = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Bot holati (FSM)"
        verbose_name_plural = "Bot holatlari (FSM)"

    def __str__(self):
        return f"{self.key} -> {self.state or 'idle'}"


class Category(models.Model):
    name = models.CharField("Nomi", max_length=120, unique=True)
    icon = models.CharField("Ikonka (FontAwesome klassi)", max_length=60, default="fa-solid fa-microchip")
    description = models.TextField("Tavsif", blank=True)
    examples = models.CharField("Loyiha misollari", max_length=255, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Yo'nalish"
        verbose_name_plural = "Yo'nalishlar"

    def __str__(self):
        return self.name


class Participant(models.Model):
    first_name = models.CharField("Ism", max_length=60)
    last_name = models.CharField("Familiya", max_length=60)
    middle_name = models.CharField("Sharifi", max_length=60, blank=True, default="")
    birth_date = models.DateField("Tug'ilgan sana", null=True, blank=True)
    phone = models.CharField(
        "Telefon raqami",
        max_length=25,
        unique=True,
        error_messages={"unique": "Bu telefon raqami bilan ariza allaqachon yuborilgan."}
    )
    email = models.EmailField("Elektron pochta", blank=True, default="")
    group = models.CharField("Guruh raqami", max_length=30, blank=True, default="")
    study_direction = models.CharField("Ta'lim yo'nalishi", max_length=120, blank=True, default="")
    telegram_username = models.CharField("Telegram username", max_length=60, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ishtirokchi"
        verbose_name_plural = "Ishtirokchilar"

    def full_name(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}".strip()

    def __str__(self):
        return self.full_name()


class Project(models.Model):
    participant = models.OneToOneField(Participant, on_delete=models.CASCADE, related_name="project")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name="Yo'nalish")
    title = models.CharField("Loyiha nomi", max_length=220)
    summary = models.TextField("Loyihaning qisqacha tavsifi", max_length=1500, blank=True, default="")
    problem = models.TextField("Qaysi muammoni hal qiladi?", max_length=1500, blank=True, default="")
    goal = models.TextField("Loyihaning maqsadi", max_length=1500, blank=True, default="")
    novelty = models.TextField("Loyihaning yangiligi va afzalliklari", max_length=1500, blank=True, default="")
    mechanism = models.TextField("Loyihaning ishlash mexanizmi", max_length=1500, blank=True, default="")
    future = models.TextField("Kelajakdagi rivojlanish imkoniyatlari", max_length=1500, blank=True, default="")
    link = models.URLField("Loyiha uchun havola (GitHub, demo, va h.k.)", blank=True, default="")

    class Meta:
        verbose_name = "Loyiha"
        verbose_name_plural = "Loyihalar"

    def __str__(self):
        return self.title


class Application(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Yangi yuborilgan"
        REVIEW = "review", "Ko'rib chiqilmoqda"
        APPROVED = "approved", "Tasdiqlangan"
        REJECTED = "rejected", "Rad etilgan"

    number = models.CharField(max_length=20, unique=True, null=True, editable=False)
    participant = models.OneToOneField(Participant, on_delete=models.CASCADE, related_name="application")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW)
    admin_notes = models.TextField("Hakamlar / Tashkilotchi xulosasi", blank=True)
    score = models.PositiveSmallIntegerField("Hakamlar bali (100 ballik tizim)", null=True, blank=True)
    reviewed_by = models.CharField("Ko'rib chiqqan shaxs", max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Ariza"
        verbose_name_plural = "Arizalar"

    @property
    def project(self):
        return getattr(self.participant, "project", None)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.number:
            self.number = f"SLF26-{self.pk:05d}"
            super().save(update_fields=["number"])

    def __str__(self):
        return self.number or "-"


def upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"projects/{instance.project_id}/{uuid.uuid4().hex}{ext}"


class ProjectFile(models.Model):
    class Kind(models.TextChoices):
        PRESENTATION = "presentation", "Taqdimot"
        DOCUMENT = "document", "Hujjat"
        IMAGE = "image", "Prototip rasmi"
        VIDEO = "video", "Demo video"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="files")
    kind = models.CharField(max_length=15, choices=Kind.choices)
    file = models.FileField(upload_to=upload_path, blank=True, null=True)
    telegram_file_id = models.CharField("Telegram file_id", max_length=255, blank=True, default="")
    telegram_file_type = models.CharField("Telegram fayl turi", max_length=20, blank=True, default="")
    original_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(default=0, help_text="Baytlarda")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Loyiha fayli"
        verbose_name_plural = "Loyiha fayllari"

    def save(self, *args, **kwargs):
        if self.file and not self.original_name:
            self.original_name = os.path.basename(self.file.name)
        if self.file and not self.file_size:
            try:
                self.file_size = self.file.size
            except Exception:
                pass
        super().save(*args, **kwargs)


class TelegramAdmin(models.Model):
    chat_id = models.BigIntegerField("Telegram Chat ID", unique=True)
    username = models.CharField("Telegram Username", max_length=64, blank=True)
    full_name = models.CharField("F.I.SH", max_length=128, blank=True)
    notify_on_application = models.BooleanField("Yangi arizalardan xabardor qilish", default=True)
    is_active = models.BooleanField("Faol", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Telegram Admin"
        verbose_name_plural = "Telegram Adminlar"

    def __str__(self):
        u = f"@{self.username}" if self.username else str(self.chat_id)
        return f"{self.full_name or 'Admin'} ({u})"


class TelegramSubscriber(models.Model):
    chat_id = models.BigIntegerField("Telegram Chat ID", unique=True)
    username = models.CharField("Telegram Username", max_length=64, blank=True)
    first_name = models.CharField("Ism", max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Telegram Foydalanuvchi"
        verbose_name_plural = "Telegram Foydalanuvchilar"

    def __str__(self):
        return f"{self.first_name} ({self.chat_id})"


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=60)
    target = models.CharField(max_length=200, blank=True)
    details = models.TextField(blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Audit yozuvi"
        verbose_name_plural = "Audit jurnali"

    def __str__(self):
        return f"{self.action} -> {self.target} ({self.created_at:%Y-%m-%d %H:%M})"
