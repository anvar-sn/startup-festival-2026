import os
import urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
env = os.environ.get

IS_VERCEL = bool(env("VERCEL") or env("AWS_LAMBDA_FUNCTION_NAME"))
SECRET_KEY = env("SECRET_KEY", "dev-only-insecure-key-startup-2026")
DEBUG = env("DEBUG", "0" if IS_VERCEL else "1") == "1"
ALLOWED_HOSTS = [h.strip() for h in env("ALLOWED_HOSTS", "*").split(",") if h.strip()]

_default_site = env("SITE_URL") or env("VERCEL_PROJECT_PRODUCTION_URL") or env("VERCEL_URL") or env("RENDER_EXTERNAL_URL") or "https://startup-festival-2026.vercel.app"
if _default_site and not _default_site.startswith(("http://", "https://")):
    _default_site = f"https://{_default_site}"
SITE_URL = _default_site.rstrip("/")

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in env(
        "CSRF_TRUSTED_ORIGINS",
        "https://*.vercel.app,https://*.onrender.com,http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if o.strip()
]
if SITE_URL.startswith(("http://", "https://")) and SITE_URL not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(SITE_URL)

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

# Database sozlamalari (Neon / Render PostgreSQL va SQLite avtomatik moslashuvchan)
database_url = env("DATABASE_URL") or env("POSTGRES_URL")
if database_url:
    try:
        url = urllib.parse.urlparse(database_url)
        db_options = {}
        host = (url.hostname or "").lower()
        if host and host not in ("localhost", "127.0.0.1", "db", "postgres"):
            db_options["sslmode"] = "require"
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": url.path.lstrip("/"),
                "USER": urllib.parse.unquote(url.username or ""),
                "PASSWORD": urllib.parse.unquote(url.password or ""),
                "HOST": url.hostname,
                "PORT": url.port or "5432",
                "CONN_MAX_AGE": 0 if IS_VERCEL else 60,
                "OPTIONS": db_options,
            }
        }
    except Exception:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": Path("/tmp/db.sqlite3") if IS_VERCEL else BASE_DIR / "db.sqlite3",
            }
        }
elif env("DB_ENGINE") == "sqlite" or not env("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": Path("/tmp/db.sqlite3") if IS_VERCEL else BASE_DIR / "db.sqlite3",
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

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
WHITENOISE_USE_FINDERS = True

try:
    import whitenoise
    static_backend = (
        "django.contrib.staticfiles.storage.StaticFilesStorage"
        if (DEBUG or IS_VERCEL)
        else "whitenoise.storage.CompressedManifestStaticFilesStorage"
    )
except ImportError:
    static_backend = "django.contrib.staticfiles.storage.StaticFilesStorage"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": static_backend},
}

MEDIA_URL = "/media/"
MEDIA_ROOT = Path("/tmp/media") if IS_VERCEL else BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Yuklanadigan ma'lumotlar cheklovi (katta taqdimot va videolar uchun moslangan)
DATA_UPLOAD_MAX_MEMORY_SIZE = 75 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 75 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FILES = 20

FESTIVAL_DATE = env("FESTIVAL_DATE", "2026-11-19T09:00:00+05:00")
TELEGRAM_URL = env("TELEGRAM_URL", "https://t.me/UrDU_startup_bot")

# Telegram Bot va Admin sozlamalari
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", "9260594956:AAH5Ny0ByaH1r8xx_oTGaIaKoRSb7ZXmcrM")
_default_admin_ids = env("TELEGRAM_ADMIN_IDS", "7647505439,6150570776")
TELEGRAM_ADMIN_IDS = [int(i.strip()) for i in _default_admin_ids.split(",") if i.strip().isdigit()]
_default_admin_usernames = env("TELEGRAM_ADMIN_USERNAMES", "mrbekii,anvar_sn")
TELEGRAM_ADMIN_USERNAMES = [u.strip().lstrip("@").lower() for u in _default_admin_usernames.split(",") if u.strip()]

if not DEBUG:
    SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = SITE_URL.startswith("https")
    SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"
