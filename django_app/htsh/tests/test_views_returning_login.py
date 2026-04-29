"""Tests for returning authenticated user flows (RET-01).

Verifies session restoration on OTP login for returning users and
start() routing based on UserFilter data.
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from htsh.models import MagicLink, QuestionnaireResponse
from htsh.services.tokens import generate_otp, hash_token
from testing.helpers import (
    make_campaign,
    make_profile,
    make_user,
    make_user_filter,
)

User = get_user_model()

SAMPLE_QUESTIONNAIRE_DATA = {
    "motivation": "motivation.want_to_feel_better",
    "priority_behaviour": "priority_behaviour.more_physically_active",
    "past_barriers": ["past_barriers.no_time"],
    "current_barriers": ["current_barriers.short_on_time"],
    "confidence_readiness": "confidence_readiness.ready_and_confident",
    "enablers": ["enablers.affordable"],
}

SAMPLE_FILTER_DATA = {
    "details-postcode": "SW1A 1AA",
    "cost": "free",
    "location": "online",
    "taught": "yes",
}


@patch("htsh.views._ensure_min_response_time")
class ReturningLoginSessionRestoreTests(TestCase):
    """Tests for session restoration when a returning user logs in via OTP."""

    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.profile = make_profile(
            user=self.user,
            disclaimer_accepted_at=timezone.now(),
        )
        self.otp = generate_otp()
        self.magic_link = MagicLink.objects.create(
            user=self.user,
            token_hash=hash_token(self.otp),
            expires_at=timezone.now() + timedelta(minutes=15),
        )

    def _set_otp_session(self, flow="login"):
        """Set OTP session keys for login flow."""
        session = self.client.session
        session["otp_user_id"] = self.user.id
        session["otp_flow"] = flow
        session["otp_contact"] = self.profile.email
        session["otp_is_email"] = True
        session.save()

    def test_returning_login_restores_all_session_keys(self, mock_timing):
        """Returning login restores questionnaire keys from QuestionnaireResponse and filter keys from UserFilter."""
        QuestionnaireResponse.objects.create(
            user=self.user,
            **SAMPLE_QUESTIONNAIRE_DATA,
        )
        make_user_filter(user=self.user, data={
            **SAMPLE_FILTER_DATA,
            "allow_check_in": "yes",
        })
        self._set_otp_session(flow="login")

        response = self.client.post(
            reverse("htsh:otp_verify"),
            {"otp": self.otp},
        )
        self.assertEqual(response.status_code, 302)

        session = self.client.session
        for key, value in SAMPLE_QUESTIONNAIRE_DATA.items():
            self.assertEqual(
                session.get(key),
                value,
                f"Session key '{key}' not restored correctly",
            )

    def test_returning_login_with_allow_check_in_sets_onboarding_complete(self, mock_timing):
        """Returning login with allow_check_in in UserFilter sets onboarding_complete in session."""
        QuestionnaireResponse.objects.create(user=self.user, **SAMPLE_QUESTIONNAIRE_DATA)
        make_user_filter(user=self.user, data={
            **SAMPLE_FILTER_DATA,
            "allow_check_in": "yes",
        })
        self._set_otp_session(flow="login")

        response = self.client.post(
            reverse("htsh:otp_verify"),
            {"otp": self.otp},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.session.get("onboarding_complete"))

    def test_returning_login_without_allow_check_in_shows_welcome_back(self, mock_timing):
        """Returning login WITHOUT allow_check_in shows 'Welcome back!' message, no onboarding_complete."""
        QuestionnaireResponse.objects.create(user=self.user, **SAMPLE_QUESTIONNAIRE_DATA)
        make_user_filter(user=self.user, data=SAMPLE_FILTER_DATA)
        self._set_otp_session(flow="login")

        response = self.client.post(
            reverse("htsh:otp_verify"),
            {"otp": self.otp},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")
        self.assertFalse(self.client.session.get("onboarding_complete", False))
        # Follow redirect and check messages via the storage
        response = self.client.get(response.url, follow=True)
        from django.contrib.messages import get_messages
        messages_list = list(get_messages(response.wsgi_request))
        welcome_found = any("Welcome back" in str(m) for m in messages_list)
        self.assertTrue(welcome_found, "Expected 'Welcome back!' info message")

    def test_returning_login_no_user_filter_redirects_to_success(self, mock_timing):
        """Returning login with no UserFilter redirects to /success."""
        self._set_otp_session(flow="login")

        response = self.client.post(
            reverse("htsh:otp_verify"),
            {"otp": self.otp},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/success")

    def test_start_auth_user_with_full_data_routes_to_listing(self, mock_timing):
        """start() for auth user with QuestionnaireResponse + UserFilter routes to listing."""
        QuestionnaireResponse.objects.create(user=self.user, **SAMPLE_QUESTIONNAIRE_DATA)
        make_user_filter(user=self.user, data={
            **SAMPLE_FILTER_DATA,
            "allow_check_in": "yes",
        })
        self.client.force_login(self.user)

        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"listing", response.content)

    def test_start_auth_user_with_partial_data_routes_to_listing(self, mock_timing):
        """start() for auth user with QuestionnaireResponse (no allow_check_in) still routes to listing."""
        QuestionnaireResponse.objects.create(user=self.user, **SAMPLE_QUESTIONNAIRE_DATA)
        self.client.force_login(self.user)

        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"listing", response.content)
