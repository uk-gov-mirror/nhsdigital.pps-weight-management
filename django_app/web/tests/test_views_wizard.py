"""Tests for web wizard step views (start through allow-check-in, success, no-check-in)."""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from pilot_access.models import PilotProfile
from testing.helpers import make_pilot_profile, make_user, make_user_filter
from testing.mocks import mock_postcodes_io

User = get_user_model()


class _AuthenticatedTestCase(TestCase):
    """Base class that logs in a user with a completed pilot profile (middleware passes)."""

    def setUp(self):
        self.user = make_user()
        self.profile = make_pilot_profile(
            user=self.user,
            disclaimer_accepted_at=timezone.now(),
        )
        self.client.force_login(self.user)


class StartViewTests(TestCase):
    """Tests for the start (home) page."""

    def test_start_anonymous_user(self):
        """GET / as anonymous user redirects to landing (middleware enforced)."""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)

    def test_start_authenticated_no_filter(self):
        """GET / with logged-in user and no UserFilter defaults start_href to details-contact-details."""
        user = make_user()
        make_pilot_profile(user=user, disclaimer_accepted_at=timezone.now())
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"details-contact-details", response.content)

    def test_start_authenticated_with_filter_data(self):
        """GET / with user who has UserFilter data routes to listing."""
        user = make_user()
        make_pilot_profile(user=user, disclaimer_accepted_at=timezone.now())
        make_user_filter(user=user, data={"allow_check_in": "yes"})
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"listing", response.content)

    def test_start_magiclink_flow(self):
        """GET / with session entry_flow=magiclink routes to listing."""
        user = make_user()
        make_pilot_profile(user=user, disclaimer_accepted_at=timezone.now())
        self.client.force_login(user)
        session = self.client.session
        session["entry_flow"] = "magiclink"
        session.save()
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"listing", response.content)


class DetailsContactDetailsViewTests(_AuthenticatedTestCase):
    """Tests for the details-contact-details step."""

    def setUp(self):
        # Override base setUp to use specific email
        self.user = make_user(email="orig@test.com")
        self.profile = make_pilot_profile(
            user=self.user,
            disclaimer_accepted_at=timezone.now(),
        )
        self.client.force_login(self.user)
        self.url = reverse("details_contact_details")

    def test_get_renders_form(self):
        """GET returns 200."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_valid_email_preference(self):
        """POST with valid email preference redirects to details_postcode."""
        response = self.client.post(self.url, {
            "email": "new@test.com",
            "phone": "",
            "preferred_contact_method": PilotProfile.CONTACT_EMAIL,
        })
        self.assertRedirects(
            response,
            reverse("details_postcode"),
            fetch_redirect_response=False,
        )

    def test_post_valid_sms_preference(self):
        """POST with valid SMS preference redirects to details_postcode."""
        response = self.client.post(self.url, {
            "email": "",
            "phone": "07700900123",
            "preferred_contact_method": PilotProfile.CONTACT_SMS,
        })
        self.assertRedirects(
            response,
            reverse("details_postcode"),
            fetch_redirect_response=False,
        )

    def test_post_invalid_no_preference(self):
        """POST with no preference shows error."""
        response = self.client.post(self.url, {
            "email": "",
            "phone": "",
            "preferred_contact_method": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Please choose a preferred contact method", response.content)

    def test_post_invalid_email(self):
        """POST with invalid email shows error."""
        response = self.client.post(self.url, {
            "email": "notanemail",
            "phone": "",
            "preferred_contact_method": PilotProfile.CONTACT_EMAIL,
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"valid email", response.content)

    def test_post_invalid_phone(self):
        """POST with invalid phone shows error."""
        response = self.client.post(self.url, {
            "email": "",
            "phone": "abc",
            "preferred_contact_method": PilotProfile.CONTACT_SMS,
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"valid mobile", response.content)

    def test_post_duplicate_email(self):
        """POST with email already used by another user shows error."""
        make_user(email="taken@test.com")
        response = self.client.post(self.url, {
            "email": "taken@test.com",
            "phone": "",
            "preferred_contact_method": PilotProfile.CONTACT_EMAIL,
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"already in use", response.content)


class DetailsPostcodeViewTests(_AuthenticatedTestCase):
    """Tests for the details-postcode step."""

    def setUp(self):
        super().setUp()
        self.url = reverse("details_postcode")

    def test_get_renders_form(self):
        """GET returns 200."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    @mock_postcodes_io(is_valid=True)
    def test_post_valid_postcode(self, mock_get):
        """POST with valid postcode redirects to goals."""
        response = self.client.post(self.url, {"details-postcode": "SW1A 1AA"})
        self.assertRedirects(
            response, reverse("goals"), fetch_redirect_response=False
        )

    def test_post_invalid_format(self):
        """POST with badly formatted postcode shows error (no API call)."""
        response = self.client.post(self.url, {"details-postcode": "NOTAPC"})
        self.assertEqual(response.status_code, 200)

    @mock_postcodes_io(is_valid=False)
    def test_post_api_invalid(self, mock_get):
        """POST with postcode rejected by API shows error."""
        response = self.client.post(self.url, {"details-postcode": "SW1A 1AA"})
        self.assertEqual(response.status_code, 200)


class AllowCheckInViewTests(_AuthenticatedTestCase):
    """Tests for the allow-check-in step."""

    def setUp(self):
        super().setUp()
        self.url = reverse("allow-check-in")

    def test_get_renders(self):
        """GET returns 200."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    @patch("web.views.requests.post")
    def test_post_yes(self, mock_post):
        """POST allow_check_in=yes sets onboarding_complete and redirects to listing."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.json.return_value = {"total": 0, "results": []}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp
        response = self.client.post(self.url, {"allow_check_in": "yes"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.session.get("onboarding_complete"))

    def test_post_no(self):
        """POST allow_check_in=no sets onboarding_complete and redirects to no_check_in."""
        response = self.client.post(self.url, {"allow_check_in": "no"})
        self.assertRedirects(
            response,
            reverse("no_check_in"),
            fetch_redirect_response=False,
        )
        self.assertTrue(self.client.session.get("onboarding_complete"))

    def test_post_invalid(self):
        """POST with no value shows error."""
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)
