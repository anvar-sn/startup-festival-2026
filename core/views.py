import hmac
import io
import json
import logging
import qrcode
from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.management import call_command
from django.db import transaction
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .excel import generate_applications_excel
from .forms import FilesForm, ParticipantForm, ProjectForm, SecurityForm
from .models import Application, AuditLog, Category, FestivalSetting, ProjectFile
from .telegram import notify_admins_new_application

logger = logging.getLogger(__name__)

# Nizom 9-bandi: Baholash mezonlari (100 ball)
CRITERIA = [
    {
        "id": "c1",
        "name": "Loyihaning yangiligi va innovatsionligi",
        "max": 20,
        "desc": "G'oyaning yangiligi, mavjud yechimlardan farqi, ijodiy va noodatiy yondashuv darajasi."
    },
    {
        "id": "c2",
        "name": "Muammoning dolzarbligi",
        "max": 15,
        "desc": "Loyiha jamiyat, litsey yoki sohadagi aniq va real muammoni hal etishga qaratilganligi."
    },
    {
        "id": "c3",
        "name": "Amaliy ahamiyati",
        "max": 20,
        "desc": "Loyihani amalda qo'llash imkoniyati, maqsadli foydalanuvchilar doirasi va hayotiyligi."
    },
    {
        "id": "c4",
        "name": "Ishlaydigan prototip yoki namoyish mavjudligi",
        "max": 15,
        "desc": "Qurilma, ishchi dastur, veb-sayt, sxema, 3D maket yoki amaliy namoyish etish namunasi."
    },
    {
        "id": "c5",
        "name": "Texnik bajarilishi va ishlash sifati",
        "max": 10,
        "desc": "Dastur kodi, elektronika sxemasi yoki texnik arxitekturaning to'g'ri va xavfsiz tuzilganligi."
    },
    {
        "id": "c6",
        "name": "Taqdimot va himoya qilish mahorati",
        "max": 10,
        "desc": "Muallifning 7 daqiqa ichida o'z g'oyasini ravon, ishonarli yetkazishi va savollarga aniq javob berishi."
    },
    {
        "id": "c7",
        "name": "Kelajakdagi rivojlanish imkoniyati",
        "max": 10,
        "desc": "Loyihaning masshtablashuvi, kelgusi rejalari va yangi bosqichdagi tanlovlarga chiqish salohiyati."
    },
]

# Nizom 7-bandi: Festival kunidagi namunaviy vaqt jadvali
SCHEDULE = [
    {"time": "09:00 – 09:30", "title": "Ro'yxatga olish & joylashtirish", "icon": "fa-solid fa-id-card-clip", "desc": "Ishtirokchilar kelishi, ro'yxatdan o'tishi va o'z stendlariga joylashishi"},
    {"time": "09:30 – 09:45", "title": "Festivalning tantanali ochilishi", "icon": "fa-solid fa-flag-checkered", "desc": "Litsey rahbariyati va tashkiliy qo'mita tabrigi"},
    {"time": "09:45 – 10:00", "title": "Shartlar va mezonlar bilan tanishtirish", "icon": "fa-solid fa-circle-info", "desc": "Hakamlar hay'atini tanishtirish va 7 daqiqalik tartibni eslatish"},
    {"time": "10:00 – 11:00", "title": "Startup loyihalar ko'rgazmasi", "icon": "fa-solid fa-store", "desc": "Barcha stendlarda prototiplar va ishlanmalar bilan dastlabki tanishuv"},
    {"time": "11:00 – 12:30", "title": "Individual loyihalar himoyasi (Pitching)", "icon": "fa-solid fa-microphone-lines", "desc": "Har bir ishtirokchiga 7 daqiqa: 2 daqiqa taqdimot, 3 daqiqa demo, 2 daqiqa savol-javob"},
    {"time": "12:30 – 13:00", "title": "Hakamlar hay'ati yakuniy baholashi", "icon": "fa-solid fa-calculator", "desc": "Ballarni umumlashtirish, baholash varaqalarini jamlash va g'oliblarni aniqlash"},
    {"time": "13:00 – 13:30", "title": "Natijalarni e'lon qilish & Taqdirlash", "icon": "fa-solid fa-trophy", "desc": "Festival g'oliblarini (I, II, III o'rinlar) tantanali taqdirlash va sovg'alarni topshirish"},
    {"time": "13:30 – 13:45", "title": "Festivalning yopilishi", "icon": "fa-solid fa-camera", "desc": "Esdalik uchun umumiy suratga tushish va xulosa"}
]

# Nizom 8-bandi: 7 daqiqalik himoya qoidasi
PITCH_RULES = [
    {"min": "2 daqiqa", "title": "Tanishuv & Muammo", "desc": "Muallif o'zini tanishtiradi, loyiha g'oyasi va qaysi dolzarb muammoni hal etishini qisqa bayon qiladi.", "pct": 28, "color": "var(--primary)"},
    {"min": "3 daqiqa", "title": "Prototip & MVP namoyishi", "desc": "Loyiha amalda qanday ishlashi ko'rsatiladi: dastur kodlari, qurilma, datchiklar yoki jonli ishchi namuna.", "pct": 43, "color": "var(--accent-emerald)"},
    {"min": "2 daqiqa", "title": "Hakamlar savol-javobi", "desc": "Hakamlar hay'ati a'zolarining texnik va amaliy savollariga mustaqil javob berish.", "pct": 29, "color": "var(--accent-gold)"}
]

def home(request):
    categories = Category.objects.all().order_by("order")
    total_apps = Application.objects.count()

    context = {
        "categories": categories,
        "criteria": CRITERIA,
        "schedule": SCHEDULE,
        "pitch_rules": PITCH_RULES,
        "total_apps": total_apps,
    }
    return render(request, "core/home.html", context)


def register(request):
    kw = dict(request=request)
    if request.method == "POST":
        pf = ParticipantForm(request.POST, prefix="p")
        prf = ProjectForm(request.POST, prefix="pr")
        ff = FilesForm(request.POST, request.FILES, prefix="f")
        sf = SecurityForm(request.POST, **kw)

        if all([pf.is_valid(), prf.is_valid(), ff.is_valid(), sf.is_valid()]):
            with transaction.atomic():
                participant = pf.save()
                project = prf.save(commit=False)
                project.participant = participant
                project.link = ff.cleaned_data["link"]
                project.save()

                cd = ff.cleaned_data
                items = []
                if cd.get("presentation"):
                    items.append(("presentation", cd["presentation"]))
                if cd.get("document"):
                    items.append(("document", cd["document"]))
                if cd.get("images"):
                    items += [("image", i) for i in cd["images"] if i]
                if cd.get("video"):
                    items.append(("video", cd["video"]))

                for kind, f in items:
                    ProjectFile.objects.create(
                        project=project,
                        kind=kind,
                        file=f,
                        original_name=getattr(f, "name", ""),
                        file_size=getattr(f, "size", 0)
                    )

                app = Application.objects.create(participant=participant)
                AuditLog.objects.create(
                    action="ariza_yuborildi",
                    target=app.number,
                    details=f"Yangi ariza: {participant.full_name()} ({project.title})",
                    ip=request.META.get("REMOTE_ADDR")
                )

            # Telegram bot orqali adminlarga inline tugmali xabar yuborish
            try:
                notify_admins_new_application(app)
            except Exception as e:
                logger.error("Adminlarga bildirishnoma yuborilmadi: %s", e)

            request.session.pop("captcha_answer", None)
            return redirect("success", number=app.number)
    else:
        pf = ParticipantForm(prefix="p")
        prf = ProjectForm(prefix="pr")
        ff = FilesForm(prefix="f")
        sf = SecurityForm(**kw)

    sf.new_captcha()
    sf.data = {}
    return render(request, "core/register.html", {"pf": pf, "prf": prf, "ff": ff, "sf": sf})


def success(request, number):
    app = get_object_or_404(
        Application.objects.select_related("participant", "participant__project", "participant__project__category"),
        number=number
    )
    return render(request, "core/success.html", {"app": app})


def status(request):
    app = None
    number = (request.GET.get("number") or "").strip().upper()
    if number:
        app = Application.objects.select_related(
            "participant", "participant__project", "participant__project__category"
        ).prefetch_related("participant__project__files").filter(number=number).first()
        if not app:
            messages.error(request, f"'{number}' raqamli ariza tizimda topilmadi. Raqamni tekshirib qayta kiriting.")

    return render(request, "core/status.html", {"app": app, "number": number})


def qr(request, number):
    if not Application.objects.filter(number=number).exists():
        raise Http404

    site_url = getattr(settings, "SITE_URL", "http://localhost:8000").rstrip("/")
    url = f"{site_url}{reverse('status')}?number={number}"
    
    qr_img = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr_img.add_data(url)
    qr_img.make(fit=True)
    img = qr_img.make_image(fill_color="#0F172A", back_color="#FFFFFF")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return HttpResponse(buf.getvalue(), content_type="image/png")


@staff_member_required
def export_excel_view(request):
    """Adminlar uchun barcha arizalarni Excel shaklida yuklab berish."""
    excel_io = generate_applications_excel()
    response = HttpResponse(
        excel_io.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="Startup_Festival_2026_Arizalar.xlsx"'
    return response


@csrf_exempt
def health_check(request):
    """Yengil sog'liq tekshiruvi (Vercel va monitoring uchun)."""
    is_vercel = bool(getattr(settings, "IS_VERCEL", False))
    festival_date = getattr(settings, "FESTIVAL_DATE", "")
    db_ok = True
    try:
        cfg = FestivalSetting.get_solo()
        festival_date = cfg.display_full()
    except Exception:
        db_ok = False
    return JsonResponse(
        {
            "status": "ok",
            "app": "Startup Festivali 2026",
            "platform": "vercel" if is_vercel else "server",
            "db_ok": db_ok,
            "festival_date": festival_date,
        }
    )


@csrf_exempt
def telegram_webhook(request):
    """Telegram Bot Webhook qabul qiluvchi endpoint (Vercel serverless uchun)."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "detail": "Method not allowed"}, status=405)

    from core.bot_engine import get_webhook_secret, process_webhook_update

    expected = get_webhook_secret()
    provided = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not provided or not hmac.compare_digest(provided, expected):
        return JsonResponse({"ok": False, "detail": "Invalid webhook secret"}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": True})

    try:
        async_to_sync(process_webhook_update)(payload)
    except Exception:
        logger.exception("Telegram webhook update qayta ishlashda xatolik")
    return JsonResponse({"ok": True})


@csrf_exempt
def setup_telegram_webhook_view(request):
    """Bir marta bosishda Neon DB migratsiyasini yuritadi va Telegram Webhook'ni ulaydi."""
    expected_key = getattr(settings, "SECRET_KEY", "")
    provided_key = request.GET.get("key") or request.headers.get("X-Setup-Key", "")
    if not provided_key or not expected_key or not hmac.compare_digest(provided_key, expected_key):
        return JsonResponse({"ok": False, "detail": "Invalid setup key"}, status=403)

    migrated = False
    migrate_err = None
    try:
        call_command("migrate", "--noinput", verbosity=0)
        migrated = True
    except Exception as exc:
        migrate_err = str(exc)
        logger.exception("Migratsiyada xatolik")

    host = request.headers.get("x-forwarded-host") or request.get_host()
    if host and "localhost" not in host.lower() and "127.0.0.1" not in host:
        webhook_url = f"https://{host}/telegram/webhook/"
    else:
        site_url = getattr(settings, "SITE_URL", "").rstrip("/")
        webhook_url = f"{site_url}/telegram/webhook/"

    from core.bot_engine import setup_telegram_webhook

    tg_result = {}
    try:
        tg_result = async_to_sync(setup_telegram_webhook)(webhook_url)
    except Exception as exc:
        tg_result = {"ok": False, "error": str(exc)}

    festival_date = ""
    try:
        festival_date = FestivalSetting.get_solo().display_full()
    except Exception:
        pass

    return JsonResponse(
        {
            "ok": bool(tg_result.get("ok")),
            "migrated": migrated,
            "migrate_error": migrate_err,
            "webhook_url": webhook_url,
            "festival_date": festival_date,
            "platform": "vercel" if getattr(settings, "IS_VERCEL", False) else "server",
            "telegram": tg_result,
        }
    )
