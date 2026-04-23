"""Tests for htsh account management views."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from htsh.models import MagicLink, UserProfile
from htsh.services.tokens import generate_otp, hash_token
from testing.helpers import make_magic_link, make_profile, make_user

User = get_user_model()


@patch("htsh.views._ensure_min_response_time")
class MagicLinkRequestViewTests(TestCase):
    """Tests for the magic_link_request view (login flow)."""

    def setUp(self):
        self.user = make_user()
        self.profile = make_profile(
            user=self.user,
            email="test@example.com",
            disclaimer_accepted_at=timezone.now(),
        )
        cache.clear()

    @patch("htsh.views.get_email_sender")
    def test_magic_link_post_valid_email_sends_otp(
        self, mock_get_sender, mock_timing
    ):
        """POST valid email sends OTP and redirects to otp_verify."""
        mock_sender = MagicMock()
        mock_get_sender.return_value = mock_sender

        response = self.client.post(
            reverse("htsh:magic_link_request"),
            {"contact": "test@example.com"},
        )
        self.assertRedirects(
            response,
            reverse("htsh:otp_verify"),
            fetch_redirect_response=False,
        )
        mock_sender.send_otp.assert_called_once()
        self.assertTrue(MagicLink.objects.filter(user=self.user).exists())
        self.assertEqual(self.client.session["otp_user_id"], self.user.id)

    def test_magic_link_post_unknown_contact_still_redirects(self, mock_timing):
        """POST unknown contact redirects to otp_verify (no error revealed)."""
        response = self.client.post(
            reverse("htsh:magic_link_request"),
            {"contact": "nobody@example.com"},
        )
        self.assertRedirects(
            response,
            reverse("htsh:otp_verify"),
            fetch_redirect_response=False,
        )
        # No MagicLink created for unknown contact
        self.assertFalse(
            MagicLink.objects.filter(
                user__email="nobody@example.com"
            ).exists()
        )

    def test_magic_link_post_rate_limited_contact(self, mock_timing):
        """POST rate limited contact redirects without sending OTP."""
        cache.set("htsh:otp_gen:test@example.com", 3, timeout=3600)
        response = self.client.post(
            reverse("htsh:magic_link_request"),
            {"contact": "test@example.com"},
        )
        self.assertRedirects(
            response,
            reverse("htsh:otp_verify"),
            fetch_redirect_response=False,
        )
        # No new MagicLink created
        self.assertFalse(MagicLink.objects.filter(user=self.user).exists())

    @patch("htsh.views.get_email_sender")
    def test_magic_link_invalidates_previous_otps(
        self, mock_get_sender, mock_timing
    ):
        """POST valid email invalidates existing unused OTPs."""
        mock_sender = MagicMock()
        mock_get_sender.return_value = mock_sender

        # Create an existing MagicLink
        old_ml = make_magic_link(user=self.user)
        self.assertIsNone(old_ml.used_at)

        self.client.post(
            reverse("htsh:magic_link_request"),
            {"contact": "test@example.com"},
        )
        old_ml.refresh_from_db()
        self.assertIsNotNone(old_ml.used_at)


class LogoutViewTests(TestCase):
    """Tests for the logout_post view."""

    def setUp(self):
        self.user = make_user()
        make_profile(
            user=self.user, disclaimer_accepted_at=timezone.now()
        )

    def test_logout_post_redirects_to_landing(self):
        """POST /logout/ logs out and redirects to landing."""
        self.client.force_login(self.user)
        response = self.client.post(reverse("htsh:logout"))
        self.assertRedirects(
            response,
            reverse("landing"),
            fetch_redirect_response=False,
        )

    def test_logout_get_not_allowed(self):
        """GET /logout/ returns 405 (require_POST)."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("htsh:logout"))
        self.assertEqual(response.status_code, 405)


class AccountViewTests(TestCase):
    """Tests for the account view."""

    def setUp(self):
        self.user = make_user()
        self.profile = make_profile(
            user=self.user,
            email="account@example.com",
            disclaimer_accepted_at=timezone.now(),
        )
        self.client.force_login(self.user)

    def test_account_post_with_unsafe_next_url(self):
        """POST with unsafe next URL ignores it."""
        response = self.client.post(
            reverse("htsh:account"),
            {
                "email": "account@example.com",
                "phone": "07700900000",
                "postcode": "SW1A 1AA",
                "preferred_contact_method": "email",
                "next": "http://evil.com/",
            },
        )
        # Should redirect to account page, not evil.com
        self.assertRedirects(
            response,
            reverse("htsh:account"),
            fetch_redirect_response=False,
        )


class DeleteAccountViewTests(TestCase):
    """Tests for the delete_account view."""

    def setUp(self):
        self.user = make_user()
        self.profile = make_profile(
            user=self.user, disclaimer_accepted_at=timezone.now()
        )
        self.client.force_login(self.user)

    def test_delete_account_get_renders(self):
        """GET /account/delete/ returns 200."""
        response = self.client.get(reverse("htsh:delete_account"))
        self.assertEqual(response.status_code, 200)

    def test_delete_account_post_deletes_and_redirects(self):
        """POST confirmation deletes user and redirects to landing."""
        user_id = self.user.id
        response = self.client.post(
            reverse("htsh:delete_account"),
            {"confirm": True},
        )
        self.assertRedirects(
            response,
            reverse("landing"),
            fetch_redirect_response=False,
        )
        self.assertFalse(User.objects.filter(id=user_id).exists())

    def test_delete_account_post_invalid_form(self):
        """POST without confirmation returns 200."""
        response = self.client.post(
            reverse("htsh:delete_account"), {}
        )
        self.assertEqual(response.status_code, 200)
        # User still exists
        self.assertTrue(User.objects.filter(id=self.user.id).exists())
