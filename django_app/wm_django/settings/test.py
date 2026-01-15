"""
Test Django settings for BDD tests.
Inherits from base settings but uses SQLite for testing.
"""
from wm_django.settings.base import *  # noqa

# Override database configuration for tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable some middleware/features that require external services for testing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',  # Fast for testing
]

# Disable cache for testing
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Disable session serializer to avoid issues
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

# Set DEBUG for better error messages in tests
DEBUG = True
