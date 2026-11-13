# STARTUP LOYIHALAR FESTIVALI – 2026
**Abu Rayhon Beruniy nomidagi Urganch davlat akademik litseyi**

> *“Sening bitta g‘oyang — Yangi O‘zbekiston sari bir qadam!”*

Neo-Heritage & Tech Elegance dizayn tizimi, to‘liq moslashuvchan (Tun/Kun rejimi, milliy Xorazm-Beruniy geometrik naqshlari), Django 5.x backend, rasmiy Telegram bot (@UrDU_startup_bot) va hakamlar boshqaruv paneli.

---

## 🌟 Asosiy Imkoniyatlar

1. **Neo-Heritage & Tech Elegance Dizayni:**
   - 🌗 **Tun / Kun rejimi (Dark & Light Mode):** Bir bosishda almashinuvchi va foydalanuvchi tanlovini eslab qoluvchi zamonaviy mavzu.
   - 🏛 **Xorazm-Beruniy Girih naqshlari:** Sun'iylikdan xoli, akademik litsey nufuziga mos sof SVG geometrik naqsh va astrolyabiya vizuali.
   - ⏱ **Real-time Countdown:** 2026-yil 19-noyabrga qolgan vaqtni soniyagacha hisoblovchi animatsion taymer.
   - 📱 **100% Responsive:** Smartfon, planshet va noutbuklarda ideal ko'rinish.

2. **Mukammal Ariza va Ro‘yxatdan O‘tish Tizimi:**
   - 4 bosqichli qulay shakl (Shaxsiy ma'lumotlar, Loyiha pasporti, Fayllar, Tasdiqlash).
   - Telefon raqami uchun dinamik maska (`+998 (XX) XXX-XX-XX`).
   - Drag & Drop fayl yuklash, rasm previewsi (oldindan ko'rish) va belgilar sanagichi.
   - Arifmetik captcha va honeypot anti-spam himoyasi.
   - Avtomatik ariza raqami (`SLF26-00001`) va dinamik **QR-kod**.
   - Muvaffaqiyat sahifasida arizani chop etish yoki PDF sifatida saqlash imkoniyati.

3. **Telegram Bot (@UrDU_startup_bot) Integratsiyasi:**
   - **Adminlar:** `@mrbekii` (ID: `7647505439`) va `@anvar_sn`.
   - **Avtomatik bildirishnoma:** Saytdan yangi ariza kelishi bilan bot orqali adminlarga inline tugmalar (`[✅ Tasdiqlash]`, `[❌ Rad etish]`, `[⏳ Ko'rib chiqish]`) bilan xabar yuboriladi.
   - **O'quvchilar uchun:** `/start` orqali festival haqida to'liq ma'lumot, 7 ta yo'nalish, mezonlar, sovg'alar va `SLF26-XXXXX` raqami orqali ariza holatini tekshirish.
   - **Admin paneli (`/admin`):** Statistika, so'nggi arizalar, barcha arizalarni **Excel (.xlsx)** formatida yuklab olish va e'lon tarqatish (broadcast).

4. **Hakamlar va Tashkiliy Qo‘mita Boshqaruvi:**
   - Django Admin (`/admin/`): Barcha arizalarni filtrlash, qidirish, hakamlar bahosi (0-100) va xulosalarini yozish.
   - Bitta tugma orqali barcha arizalarni formatlangan chiroyli **Excel jadval (.xlsx)** ga eksport qilish (`/export-excel/`).

---

## 🚀 Ishga Tushirish Qo‘llanmasi

### 1. Docker orqali (Tavsiya etiladi - Web + DB + Bot)
```bash
# 1. Sozlamalarni tekshiring
cp .env.example .env

# 2. Konteynerlarni yig'ish va ishga tushirish
docker compose up -d --build

# 3. Migratsiyalarni o'tkazish
docker compose exec web python manage.py migrate

# 4. Superuser (Admin) yaratish
docker compose exec web python manage.py createsuperuser
```
* Veb-sayt: http://localhost:8000
* Django Admin: http://localhost:8000/admin/
* Bot: Orqa fonda avtomatik ishlaydi!

---

### 2. Lokal Kompyuterda Ishga Tushirish (SQLite bilan test)
```bash
# PowerShell (Windows):
$env:DEBUG="1"; $env:DB_ENGINE="sqlite"

# Kutubxonalarni o'rnatish
pip install -r requirements.txt

# Bazani yangilash
python manage.py migrate

# 1-Terminalda Veb-saytni ishga tushirish:
python manage.py runserver

# 2-Terminalda Telegram Botni ishga tushirish:
python manage.py runbot
```

---

## ⚙️ Sozlamalar (.env)

| O'zgaruvchi | Tavsif | Standart qiymat |
| :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | BotFather bergan token | `9260594956:AAH5Ny0ByaH1r8xx_oTGaIaKoRSb7ZXmcrM` |
| `TELEGRAM_ADMIN_IDS` | Asosiy admin chat ID lari | `7647505439` |
| `TELEGRAM_ADMIN_USERNAMES` | Asosiy admin telegram username lari | `mrbekii,anvar_sn` |
| `TELEGRAM_URL` | Rasmiy bot havolasi | `https://t.me/UrDU_startup_bot` |
| `FESTIVAL_DATE` | Festival boshlanish sanasi (ISO) | `2026-11-19T09:00:00+05:00` |
| `SITE_URL` | Sayt domeni (QR-kod uchun) | `http://localhost:8000` |
| `DB_ENGINE` | Baza turi | `sqlite` yoki `postgresql` |

---

## 📞 Tashkiliy Qo‘mita
* **Muassasa:** Abu Rayhon Beruniy nomidagi Urganch davlat akademik litseyi
* **Mas'ullar:** Behruz ([@mrbekii](https://t.me/mrbekii)) va Anvar ([@anvar_sn](https://t.me/anvar_sn))
* **Telefon:** +998 97 091 67 89
* **Telegram Bot:** [@UrDU_startup_bot](https://t.me/UrDU_startup_bot)
