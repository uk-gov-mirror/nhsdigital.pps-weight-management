"""Tests for returning anonymous user flows (RET-02).

Verifies that anonymous users with a campaign session start fresh (no stale
wizard data) and that users without a campaign code are redirected by middleware.
"""

from django.test import TestCase
from django.urls import reverse

from testing.helpers import make_campaign
from web.views import PERSISTED_SESSION_KEYS


class ReturningAnonymousUserTests(TestCase):
    """Tests for returning anonymous user behaviour."""

    def setUp(self):
        self.campaign = make_campaign()
        session = self.client.session
        session["campaign_code"] = self.campaign.campaign_code
        session.save()

    def test_anonymous_with_campaign_routes_to_questionnaire_intro(self):
        """Fresh anonymous session with campaign_code routes start_href to questionnaire-intro."""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"questionnaire-intro", response.content)

    def test_anonymous_with_campaign_has_no_persisted_keys(self):
        """Fresh anonymous session with campaign_code has no PERSISTED_SESSION_KEYS values."""
        self.client.get(reverse("home"))
        session = self.client.session
        for key in PERSISTED_SESSION_KEYS:
            self.assertNotIn(
                key,
                session,
                f"Session key '{key}' should not be present in a fresh anonymous session",
            )

    def test_anonymous_without_campaign_redirects(self):
        """Anonymous user without campaign_code is redirected by middleware (302)."""
        # Flush session to remove campaign_code
        self.client.session.flush()
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("landing", response.url)

    def test_anonymous_expired_session_starts_fresh(self):
        """Anonymous user who returns after session expiry starts fresh with no stale wizard keys."""
        # Simulate a user who previously completed the questionnaire
        session = self.client.session
        session["goals"] = ["lose-weight"]
        session["barriers"] = ["cost"]
        session["who_with"] = ["alone"]
        session["timetable"] = ["weekdays"]
        session["channel"] = ["online"]
        session["details-postcode"] = "SW1A 1AA"
        session.save()

        # Simulate session expiry: clear cookies and start fresh with only campaign_code
        self.client.cookies.clear()
        # Establish a new session by visiting landing with campaign code
        response = self.client.get(
            reverse("landing"),
            {"cc": self.campaign.campaign_code},
        )
        self.assertEqual(response.status_code, 302)

        # Visit start page with the new campaign session
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

        # Verify no stale wizard keys remain
        session = self.client.session
        for key in PERSISTED_SESSION_KEYS:
            self.assertNotIn(
                key,
                session,
                f"Stale session key '{key}' should not persist after session expiry",
            )
