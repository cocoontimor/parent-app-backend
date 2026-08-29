import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)
environ.Env.read_env(os.path.join(BASE_DIR.parent, ".env"))

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

EXTERNAL_APPS = [
    "allauth",
    "allauth.account",
    "django_extensions",
    "rest_framework",  # kept: serializers shape Inertia props
    "rest_framework.authtoken",
    "inertia",
    "django_vite",
    "django_celery_beat",
]

INTERNAL_APPS = [
    "users",
    "utils",
    "children",
    "announcements",
    "updates",
    "messaging",
    "elearning",
    "payments",
    "web",
]

INSTALLED_APPS = DJANGO_APPS + INTERNAL_APPS + EXTERNAL_APPS
SITE_ID = 1

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "inertia.middleware.InertiaMiddleware",
    "web.middleware.inertia_share",  # shares auth.user with every Inertia page
]

ROOT_URLCONF = "cocoon.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "cocoon.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DATABASE_NAME"),
        "USER": env("POSTGRES_DATABASE_USER"),
        "PASSWORD": env("POSTGRES_DATABASE_PASSWORD"),
        "HOST": env("POSTGRES_DATABASE_HOST"),
        "PORT": env("POSTGRES_DATABASE_PORT"),
        # Cloud SQL is ENCRYPTED_ONLY; use "require" in prod. Defaults to
        # "prefer" so local/dev Postgres (no SSL) still connects.
        "OPTIONS": {"sslmode": env("POSTGRES_DATABASE_SSLMODE", default="prefer")},
    }
}

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Allauth
# ---------------------------------------------------------------------------
ACCOUNT_LOGIN_METHODS = {"username"}
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_EMAIL_REQUIRED = False
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "none"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"

# ---------------------------------------------------------------------------
# REST Framework
# ---------------------------------------------------------------------------
# The REST API and its OpenAPI schema were retired when the admin UI moved to
# Inertia (Svelte) served directly by Django. `rest_framework` stays installed
# only because the serializers are reused to shape Inertia page props.

# ---------------------------------------------------------------------------
# Cache (Redis)
# ---------------------------------------------------------------------------
REDIS_HOST = env("REDIS_HOST", default="localhost")
REDIS_PORT = env("REDIS_PORT", default="6379")
REDIS_PASSWORD = env("REDIS_PASSWORD", default="")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/1"
        if REDIS_PASSWORD
        else f"redis://{REDIS_HOST}:{REDIS_PORT}/1",
    }
}

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=f"redis://{REDIS_HOST}:{REDIS_PORT}/10")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=f"redis://{REDIS_HOST}:{REDIS_PORT}/11")
CELERY_TIMEZONE = "UTC"
CELERY_TASK_IGNORE_RESULT = True

# Schedules live in the database (django-celery-beat), editable via the Django
# admin without a redeploy. The two default tasks are seeded by a data migration
# (messaging/migrations/0004); each schedule carries its own timezone.
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# ---------------------------------------------------------------------------
# WhatsApp Cloud API
# ---------------------------------------------------------------------------
WHATSAPP_PHONE_NUMBER_ID = env("WHATSAPP_PHONE_NUMBER_ID", default="")
WHATSAPP_ACCESS_TOKEN = env("WHATSAPP_ACCESS_TOKEN", default="")
WHATSAPP_WEBHOOK_VERIFY_TOKEN = env("WHATSAPP_WEBHOOK_VERIFY_TOKEN", default="cocoon-webhook-verify")
# Meta App Secret — used to verify the X-Hub-Signature-256 on inbound webhooks.
# When unset, signature verification is skipped (dev-friendly fail-open).
WHATSAPP_APP_SECRET = env("WHATSAPP_APP_SECRET", default="")

# Absolute base URL used to build magic links sent over WhatsApp.
APP_BASE_URL = env("APP_BASE_URL", default="http://localhost:8000")

# ---------------------------------------------------------------------------
# Email (console in dev)
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ---------------------------------------------------------------------------
# i18n / Static
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
# Vite build output; django-vite reads the manifest here in prod.
# frontend/ is a sibling of src/ (BASE_DIR), so use BASE_DIR.parent.
STATICFILES_DIRS = [BASE_DIR.parent / "frontend" / "dist"]

MEDIA_URL = "media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# ---------------------------------------------------------------------------
# Inertia + django-vite (Svelte frontend served by Django)
# ---------------------------------------------------------------------------
INERTIA_LAYOUT = "base.html"

# Dev: Vite serves assets from its own server (port 5173) with HMR.
# Prod: assets are read from the built manifest under frontend/dist.
DJANGO_VITE = {
    "default": {
        "dev_mode": DEBUG,
        "dev_server_port": 5173,
        "manifest_path": BASE_DIR.parent / "frontend" / "dist" / ".vite" / "manifest.json",
    }
}

# CSRF: Inertia (axios) sends the token in this header; align Django to read it.
CSRF_HEADER_NAME = "HTTP_X_XSRF_TOKEN"
CSRF_COOKIE_NAME = "XSRF-TOKEN"

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
# If GS_BUCKET_NAME is set, media files go to Google Cloud Storage via
# django-storages. Auth uses Application Default Credentials:
#   - On GCE: picked up from the VM's metadata server (attached SA).
#   - Locally: `gcloud auth application-default login`, or a key file
#     referenced by GOOGLE_APPLICATION_CREDENTIALS.
# When GS_BUCKET_NAME is empty, we fall back to the local filesystem so dev
# / tests keep working without touching GCP.
GS_BUCKET_NAME = env("GS_BUCKET_NAME", default="")

if GS_BUCKET_NAME:
    default_storage = {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        "OPTIONS": {
            "bucket_name": GS_BUCKET_NAME,
            "project_id": env("GS_PROJECT_ID", default=""),
            "location": env("GS_LOCATION", default="media"),
            "default_acl": None,          # bucket uses uniform IAM
            "querystring_auth": False,    # bucket is public-read
            "file_overwrite": False,
        },
    }
else:
    default_storage = {"BACKEND": "django.core.files.storage.FileSystemStorage"}

STORAGES = {
    "default": default_storage,
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Security (behind an HTTPS-terminating reverse proxy / nginx)
# ---------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
