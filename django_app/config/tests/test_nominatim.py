"""Unit tests for Nominatim geocoding."""

from unittest.mock import patch, MagicMock

from django.test import TestCase

from api.v3.nominatim import nominatim_geocode


class TestNominatimGeocode(TestCase):
    """Tests for nominatim_geocode with mocked HTTP."""

    databases = set()

    @patch("api.v3.nominatim.requests.get")
    def test_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"lat": "51.5", "lon": "-0.1"}]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        lat, lon = nominatim_geocode("SW1A 1AA")
        self.assertEqual(lat, 51.5)
        self.assertEqual(lon, -0.1)

    @patch("api.v3.nominatim.requests.get")
    def test_empty_results(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        lat, lon = nominatim_geocode("ZZ99 9ZZ")
        self.assertIsNone(lat)
        self.assertIsNone(lon)

    def test_empty_postcode(self):
        lat, lon = nominatim_geocode("")
        self.assertIsNone(lat)
        self.assertIsNone(lon)

    def test_none_postcode(self):
        lat, lon = nominatim_geocode(None)
        self.assertIsNone(lat)
        self.assertIsNone(lon)

    @patch("api.v3.nominatim.requests.get")
    def test_request_exception(self, mock_get):
        import requests
        mock_get.side_effect = requests.RequestException("Network error")

        lat, lon = nominatim_geocode("SW1A 1AA")
        self.assertIsNone(lat)
        self.assertIsNone(lon)
