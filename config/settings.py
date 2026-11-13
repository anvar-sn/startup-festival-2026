import os
import urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
env = os.environ.get

SECRET_KEY = env("SECRET_KEY", "dev-only-insecure-key-startup-2026")
DEBUG = env("DEBUG", "1") == "1"
ALLOWED_HOSTS = [h.strip() for h in env("ALLOWED_HOSTS", "*").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in env(
        "CSRF_TRUSTED_ORIGINS",
        "https://*.onrender.com,http://localhost:8000,http://127.0.0.1:8000"
    ).split(",")
    if o.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
]

try:
    import whitenoise
    MIDDLEWARE.append("whitenoise.middleware.WhiteNoiseMiddleware")
except ImportError:
    pass

MIDDLEWARE.extend([
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
])

ROOT_URLCONF = "config.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
            "core.context.site",
        ]
    },
}]

WSGI_APPLICATION = "config.wsgi.application"

# Database sozlamalari (Render PostgreSQL va SQLite avtomatik moslashuvchan)
database_url = env("DATABASE_URL")
if database_url:
    try:
        url = urllib.parse.urlparse(database_url)
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": url.path[1:],
                "USER": url.username,
                "PASSWORD": url.password,
                "HOST": url.hostname,
                "PORT": url.port or "5432",
            }
        }
    except Exception:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": BASE_DIR / "db.sqlite3",
            }
        }
elif env("DB_ENGINE") == "sqlite" or not env("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", "festival"),
            "USER": env("POSTGRES_USER", "festival"),
            "PASSWORD": env("POSTGRES_PASSWORD", ""),
            "HOST": env("POSTGRES_HOST", "localhost"),
            "PORT": env("POSTGRES_PORT", "5432"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"django.contrib.auth.password_validation.{n}"}
    for n in ["UserAttributeSimilarityValidator", "MinimumLengthValidator", "CommonPasswordValidator", "NumericPasswordValidator"]
]

LANGUAGE_CODE = "uz"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

try:
    import whitenoise
    static_backend = "whitenoise.storage.CompressedManifestStaticFilesStorage" if not DEBUG else "django.contrib.staticfiles.storage.StaticFilesStorage"
except ImportError:
    static_backend = "django.contrib.staticfiles.storage.StaticFilesStorage"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": static_backend},
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Yuklanadigan ma'lumotlar cheklovi (katta taqdimot va videolar uchun moslangan)
DATA_UPLOAD_MAX_MEMORY_SIZE = 75 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 75 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FILES = 20

SITE_URL = env("SITE_URL", "http://localhost:8000")
FESTIVAL_DATE = env("FESTIVAL_DATE", "2026-11-19T09:00:00+05:00")
TELEGRAM_URL = env("TELEGRAM_URL", "https://t.me/UrDU_startup_bot")

# Telegram Bot va Admin sozlamalari
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", "9260594956:AAH5Ny0ByaH1r8xx_oTGaIaKoRSb7ZXmcrM")
_default_admin_ids = env("TELEGRAM_ADMIN_IDS", "7647505439")
TELEGRAM_ADMIN_IDS = [int(i.strip()) for i in _default_admin_ids.split(",") if i.strip().isdigit()]
_default_admin_usernames = env("TELEGRAM_ADMIN_USERNAMES", "mrbekii,anvar_sn")
TELEGRAM_ADMIN_USERNAMES = [u.strip().lstrip("@").lower() for u in _default_admin_usernames.split(",") if u.strip()]

if not DEBUG:
    SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = SITE_URL.startswith("https")
    SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"
