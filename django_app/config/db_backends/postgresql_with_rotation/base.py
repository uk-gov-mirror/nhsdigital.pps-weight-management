import os
from typing import Any

from django.db.backends.postgresql.base import DatabaseWrapper as PostgresDatabaseWrapper

from config.secret_store import get_database_password

_AUTH_FAILURE_MARKERS = (
    "password authentication failed",
    "authentication failed",
    "fe_sendauth",
)


class DatabaseWrapper(PostgresDatabaseWrapper):
    def get_new_connection(self, conn_params: dict[str, Any]):
        try:
            return super().get_new_connection(conn_params)
        except Exception as exc:
            if not self._should_retry_with_refreshed_password(exc):
                raise

            refreshed_password = get_database_password(force_refresh=True)
            retry_params = dict(conn_params)
            retry_params["password"] = refreshed_password
            self.settings_dict["PASSWORD"] = refreshed_password
            return super().get_new_connection(retry_params)

    def _should_retry_with_refreshed_password(self, exc: Exception) -> bool:
        if not os.getenv("DATABASE_PASSWORD_SECRET_ARN", "").strip():
            return False

        message = str(exc).lower()
        return any(marker in message for marker in _AUTH_FAILURE_MARKERS)
