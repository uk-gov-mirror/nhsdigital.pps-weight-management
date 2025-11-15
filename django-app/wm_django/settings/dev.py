from .base import *  # noqa
DEBUG = True

# Allow any CloudFront origin for ephemeral environments
CSRF_TRUSTED_ORIGINS = ["https://*.cloudfront.net"]

# Useful when testing locally, too:
ALLOWED_HOSTS = ["*", "localhost", "127.0.0.1"]

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_CLOUDFRONT_FORWARDED_PROTO", "https")

# Cookies secure only if using HTTPS
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True