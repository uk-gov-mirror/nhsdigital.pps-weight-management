"""Mock decorators for suppressing real HTTP calls in tests."""

from unittest.mock import MagicMock, patch


def mock_nominatim(lat=51.5074, lon=-0.1278):
    """Decorator that patches nominatim_geocode to return fixed coordinates."""
    return patch(
        "api.v3.nominatim.nominatim_geocode",
        return_value=(lat, lon),
    )


def mock_postcodes_io(is_valid=True):
    """Decorator that patches requests.get for postcodes.io validation."""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {"result": is_valid}
    mock_response.raise_for_status = MagicMock()
    return patch("web.views.requests.get", return_value=mock_response)


def mock_internal_api(response_data=None, status_code=200):
    """Decorator that patches requests calls to the internal v3 API."""
    if response_data is None:
        response_data = {"results": [], "count": 0}
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.ok = 200 <= status_code < 300
    mock_response.json.return_value = response_data
    mock_response.raise_for_status = MagicMock()
    return patch("web.views.requests", MagicMock(
        get=MagicMock(return_value=mock_response),
        post=MagicMock(return_value=mock_response),
    ))
