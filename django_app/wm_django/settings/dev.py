"""
Development Django settings.

These override base.py with permissive hosts/origins and enables DEBUG
"""

from .base import * 
DEBUG = True

ENV_NAME = "Development"

# Allow any CloudFront origin for ephemeral environments
CSRF_TRUSTED_ORIGINS = ["https://*.cloudfront.net"]

# Useful when testing locally, too:
ALLOWED_HOSTS = ["*", "localhost", "127.0.0.1"]

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_CLOUDFRONT_FORWARDED_PROTO", "https")

# Persist login session info when using http locally
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Stop the app throwing "INTERNAL SERVER ERROR" when static files are missing
WHITENOISE_MANIFEST_STRICT = False
