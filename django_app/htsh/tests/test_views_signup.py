"""Tests for htsh signup flow views."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from htsh.models import MagicLink, UserProfile
from htsh.services.tokens import generate_otp, hash_token
from testing.helpers import (
    make_campaign,
    make_magic_link,
    make_profile,
    make_user,
    make_user_filter,
)

User = get_user_model()


class LandingViewTests(TestCase):
    """Tests for the landing page view."""

    def test_landing_get_valid_campaign_code(self):
        """GET /landing/?cc=CODE with valid campaign redirects to /."""
        campaign = make_campaign()
        response = self.client.get(
            reverse("landing"), {"cc": campaign.campaign_code}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")
        # Campaign code stored in session
        self.assertEqual(self.client.session.get("campaign_code"), campaign.campaign_code)

    def test_landing_get_invalid_campaign_code(self):
        """GET /landing/?cc=BADCODE shows campaign_invalid."""
        response = self.client.get(
            reverse("landing"), {"cc": "BADCODE"}
        )
        self.assertEqual(response.status_code, 200)
        # Invalid code should NOT be stored in session
        self.assertNotIn("campaign_code", self.client.session)

    def test_landing_get_expired_campaign_code(self):
        """GET with expired campaign shows campaign_invalid."""
        campaign = make_campaign(
            valid_from=timezone.now().date() - timedelta(days=30),
            valid_to=timezone.now().date() - timedelta(days=1),
        )
        response = self.client.get(
            reverse("landing"), {"cc": campaign.campaign_code}
        )
        self.assertEqual(response.status_code, 200)
        # Expired campaign should NOT be stored in session
        self.assertNotIn("campaign_code", self.client.session)

    def test_landing_valid_campaign_restarts_authenticated_user_journey(self):
        """Valid campaign entry logs out authenticated user and starts fresh anonymous flow."""
        campaign = make_campaign()
        user = make_user()
        make_profile(user=user, campaign=campaign, disclaimer_accepted_at=timezone.now())
        make_user_filter(user=user, data={"details-postcode": "SW1A 1AA"})
        self.client.force_login(user)

        # Precondition: authenticated returning user sees listing journey path.
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"listing", response.content)

        # Campaign entry should force a fresh anonymous campaign journey.
        response = self.client.get(reverse("landing"), {"cc": campaign.campaign_code})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")

        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"details-postcode", response.content)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.session.get("campaign_code"), campaign.campaign_code)

    def test_landing_valid_campaign_sets_no_store_headers(self):
        """Campaign redirect responses must not be cacheable at CDN edge."""
        campaign = make_campaign(campaign_code="999999")
        response = self.client.get(reverse("landing"), {"cc": campaign.campaign_code})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Cache-Control"],
            "no-cache, no-store, must-revalidate, private",
        )
        self.assertEqual(response["Pragma"], "no-cache")
        self.assertEqual(response["Expires"], "0")

    def test_landing_invalid_campaign_sets_no_store_headers(self):
        """Campaign code error pages should not be edge-cached either."""
        response = self.client.get(reverse("landing"), {"cc": "BADCODE"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Cache-Control"],
            "no-cache, no-store, must-revalidate, private",
        )
        self.assertEqual(response["Pragma"], "no-cache")
        self.assertEqual(response["Expires"], "0")


class DisclaimerViewTests(TestCase):
    """Tests for the disclaimer view."""

    def test_disclaimer_post_accepted(self):
        """POST accepted disclaimer redirects to campaign_contact_type."""
        response = self.client.post(
            reverse("htsh:disclaimer"),
            {"disclaimer_accepted": "accepted"},
        )
        self.assertRedirects(
            response,
            reverse("htsh:campaign_contact_type"),
            fetch_redirect_response=False,
        )
        self.assertTrue(self.client.session["disclaimer_accepted"])

    def test_disclaimer_post_declined(self):
        """POST declined disclaimer redirects to details_not_shared."""
        response = self.client.post(
            reverse("htsh:disclaimer"),
            {"disclaimer_accepted": "not-accepted"},
        )
        self.assertRedirects(
            response,
            reverse("htsh:details_not_shared"),
            fetch_redirect_response=False,
        )
        self.assertFalse(self.client.session["disclaimer_accepted"])

    def test_disclaimer_post_invalid(self):
        """POST with no data returns 200 with error."""
        response = self.client.post(reverse("htsh:disclaimer"), {})
        self.assertEqual(response.status_code, 200)


class DetailsNotSharedViewTests(TestCase):
    """Tests for the details_not_shared view."""

    def test_details_not_shared_with_declined_disclaimer(self):
        """GET with disclaimer_accepted=False in session returns 200."""
        session = self.client.session
        session["disclaimer_accepted"] = False
        session.save()
        response = self.client.get(reverse("htsh:details_not_shared"))
        self.assertEqual(response.status_code, 200)

    def test_details_not_shared_without_session(self):
        """GET without session flag redirects to landing."""
        response = self.client.get(reverse("htsh:details_not_shared"))
        self.assertRedirects(
            response,
            reverse("landing"),
            fetch_redirect_response=False,
        )


class ReturningViewTests(TestCase):
    """Tests for the returning view."""

    def test_returning_post_returning(self):
        """POST returning=returning redirects to magic_link_request."""
        response = self.client.post(
            reverse("htsh:returning"),
            {"returning": "returning"},
        )
        self.assertRedirects(
            response,
            reverse("htsh:magic_link_request"),
            fetch_redirect_response=False,
        )

    def test_returning_post_first_time(self):
        """POST returning=first-time redirects to disclaimer."""
        response = self.client.post(
            reverse("htsh:returning"),
            {"returning": "first-time"},
        )
        self.assertRedirects(
            response,
            reverse("htsh:disclaimer"),
            fetch_redirect_response=False,
        )

    def test_returning_post_invalid(self):
        """POST with invalid value returns 200 with error."""
        response = self.client.post(
            reverse("htsh:returning"), {}
        )
        self.assertEqual(response.status_code, 200)


class CampaignContactTypeViewTests(TestCase):
    """Tests for the campaign_contact_type view."""

    def test_contact_type_get_without_disclaimer(self):
        """GET without disclaimer_accepted session redirects to landing."""
        response = self.client.get(reverse("htsh:campaign_contact_type"))
        self.assertRedirects(
            response,
            reverse("landing"),
            fetch_redirect_response=False,
        )

    def test_contact_type_get_with_disclaimer(self):
        """GET with disclaimer_accepted=True returns 200."""
        session = self.client.session
        session["disclaimer_accepted"] = True
        session.save()
        response = self.client.get(reverse("htsh:campaign_contact_type"))
        self.assertEqual(response.status_code, 200)

    def test_contact_type_post_email(self):
        """POST preferred_contact_method=email redirects to campaign_contact_info."""
        session = self.client.session
        session["disclaimer_accepted"] = True
        session.save()
        response = self.client.post(
            reverse("htsh:campaign_contact_type"),
            {"preferred_contact_method": "email"},
        )
        self.assertRedirects(
            response,
            reverse("htsh:campaign_contact_info"),
            fetch_redirect_response=False,
        )
        self.assertEqual(self.client.session["preferred_contact_method"], "email")

    def test_contact_type_post_sms(self):
        """POST preferred_contact_method=sms redirects to campaign_contact_info."""
        session = self.client.session
        session["disclaimer_accepted"] = True
        session.save()
        response = self.client.post(
            reverse("htsh:campaign_contact_type"),
            {"preferred_contact_method": "sms"},
        )
        self.assertRedirects(
            response,
            reverse("htsh:campaign_contact_info"),
            fetch_redirect_response=False,
        )
        self.assertEqual(self.client.session["preferred_contact_method"], "sms")

    def test_contact_type_post_invalid(self):
        """POST with empty method returns 200 with error."""
        session = self.client.session
        session["disclaimer_accepted"] = True
        session.save()
        response = self.client.post(
            reverse("htsh:campaign_contact_type"),
            {"preferred_contact_method": ""},
        )
        self.assertEqual(response.status_code, 200)


@patch("htsh.views._ensure_min_response_time")
class CampaignContactInfoViewTests(TestCase):
    """Tests for the campaign_contact_info view."""

    def setUp(self):
        self.campaign = make_campaign()
        cache.clear()

    def _set_session(self):
        """Set required session keys for campaign contact info flow."""
        session = self.client.session
        session["disclaimer_accepted"] = True
        session["preferred_contact_method"] = "email"
        session["campaign_code"] = self.campaign.campaign_code
        session.save()

    def test_contact_info_get_without_disclaimer(self, mock_timing):
        """GET without disclaimer_accepted redirects to landing."""
        response = self.client.get(reverse("htsh:campaign_contact_info"))
        self.assertRedirects(
            response,
            reverse("landing"),
            fetch_redirect_response=False,
        )

    def test_contact_info_get_without_contact_type(self, mock_timing):
        """GET with disclaimer but no preferred_contact_method redirects."""
        session = self.client.session
        session["disclaimer_accepted"] = True
        session["campaign_code"] = self.campaign.campaign_code
        session.save()
        response = self.client.get(reverse("htsh:campaign_contact_info"))
        self.assertRedirects(
            response,
            reverse("htsh:campaign_contact_type"),
            fetch_redirect_response=False,
        )

    def test_contact_info_get_valid_session(self, mock_timing):
        """GET with full session returns 200."""
        self._set_session()
        response = self.client.get(reverse("htsh:campaign_contact_info"))
        self.assertEqual(response.status_code, 200)

    @patch("htsh.views.get_email_sender")
    def test_contact_info_post_email_creates_user_and_sends_otp(
        self, mock_get_sender, mock_timing
    ):
        """POST email creates user, profile, magic link, and sends OTP."""
        mock_sender = MagicMock()
        mock_get_sender.return_value = mock_sender
        self._set_session()

        response = self.client.post(
            reverse("htsh:campaign_contact_info"),
            {"email": "newuser@example.com"},
        )
        self.assertRedirects(
            response,
            reverse("htsh:otp_verify"),
            fetch_redirect_response=False,
        )
        # User created
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())
        user = User.objects.get(email="newuser@example.com")
        # Profile created
        profile = UserProfile.objects.get(user=user)
        self.assertIsNone(profile.disclaimer_accepted_at)
        # MagicLink created
        self.assertTrue(MagicLink.objects.filter(user=user).exists())
        # OTP sent
        mock_sender.send_otp.assert_called_once()
        call_kwargs = mock_sender.send_otp.call_args
        self.assertEqual(call_kwargs[1]["email"], "newuser@example.com")

    def test_contact_info_post_invalid_email(self, mock_timing):
        """POST with invalid email returns 200 with errors."""
        self._set_session()
        response = self.client.post(
            reverse("htsh:campaign_contact_info"),
            {"email": "not-an-email"},
        )
        self.assertEqual(response.status_code, 200)

    @patch("htsh.views.get_email_sender")
    def test_contact_info_rate_limited(self, mock_get_sender, mock_timing):
        """POST when rate limited returns 200 with rate limit error."""
        self._set_session()
        # Pre-set rate limit counter at the limit
        cache.set("htsh:otp_gen:ratelimit@example.com", 3, timeout=3600)

        response = self.client.post(
            reverse("htsh:campaign_contact_info"),
            {"email": "ratelimit@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Too many requests", str(response.content))


@patch("htsh.views._ensure_min_response_time")
class OtpVerifyViewTests(TestCase):
    """Tests for the otp_verify view."""

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
        """Set OTP session keys."""
        session = self.client.session
        session["otp_user_id"] = self.user.id
        session["otp_flow"] = flow
        session["otp_contact"] = self.profile.email
        session["otp_is_email"] = True
        session.save()

    def test_otp_verify_get_renders_form(self, mock_timing):
        """GET /otp/ with valid session returns 200."""
        self._set_otp_session()
        response = self.client.get(reverse("htsh:otp_verify"))
        self.assertEqual(response.status_code, 200)

    def test_otp_verify_get_no_session_redirects(self, mock_timing):
        """GET with empty session redirects to landing."""
        response = self.client.get(reverse("htsh:otp_verify"))
        self.assertRedirects(
            response,
            reverse("landing"),
            fetch_redirect_response=False,
        )

    def test_otp_verify_post_valid_otp(self, mock_timing):
        """POST with valid OTP logs user in and redirects."""
        self._set_otp_session()
        response = self.client.post(
            reverse("htsh:otp_verify"),
            {"otp": self.otp},
        )
        self.assertEqual(response.status_code, 302)
        # MagicLink should be marked as used
        self.magic_link.refresh_from_db()
        self.assertIsNotNone(self.magic_link.used_at)

    def test_otp_verify_post_invalid_otp(self, mock_timing):
        """POST with invalid OTP returns 200 with form error."""
        self._set_otp_session()
        response = self.client.post(
            reverse("htsh:otp_verify"),
            {"otp": "000000"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Invalid or expired", str(response.content))

    def test_otp_verify_post_expired_otp(self, mock_timing):
        """POST with expired MagicLink returns 200 with error."""
        self.magic_link.expires_at = timezone.now() - timedelta(minutes=1)
        self.magic_link.save()
        self._set_otp_session()
        response = self.client.post(
            reverse("htsh:otp_verify"),
            {"otp": self.otp},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Invalid or expired", str(response.content))

    def test_otp_verify_lockout_after_5_attempts(self, mock_timing):
        """5 invalid OTP attempts triggers lockout page."""
        self._set_otp_session()
        for _ in range(5):
            response = self.client.post(
                reverse("htsh:otp_verify"),
                {"otp": "000000"},
            )
        # 5th attempt should render lockout page
        self.assertEqual(response.status_code, 200)
        self.assertIn("too many attempts", response.content.decode().lower())

    def test_otp_verify_clears_attempts_on_success(self, mock_timing):
        """Successful OTP clears attempt counter from cache."""
        # Set some failed attempts
        cache.set(f"htsh:otp_attempts:{self.user.id}", 3, timeout=900)
        self._set_otp_session()
        self.client.post(
            reverse("htsh:otp_verify"),
            {"otp": self.otp},
        )
        # Attempt counter should be cleared
        self.assertIsNone(cache.get(f"htsh:otp_attempts:{self.user.id}"))

    def test_otp_verify_signup_flow_sets_disclaimer(self, mock_timing):
        """OTP success in signup flow sets disclaimer_accepted_at on profile."""
        # Create profile without disclaimer
        self.profile.disclaimer_accepted_at = None
        self.profile.save()
        self._set_otp_session(flow="signup")
        self.client.post(
            reverse("htsh:otp_verify"),
            {"otp": self.otp},
        )
        self.profile.refresh_from_db()
        self.assertIsNotNone(self.profile.disclaimer_accepted_at)


@patch("htsh.views._ensure_min_response_time")
class InterstitialSignupSessionMigrationTests(TestCase):
    """Tests for session data migration during interstitial signup OTP verify."""

    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.profile = make_profile(
            user=self.user,
            disclaimer_accepted_at=None,
        )
        self.otp = generate_otp()
        MagicLink.objects.create(
            user=self.user,
            token_hash=hash_token(self.otp),
            expires_at=timezone.now() + timedelta(minutes=15),
        )

    def _set_otp_session(self, **extra):
        """Set OTP session keys for signup flow with questionnaire data."""
        session = self.client.session
        session["otp_user_id"] = self.user.id
        session["otp_flow"] = "signup"
        session["otp_contact"] = self.profile.email
        session["otp_is_email"] = True
        session["disclaimer_accepted"] = True
        # Questionnaire session data (new schema)
        session["motivation"] = "motivation.want_to_feel_better"
        session["priority_behaviour"] = "priority_behaviour.more_physically_active"
        session["past_barriers"] = ["past_barriers.no_time"]
        session["current_barriers"] = ["current_barriers.short_on_time"]
        session["confidence_readiness"] = "confidence_readiness.ready_and_confident"
        session["enablers"] = ["enablers.affordable"]
        session["details-postcode"] = "SW1A 1AA"
        for k, v in extra.items():
            session[k] = v
        session.save()

    def test_signup_migrates_session_to_questionnaire_response(self, mock_timing):
        """OTP signup migrates questionnaire session data to QuestionnaireResponse."""
        self._set_otp_session()
        self.client.post(
            reverse("htsh:otp_verify"),
            {"otp": self.otp},
        )
        from htsh.models import QuestionnaireResponse

        qr = QuestionnaireResponse.objects.get(user=self.user)
        self.assertEqual(qr.motivation, "motivation.want_to_feel_better")
        self.assertEqual(qr.priority_behaviour, "priority_behaviour.more_physically_active")
        self.assertEqual(qr.past_barriers, ["past_barriers.no_time"])
        self.assertEqual(qr.current_barriers, ["current_barriers.short_on_time"])
        self.assertEqual(qr.confidence_readiness, "confidence_readiness.ready_and_confident")
        self.assertEqual(qr.enablers, ["enablers.affordable"])

    def test_interstitial_signup_redirects_to_allow_check_in(self, mock_timing):
        """OTP signup with account_prompt_service_id → redirect to /allow-check-in."""
        self._set_otp_session(account_prompt_service_id=42)
        response = self.client.post(
            reverse("htsh:otp_verify"),
            {"otp": self.otp},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/allow-check-in", response.url)

    def test_standard_signup_redirects_to_success(self, mock_timing):
        """OTP signup without account_prompt_service_id → redirect to /success."""
        self._set_otp_session()
        response = self.client.post(
            reverse("htsh:otp_verify"),
            {"otp": self.otp},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/success", response.url)
