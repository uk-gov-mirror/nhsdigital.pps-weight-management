"""Unit tests for geo utilities, OTP services, and sender interface."""

from unittest.mock import patch

from django.test import TestCase

from api.v3.geo import UK_POSTCODE_REGEX, haversine_km, resolve_centre_and_radius
from htsh.services.tokens import generate_otp, hash_token


class HaversineTests(TestCase):
    databases = set()

    def test_known_distance_london_to_paris(self):
        result = haversine_km(51.5074, -0.1278, 48.8566, 2.3522)
        self.assertAlmostEqual(result, 343.5, delta=1.0)


class PostcodeRegexTests(TestCase):
    databases = set()

    def test_valid_with_space(self):
        self.assertTrue(UK_POSTCODE_REGEX.match("SW1A 1AA"))

    def test_invalid(self):
        self.assertFalse(UK_POSTCODE_REGEX.match("INVALID"))


class ResolveCentreAndRadiusTests(TestCase):
    databases = set()

    @patch("api.v3.geo.geocode_postcode", return_value=(51.5, -0.1))
    def test_valid_postcode(self, _mock_geocode):
        lat, lon, radius_km = resolve_centre_and_radius("SW1A 1AA", 10)
        self.assertAlmostEqual(lat, 51.5)
        self.assertAlmostEqual(lon, -0.1)
        self.assertAlmostEqual(radius_km, 10 * 1.60934, places=3)

    def test_empty_postcode(self):
        result = resolve_centre_and_radius("", 10)
        self.assertEqual(result, (None, None, None))

    def test_invalid_postcode(self):
        result = resolve_centre_and_radius("INVALID", 10)
        self.assertEqual(result, (None, None, None))


class OTPTests(TestCase):
    databases = set()

    def test_generate_otp_length(self):
        otp = generate_otp()
        self.assertEqual(len(otp), 6)

    def test_generate_otp_digits_only(self):
        otp = generate_otp()
        self.assertTrue(otp.isdigit())

    def test_hash_token_deterministic(self):
        self.assertEqual(hash_token("test"), hash_token("test"))
