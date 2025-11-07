from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY    = os.getenv('DJANGO_SECRET_KEY', 'dev-secret-key-change-me')
DEBUG         = os.getenv('DJANGO_DEBUG', 'false').lower() == 'true'
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '*').split(',')

COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID")
COGNITO_CLIENT_ID    = os.environ.get("COGNITO_CLIENT_ID")
AWS_REGION           = os.environ.get("AWS_REGION") 

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'web',
    'api',
    'scheduler',
]

MIDDLEWARE = [
    'core.middleware.CognitoAccessTokenMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'helloworld.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.jinja2.Jinja2',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'environment': 'helloworld.jinja2_env.environment',
        },
    },
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'helloworld.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': os.getenv('DATABASE_HOST', 'db'),
        'PORT': os.getenv('DATABASE_PORT', '5432'),
        'NAME': os.getenv('DATABASE_NAME', 'app'),
        'USER': os.getenv('DATABASE_USER', 'app'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD', 'app'),
        'OPTIONS': {
            'connect_timeout': 5,
        },
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'UTC'
USE_I18N      = True
USE_TZ        = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

if os.getenv("DJANGO_SIMPLE_LOGGING", "true").lower() == "true":
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {'console': {'class': 'logging.StreamHandler'}},
        'root': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
    }
