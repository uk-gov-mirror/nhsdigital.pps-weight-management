# pilot_access/tokens.py
from __future__ import annotations

import hashlib
import secrets
import hmac
from django.conf import settings


def generate_token() -> str:
    """
    Returns the *raw* token you send to the user (email/SMS).
    """
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    # HMAC binds the hash to your SECRET_KEY so rainbow tables are pointless
    return hmac.new(
        key=settings.SECRET_KEY.encode("utf-8"),
        msg=raw_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
