import base64
import json
import os
import threading
import time
from typing import Optional


_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, tuple[str, float]] = {}


def _cache_key(secret_arn: str, secret_key: str, region: str) -> str:
    return f"{region}:{secret_arn}:{secret_key}"


def _read_cached_value(cache_key: str) -> Optional[str]:
    with _CACHE_LOCK:
        cached = _CACHE.get(cache_key)
        if not cached:
            return None

        value, expires_at = cached
        if time.time() >= expires_at:
            _CACHE.pop(cache_key, None)
            return None

        return value


def _write_cached_value(cache_key: str, value: str, ttl_seconds: int) -> None:
    with _CACHE_LOCK:
        _CACHE[cache_key] = (value, time.time() + ttl_seconds)


def _read_secret_string(secret_arn: str, region: str) -> str:
    import boto3

    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_arn)

    if "SecretString" in response and response["SecretString"]:
        return response["SecretString"]

    if "SecretBinary" in response and response["SecretBinary"]:
        binary_value = base64.b64decode(response["SecretBinary"])
        return binary_value.decode("utf-8")

    raise ValueError(f"Secret {secret_arn} did not contain SecretString or SecretBinary")


def _extract_secret_value(secret_string: str, secret_key: str) -> str:
    try:
        secret_payload = json.loads(secret_string)
    except json.JSONDecodeError as exc:
        raise ValueError("DB secret value is not valid JSON") from exc

    if secret_key not in secret_payload:
        raise KeyError(f"Key '{secret_key}' not found in DB secret payload")

    value = secret_payload[secret_key]
    if not isinstance(value, str):
        value = str(value)

    return value


def get_database_password() -> str:
    secret_arn = os.getenv("DATABASE_PASSWORD_SECRET_ARN", "").strip()
    if not secret_arn:
        return os.getenv("DATABASE_PASSWORD", "app")

    secret_key = os.getenv("DATABASE_PASSWORD_SECRET_KEY", "db_password")
    region = os.getenv("AWS_REGION", "eu-west-2")

    try:
        ttl_seconds = int(os.getenv("DATABASE_PASSWORD_CACHE_TTL_SECONDS", "300"))
    except ValueError:
        ttl_seconds = 300

    ttl_seconds = max(0, ttl_seconds)

    cache_key = _cache_key(secret_arn=secret_arn, secret_key=secret_key, region=region)
    if ttl_seconds > 0:
        cached_value = _read_cached_value(cache_key)
        if cached_value is not None:
            return cached_value

    secret_string = _read_secret_string(secret_arn=secret_arn, region=region)
    password = _extract_secret_value(secret_string=secret_string, secret_key=secret_key)

    if ttl_seconds > 0:
        _write_cached_value(cache_key=cache_key, value=password, ttl_seconds=ttl_seconds)

    return password
