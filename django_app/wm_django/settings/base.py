"""
Base Django settings shared across all environments.

Environment-specific overrides live in:
- wm_django.settings.dev
- wm_django.settings.prod

Security- and environment-sensitive values (SECRET_KEY, DEBUG, ALLOWED_HOSTS,
database credentials, etc.) are configured via environment variables.
"""

from pathlib import Path
import os

from wm_django.secret_store import get_database_password


# -------------------------------------------------------------------
# Paths and core environment
# -------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

ENV_NAME = os.getenv("DJANGO_ENV_NAME", "Unknown")
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")
SERVICE_API_BASE_URL = os.getenv("SERVICE_API_BASE_URL")


# -------------------------------------------------------------------
# External services (Cognito / AWS)
# -------------------------------------------------------------------

COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID")
COGNITO_CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID")
AWS_REGION = os.environ.get("AWS_REGION")


# -------------------------------------------------------------------
# Applications
# -------------------------------------------------------------------

INSTALLED_APPS = [
    # Django contrib apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party apps
    "nhsuk_frontend_jinja",
    "rest_framework",
    "drf_spectacular",

    # Project apps
    "core",
    "web",
    "api",
    "scheduler",
    "pilot_access.apps.PilotAccessConfig",
]


# -------------------------------------------------------------------
# Middleware
# -------------------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "pilot_access.middleware.PilotAccessMiddleware",
 ]


# -------------------------------------------------------------------
# URL configuration
# -------------------------------------------------------------------

ROOT_URLCONF = "wm_django.urls"


# -------------------------------------------------------------------
# Templates (Django & Jinja2)
# -------------------------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates" / "django"],
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
    {
        "BACKEND": "django.template.backends.jinja2.Jinja2",
        "DIRS": [BASE_DIR / "templates" / "jinja2"],
        "OPTIONS": {
            "environment": "wm_django.jinja2_env.environment",
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# -------------------------------------------------------------------
# WSGI / ASGI
# -------------------------------------------------------------------

WSGI_APPLICATION = "wm_django.wsgi.application"


# -------------------------------------------------------------------
# Database
# -------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "wm_django.db_backends.postgresql_with_rotation",
        "HOST": os.getenv("DATABASE_HOST", "db"),
        "PORT": os.getenv("DATABASE_PORT", "5432"),
        "NAME": os.getenv("DATABASE_NAME", "app"),
        "USER": os.getenv("DATABASE_USER", "app"),
        "PASSWORD": get_database_password(),
        "OPTIONS": {
            "connect_timeout": 5,
        },
    }
}


# -------------------------------------------------------------------
# Internationalisation
# -------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# -------------------------------------------------------------------
# Static files
# -------------------------------------------------------------------

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# -------------------------------------------------------------------
# Proxy / SSL handling
# -------------------------------------------------------------------

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# -------------------------------------------------------------------
# Default primary key field type
# -------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------

if os.getenv("DJANGO_SIMPLE_LOGGING", "true").lower() == "true":
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
        },
    }


# -------------------------------------------------------------------
# Django REST Framework
# -------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}


# -------------------------------------------------------------------
# DRF Spectacular (OpenAPI)
# -------------------------------------------------------------------

SPECTACULAR_SETTINGS = {
    "TITLE": "Weight Management API",
    "DESCRIPTION": "API documentation for Weight Management services.",
    "SERVE_INCLUDE_SCHEMA": False,
}

# -------------------------------------------------------------------
# Session configuration (explicit for anonymous user support — MID-03)
# -------------------------------------------------------------------

SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds
SESSION_SAVE_EVERY_REQUEST = False  # Save only when session is modified
SESSION_COOKIE_HTTPONLY = True

# -------------------------------------------------------------------
# Pilot Access - Protected route model
# -------------------------------------------------------------------

# Paths requiring full authentication (user + pilot profile + disclaimer)
PILOT_ACCESS_AUTH_REQUIRED_PREFIXES = [
    "/pilot/account/",
    "/favourites",
]

# System/infrastructure paths exempt from ALL pilot access checks
PILOT_ACCESS_EXEMPT_PREFIXES = [
    "/health",
    "/static/",
    "/admin/",
    "/apidocs/",
    "/redoc/",
    "/schema.yaml",
    "/v1/",
    "/v2/",
    "/v3/",
]

# -------------------------------------------------------------------
# Pilot Access - Email and SMS senders (empty = use mocks that log)
# -------------------------------------------------------------------

PILOT_ACCESS_EMAIL_SENDER = ""
PILOT_ACCESS_SMS_SENDER = ""