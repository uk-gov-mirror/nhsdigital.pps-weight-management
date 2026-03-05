from unittest.mock import MagicMock, patch

from django.db.backends.postgresql.base import (
    DatabaseWrapper as PostgresDatabaseWrapper,
)
from django.test import TestCase

from wm_django.db_backends.postgresql_with_rotation.base import DatabaseWrapper


class PostgreSQLWithRotationTests(TestCase):
    databases = set()

    def _make_wrapper(self) -> DatabaseWrapper:
        wrapper = DatabaseWrapper.__new__(DatabaseWrapper)
        wrapper.settings_dict = {}
        return wrapper

    @patch("wm_django.db_backends.postgresql_with_rotation.base.get_database_password")
    @patch("wm_django.db_backends.postgresql_with_rotation.base.os.getenv")
    def test_retries_once_with_refreshed_password_on_auth_failure(
        self, mock_getenv, mock_get_password
    ):
        mock_getenv.return_value = "arn:aws:secretsmanager:region:acct:secret:db"
        mock_get_password.return_value = "fresh-password"

        wrapper = self._make_wrapper()

        auth_error = Exception("password authentication failed for user app")
        with patch.object(
            PostgresDatabaseWrapper,
            "get_new_connection",
            side_effect=[auth_error, MagicMock(name="connection")],
        ) as super_connect:
            result = wrapper.get_new_connection(
                {"password": "stale-password", "host": "db"}
            )

        self.assertIsNotNone(result)
        self.assertEqual(super_connect.call_count, 2)
        first_call_params = super_connect.call_args_list[0].args[0]
        second_call_params = super_connect.call_args_list[1].args[0]
        self.assertEqual(first_call_params["password"], "stale-password")
        self.assertEqual(second_call_params["password"], "fresh-password")
        self.assertEqual(wrapper.settings_dict["PASSWORD"], "fresh-password")
        mock_get_password.assert_called_once_with(force_refresh=True)

    @patch("wm_django.db_backends.postgresql_with_rotation.base.get_database_password")
    @patch("wm_django.db_backends.postgresql_with_rotation.base.os.getenv")
    def test_does_not_retry_when_secret_arn_not_configured(
        self, mock_getenv, mock_get_password
    ):
        mock_getenv.return_value = ""

        wrapper = self._make_wrapper()

        with patch.object(
            PostgresDatabaseWrapper,
            "get_new_connection",
            side_effect=Exception("password authentication failed for user app"),
        ) as super_connect:
            with self.assertRaises(Exception) as ctx:
                wrapper.get_new_connection({"password": "stale-password"})

        self.assertIn("password authentication failed", str(ctx.exception))
        self.assertEqual(super_connect.call_count, 1)
        mock_get_password.assert_not_called()

    @patch("wm_django.db_backends.postgresql_with_rotation.base.get_database_password")
    @patch("wm_django.db_backends.postgresql_with_rotation.base.os.getenv")
    def test_does_not_retry_for_non_auth_connection_errors(
        self, mock_getenv, mock_get_password
    ):
        mock_getenv.return_value = "arn:aws:secretsmanager:region:acct:secret:db"

        wrapper = self._make_wrapper()

        with patch.object(
            PostgresDatabaseWrapper,
            "get_new_connection",
            side_effect=Exception("could not connect to server: timeout"),
        ) as super_connect:
            with self.assertRaises(Exception) as ctx:
                wrapper.get_new_connection({"password": "stale-password"})

        self.assertIn("timeout", str(ctx.exception))
        self.assertEqual(super_connect.call_count, 1)
        mock_get_password.assert_not_called()
