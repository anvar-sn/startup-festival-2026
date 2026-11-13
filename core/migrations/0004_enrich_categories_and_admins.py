from django.db import migrations

CATEGORY_DATA = [
    {
        "name": "IT va dasturlash",
        "icon": "fa-solid fa-code",
        "description": "Veb-saytlar, mobil ilovalar, bulutli texnologiyalar, ma'lumotlar bazasi va dasturiy yechimlar.",
        "examples": "Mobil ilova, Web platforma, SaaS, API xizmatlar",
        "order": 1
    },
    {
        "name": "Sun'iy intellekt (AI)",
        "icon": "fa-solid fa-brain",
        "description": "Mashinaviy o'rganish, neyron tarmoqlar, kompyuter ko'rishi, NLP va aqlli yordamchi tizimlar.",
        "examples": "AI chatbot, tasvirni aniqlash, avtomatlashtirilgan tavsiya tizimlari",
        "order": 2
    },
    {
        "name": "Robototexnika va elektronika",
        "icon": "fa-solid fa-robot",
        "description": "Avtonom robotlar, mikrokontrollerlar (Arduino, ESP32, STM32), IoT qurilmalari va aqlli datchiklar.",
        "examples": "Aqlli uy tizimi, avtonom dron, qishloq xo'jaligi roboti",
        "order": 3
    },
    {
        "name": "Ta'lim texnologiyalari (EdTech)",
        "icon": "fa-solid fa-graduation-cap",
        "description": "Interaktiv o'quv vositalari, simulyatorlar, virtual laboratoriyalar va bilimni baholash platformalari.",
        "examples": "Interaktiv darslik, VR laboratoriya, o'quvchilar reyting tizimi",
        "order": 4
    },
    {
        "name": "Ekologiya va yashil texnologiyalar",
        "icon": "fa-solid fa-leaf",
        "description": "Yashil energiya, chiqindilarni qayta ishlash, suv tejash texnologiyalari va Smart Agro yechimlari.",
        "examples": "Quyosh energiyasida ishlovchi qurilma, aqlli sug'orish",
        "order": 5
    },
    {
        "name": "Ijtimoiy innovatsiyalar",
        "icon": "fa-solid fa-hands-holding-circle",
        "description": "Imkoniyati cheklangan shaxslarga ko'maklashuvchi, tibbiyot, jamoat xavfsizligi va madaniy merosni asrash loyihalari.",
        "examples": "Brayl alifbosi yordamchisi, xavfsiz yo'l harakati ilovasi",
        "order": 6
    },
    {
        "name": "Biznes va tadbirkorlik",
        "icon": "fa-solid fa-chart-line",
        "description": "Elektron tijorat, logistika optimallashtirish, FinTech va innovatsion xizmat ko'rsatish modellari.",
        "examples": "Mahalliy bozor marketplace, yetkazib berish xizmati platformasi",
        "order": 7
    },
]

def seed_rich_categories(apps, schema_editor):
    Category = apps.get_model("core", "Category")
    TelegramAdmin = apps.get_model("core", "TelegramAdmin")

    for item in CATEGORY_DATA:
        Category.objects.update_or_create(
            name=item["name"],
            defaults={
                "icon": item["icon"],
                "description": item["description"],
                "examples": item["examples"],
                "order": item["order"]
            }
        )

    # Dastlabki adminlarni ro'yxatdan o'tkazish
    TelegramAdmin.objects.update_or_create(
        chat_id=7647505439,
        defaults={
            "username": "mrbekii",
            "full_name": "Behruz",
            "is_active": True,
            "notify_on_application": True
        }
    )

class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_telegramadmin_telegramsubscriber_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_rich_categories, migrations.RunPython.noop),
    ]
