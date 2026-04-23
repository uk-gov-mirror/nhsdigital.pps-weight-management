# htsh/services/tokens.py
from __future__ import annotations

import hashlib
import secrets
import hmac
import string
from django.conf import settings


def generate_otp() -> str:
    """
    Generate a cryptographically secure 6-digit OTP code.
    """
    return ''.join(secrets.choice(string.digits) for _ in range(6))


def hash_token(raw_token: str) -> str:
    """
    Hash a token (or OTP) for secure storage.
    HMAC binds the hash to your SECRET_KEY so rainbow tables are pointless.
    """
    return hmac.new(
        key=settings.SECRET_KEY.encode("utf-8"),
        msg=raw_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
