import random
import re
from django import forms
from .models import Participant, Project
from .validators import file_validator


class StyledMixin:
    def style(self):
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-select"
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = "form-control form-textarea"
            else:
                widget.attrs["class"] = "form-control"


class ParticipantForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Participant
        fields = [
            "last_name",
            "first_name",
            "middle_name",
            "birth_date",
            "phone",
            "telegram_username",
            "email",
            "group",
            "study_direction"
        ]
        widgets = {
            "last_name": forms.TextInput(attrs={"placeholder": "Masalan: Karimov"}),
            "first_name": forms.TextInput(attrs={"placeholder": "Masalan: Sardor"}),
            "middle_name": forms.TextInput(attrs={"placeholder": "Masalan: Rustam o'g'li"}),
            "birth_date": forms.DateInput(attrs={"type": "date"}),
            "phone": forms.TextInput(attrs={"placeholder": "+998 90 123 45 67", "inputmode": "tel", "id": "id_phone"}),
            "telegram_username": forms.TextInput(attrs={"placeholder": "@username"}),
            "email": forms.EmailInput(attrs={"placeholder": "pochta@litsey.uz (ixtiyoriy)"}),
            "group": forms.TextInput(attrs={"placeholder": "Masalan: 214-guruh"}),
            "study_direction": forms.TextInput(attrs={"placeholder": "Masalan: Aniq fanlar (IT & Dasturlash)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style()

    def clean_phone(self):
        raw = self.cleaned_data.get("phone", "")
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 9:
            digits = "998" + digits
        if not (len(digits) == 12 and digits.startswith("998")):
            raise forms.ValidationError("Telefon raqamini to'g'ri formatda kiriting: +998 (XX) XXX-XX-XX")
        return "+" + digits

    def clean_telegram_username(self):
        uname = self.cleaned_data.get("telegram_username", "").strip()
        if uname:
            uname = uname.lstrip("@").strip()
            if not re.match(r"^[a-zA-Z0-9_]{4,32}$", uname):
                raise forms.ValidationError("Telegram usernameni to'g'ri kiriting (masalan: @username)")
        return uname


class ProjectForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Project
        fields = ["title", "category", "summary", "problem", "goal", "novelty", "mechanism", "future"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Loyihangizning rasmiy nomi"}),
            "summary": forms.Textarea(attrs={"rows": 3, "placeholder": "Loyihaning asosiy mazmuni 2-3 jumlada..."}),
            "problem": forms.Textarea(attrs={"rows": 3, "placeholder": "Loyiha jamiyatdagi qaysi aniq muammoni bartaraf etadi?"}),
            "goal": forms.Textarea(attrs={"rows": 3, "placeholder": "Loyihaning asosiy maqsadi va kutilayotgan natijalar..."}),
            "novelty": forms.Textarea(attrs={"rows": 3, "placeholder": "Mavjud muqobillardan farqi, o'ziga xosligi va ustun jihatlari..."}),
            "mechanism": forms.Textarea(attrs={"rows": 3, "placeholder": "Texnik jihatdan qanday ishlaydi? Qanday texnologiyalar ishlatilgan?"}),
            "future": forms.Textarea(attrs={"rows": 3, "placeholder": "Kelgusida loyihani qanday kengaytirish va tijoratlashtirish rejalashtirilgan?"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style()
        self.fields["category"].empty_label = "— Yo'nalishni tanlang —"


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(d, initial) for d in data if d]
        return [single_clean(data, initial)] if data else []


class FilesForm(StyledMixin, forms.Form):
    presentation = forms.FileField(
        label="Loyiha taqdimoti / slaydi (PDF yoki PPTX, 15 MB gacha)",
        required=True,
        validators=[file_validator(["pdf", "pptx"], 15)],
        help_text="Loyihangizning asosiy slayd taqdimoti (7 daqiqalik himoya uchun)",
        widget=forms.FileInput(attrs={"accept": ".pdf,.pptx"}),
        error_messages={"required": "Loyiha taqdimoti (slayd) faylini yuklash majburiy."}
    )
    document = forms.FileField(
        label="Loyiha to'liq pasporti / hujjati (PDF yoki DOCX — ixtiyoriy)",
        required=False,
        validators=[file_validator(["pdf", "docx"], 10)],
        help_text="Loyiha tavsifi, hisob-kitoblar va texnik xususiyatlar (ixtiyoriy)",
        widget=forms.FileInput(attrs={"accept": ".pdf,.docx"})
    )
    images = MultipleFileField(
        label="Prototip yoki dizayn rasmlari (JPG, PNG, WEBP — ixtiyoriy)",
        required=False,
        validators=[file_validator(["jpg", "jpeg", "png", "webp"], 5)],
        help_text="Sxema, 3D model, interfeys yoki tayyor qurilma suratlari (ko‘pi bilan 5 ta)",
        widget=MultipleFileInput(attrs={"accept": ".jpg,.jpeg,.png,.webp"})
    )
    video = forms.FileField(
        label="Demo video rolik (MP4 yoki WEBM, 50 MB gacha — ixtiyoriy)",
        required=False,
        validators=[file_validator(["mp4", "webm"], 50)],
        help_text="Qurilma yoki ilovaning ishlash jarayonidan qisqa rolik (ixtiyoriy)",
        widget=forms.FileInput(attrs={"accept": ".mp4,.webm"})
    )
    link = forms.URLField(
        label="Loyiha havolasi (GitHub, veb-sayt, Figma va h.k. — ixtiyoriy)",
        required=False,
        widget=forms.URLInput(attrs={"placeholder": "https://github.com/foydalanuvchi/loyiha"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style()

    def clean_images(self):
        imgs = self.cleaned_data.get("images", [])
        if len(imgs) > 5:
            raise forms.ValidationError("Ko'pi bilan 5 ta rasm yuklash mumkin.")
        return imgs


class SecurityForm(StyledMixin, forms.Form):
    consent = forms.BooleanField(
        label="Men taqdim etgan barcha ma'lumotlar to'g'riligini, loyiha shaxsiy muallifligim ostida yaratilganligini va festivalning individual ishtirok etish qoidalariga to'liq roziligimni tasdiqlayman.",
        error_messages={"required": "Davom etish uchun festival shartlariga rozilik bildirishingiz shart."}
    )
    captcha = forms.IntegerField(
        label="Robot emasligingizni tasdiqlang",
        widget=forms.NumberInput(attrs={"placeholder": "Javobni kiriting"})
    )
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"})
    )

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.style()
        self.request = request
        self.fields["website"].widget.attrs["class"] = "hp-field"

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam bot aniqlandi.")

    def clean_captcha(self):
        ans = self.cleaned_data.get("captcha")
        sess_ans = self.request.session.get("captcha_answer") if self.request else None
        if ans != sess_ans:
            raise forms.ValidationError("Matematik savolga noto'g'ri javob berildi. Qayta hisoblang.")
        return ans

    def new_captcha(self):
        a = random.randint(3, 16)
        b = random.randint(2, 14)
        if self.request:
            self.request.session["captcha_answer"] = a + b
        self.fields["captcha"].label = f"Xavfsizlik tekshiruvi: {a} + {b} = ?"
        self.data = self.data.copy() if self.is_bound else self.data
