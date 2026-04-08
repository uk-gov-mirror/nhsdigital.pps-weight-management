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


class _AnonymousCampaignTestCase(TestCase):
    """Base class for anonymous users with valid campaign session."""

    def setUp(self):
        session = self.client.session
        session["campaign_code"] = "TESTCAMP"
        session.save()


class AnonymousStartViewTests(_AnonymousCampaignTestCase):
    """Tests for start() with anonymous campaign users."""

    def test_start_anonymous_with_campaign_shows_postcode_href(self):
        """GET / as anonymous campaign user → start_href is details-postcode."""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"details-postcode", response.content)

    def test_start_anonymous_with_campaign_no_contact_details(self):
        """GET / as anonymous campaign user → start_href is NOT details-contact-details."""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        # The start_href should not be contact details for anonymous
        self.assertNotIn(b'href="/details-contact-details"', response.content)


class AnonymousDetailsPostcodeTests(_AnonymousCampaignTestCase):
    """Tests for details-postcode with anonymous campaign users."""

    def test_get_renders(self):
        """GET /details-postcode as anonymous campaign user → 200."""
        response = self.client.get(reverse("details_postcode"))
        self.assertEqual(response.status_code, 200)

    @mock_postcodes_io(is_valid=True)
    def test_post_valid_postcode_redirects_to_goals(self, mock_get):
        """POST /details-postcode with valid postcode → 302 to /goals."""
        response = self.client.post(
            reverse("details_postcode"), {"details-postcode": "SW1A 1AA"}
        )
        self.assertRedirects(
            response, reverse("goals"), fetch_redirect_response=False
        )

    @mock_postcodes_io(is_valid=True)
    def test_post_does_not_persist_to_user_filter(self, mock_get):
        """POST with valid postcode does not create a UserFilter (anonymous)."""
        from pilot_access.models import UserFilter

        self.client.post(
            reverse("details_postcode"), {"details-postcode": "SW1A 1AA"}
        )
        self.assertEqual(UserFilter.objects.count(), 0)


class AnonymousGoalsTests(_AnonymousCampaignTestCase):
    """Tests for goals with anonymous campaign users."""

    def test_get_renders(self):
        """GET /goals as anonymous campaign user → 200."""
        response = self.client.get(reverse("goals"))
        self.assertEqual(response.status_code, 200)

    def test_post_valid_redirects_to_barriers(self):
        """POST /goals with valid values → 302 to /barriers."""
        response = self.client.post(reverse("goals"), {"goals": ["lose_weight"]})
        self.assertRedirects(
            response, reverse("barriers"), fetch_redirect_response=False
        )


class AnonymousBarriersTests(_AnonymousCampaignTestCase):
    """Tests for barriers with anonymous campaign users."""

    def test_get_renders(self):
        """GET /barriers as anonymous campaign user → 200."""
        response = self.client.get(reverse("barriers"))
        self.assertEqual(response.status_code, 200)

    def test_post_valid_redirects_to_preference_who_with(self):
        """POST /barriers with valid values → 302 to /preference-who-with."""
        response = self.client.post(
            reverse("barriers"), {"barriers": ["time"]}
        )
        self.assertRedirects(
            response, reverse("preference_who_with"), fetch_redirect_response=False
        )


class AnonymousPreferenceWhoWithTests(_AnonymousCampaignTestCase):
    """Tests for preference-who-with with anonymous campaign users."""

    def test_get_renders(self):
        """GET /preference-who-with as anonymous campaign user → 200."""
        response = self.client.get(reverse("preference_who_with"))
        self.assertEqual(response.status_code, 200)


class AnonymousPreferenceChannelTests(_AnonymousCampaignTestCase):
    """Tests for preference_channel() with anonymous campaign users."""

    def test_post_redirects_to_listing(self):
        """POST preference-channel as anonymous → redirects to listing."""
        response = self.client.post(
            reverse("preference_channel"), {"channel": "online"}
        )
        self.assertRedirects(
            response, reverse("listing"), fetch_redirect_response=False
        )

    def test_post_sets_onboarding_complete(self):
        """POST preference-channel as anonymous → sets onboarding_complete in session."""
        self.client.post(reverse("preference_channel"), {"channel": "online"})
        self.assertTrue(self.client.session.get("onboarding_complete"))

    def test_post_does_not_redirect_to_allow_check_in(self):
        """POST preference-channel as anonymous → does NOT redirect to allow-check-in."""
        response = self.client.post(
            reverse("preference_channel"), {"channel": "online"}
        )
        self.assertNotIn("allow-check-in", response.url)


class AuthenticatedPreferenceChannelTests(_AuthenticatedTestCase):
    """Regression guard: preference_channel() still redirects auth users to allow-check-in."""

    def test_post_redirects_to_allow_check_in(self):
        """POST preference-channel as authenticated → redirects to allow-check-in."""
        response = self.client.post(
            reverse("preference_channel"), {"channel": "online"}
        )
        self.assertRedirects(
            response, reverse("allow-check-in"), fetch_redirect_response=False
        )
