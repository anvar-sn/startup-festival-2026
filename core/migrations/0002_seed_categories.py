from django.db import migrations
NAMES = ["IT va dasturlash", "Sun'iy intellekt (AI)", "Robototexnika va elektronika", "Ta'lim texnologiyalari (EdTech)",
         "Ekologiya va yashil texnologiyalar", "Ijtimoiy innovatsiyalar", "Biznes va tadbirkorlik"]
def seed(apps, se):
    C = apps.get_model("core", "Category")
    for i, n in enumerate(NAMES, 1): C.objects.get_or_create(name=n, defaults={"order": i})
class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
