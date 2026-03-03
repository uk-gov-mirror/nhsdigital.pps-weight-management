from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

from django.db.backends.postgresql.base import DatabaseWrapper as PostgresDatabaseWrapper

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "django_app"))

from wm_django.db_backends.postgresql_with_rotation.base import DatabaseWrapper


def _make_wrapper() -> DatabaseWrapper:
    wrapper = DatabaseWrapper.__new__(DatabaseWrapper)
    wrapper.settings_dict = {}
    return wrapper


@patch("wm_django.db_backends.postgresql_with_rotation.base.get_database_password")
@patch("wm_django.db_backends.postgresql_with_rotation.base.os.getenv")
def test_retries_once_with_refreshed_password_on_auth_failure(mock_getenv, mock_get_password):
    mock_getenv.return_value = "arn:aws:secretsmanager:region:acct:secret:db"
    mock_get_password.return_value = "fresh-password"

    wrapper = _make_wrapper()

    auth_error = Exception("password authentication failed for user app")
    with patch.object(
        PostgresDatabaseWrapper,
        "get_new_connection",
        side_effect=[auth_error, MagicMock(name="connection")],
    ) as super_connect:
        result = wrapper.get_new_connection({"password": "stale-password", "host": "db"})

    assert result is not None
    assert super_connect.call_count == 2
    first_call_params = super_connect.call_args_list[0].args[0]
    second_call_params = super_connect.call_args_list[1].args[0]
    assert first_call_params["password"] == "stale-password"
    assert second_call_params["password"] == "fresh-password"
    assert wrapper.settings_dict["PASSWORD"] == "fresh-password"
    mock_get_password.assert_called_once_with(force_refresh=True)


@patch("wm_django.db_backends.postgresql_with_rotation.base.get_database_password")
@patch("wm_django.db_backends.postgresql_with_rotation.base.os.getenv")
def test_does_not_retry_when_secret_arn_not_configured(mock_getenv, mock_get_password):
    mock_getenv.return_value = ""

    wrapper = _make_wrapper()

    with patch.object(
        PostgresDatabaseWrapper,
        "get_new_connection",
        side_effect=Exception("password authentication failed for user app"),
    ) as super_connect:
        try:
            wrapper.get_new_connection({"password": "stale-password"})
            assert False, "Expected exception to be re-raised"
        except Exception as exc:
            assert "password authentication failed" in str(exc)

    assert super_connect.call_count == 1
    mock_get_password.assert_not_called()


@patch("wm_django.db_backends.postgresql_with_rotation.base.get_database_password")
@patch("wm_django.db_backends.postgresql_with_rotation.base.os.getenv")
def test_does_not_retry_for_non_auth_connection_errors(mock_getenv, mock_get_password):
    mock_getenv.return_value = "arn:aws:secretsmanager:region:acct:secret:db"

    wrapper = _make_wrapper()

    with patch.object(
        PostgresDatabaseWrapper,
        "get_new_connection",
        side_effect=Exception("could not connect to server: timeout"),
    ) as super_connect:
        try:
            wrapper.get_new_connection({"password": "stale-password"})
            assert False, "Expected exception to be re-raised"
        except Exception as exc:
            assert "timeout" in str(exc)

    assert super_connect.call_count == 1
    mock_get_password.assert_not_called()
