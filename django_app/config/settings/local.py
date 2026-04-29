"""
Local Django settings.

These override base.py with permissive hosts/origins and enables DEBUG
"""

from .base import *

ENV_NAME = "Local"

DEBUG = True

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
]

# Let sessionid cookie be set
SESSION_COOKIE_SAMESITE = "Lax"

# Sessions must work over plain HTTP locally
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# We are not behind CloudFront or ALB locally
SECURE_PROXY_SSL_HEADER = None
USE_X_FORWARDED_HOST = False

# Do not force HTTPS locally
SECURE_SSL_REDIRECT = False

# Optional
CSRF_TRUSTED_ORIGINS = []
