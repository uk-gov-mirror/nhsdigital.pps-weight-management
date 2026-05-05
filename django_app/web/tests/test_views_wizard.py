"""Tests for web wizard step views (start through allow-check-in, success, no-check-in)."""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from htsh.models import UserProfile, QuestionnaireResponse
from testing.helpers import make_profile, make_user, make_user_filter
from testing.mocks import mock_postcodes_io

User = get_user_model()


class _AuthenticatedTestCase(TestCase):
    """Base class that logs in a user with a completed pilot profile (middleware passes)."""

    def setUp(self):
        self.user = make_user()
        self.profile = make_profile(
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

    def test_start_authenticated_no_data(self):
        """GET / with logged-in user and no data defaults start_href to details-contact-details."""
        user = make_user()
        make_profile(user=user, disclaimer_accepted_at=timezone.now())
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"details-contact-details", response.content)

    def test_start_authenticated_with_questionnaire_response(self):
        """GET / with user who has QuestionnaireResponse routes to listing."""
        user = make_user()
        make_profile(user=user, disclaimer_accepted_at=timezone.now())
        QuestionnaireResponse.objects.create(
            user=user,
            motivation="motivation.want_to_feel_better",
        )
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"listing", response.content)

    def test_start_shows_human_readable_past_barriers_summary(self):
        """GET / shows selected past barrier text, not the stored enum-like value."""
        user = make_user()
        make_profile(user=user, disclaimer_accepted_at=timezone.now())
        QuestionnaireResponse.objects.create(
            user=user,
            motivation="motivation.want_to_feel_better",
            past_barriers=["past_barriers.didnt_know_where_to_start"],
        )
        self.client.force_login(user)

        session = self.client.session
        session["onboarding_complete"] = True
        session.save()

        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"past_barriers.didnt_know_where_to_start", response.content)
        self.assertIn(b"I didn&#39;t know what to do or where to start", response.content)

    def test_start_authenticated_with_filter_data(self):
        """GET / with user who has UserFilter data routes to listing."""
        user = make_user()
        make_profile(user=user, disclaimer_accepted_at=timezone.now())
        make_user_filter(user=user, data={"allow_check_in": "yes"})
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"listing", response.content)

    def test_start_magiclink_flow(self):
        """GET / with session entry_flow=magiclink routes to listing."""
        user = make_user()
        make_profile(user=user, disclaimer_accepted_at=timezone.now())
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
        self.user = make_user(email="orig@test.com")
        self.profile = make_profile(
            user=self.user,
            disclaimer_accepted_at=timezone.now(),
        )
        self.client.force_login(self.user)
        self.url = reverse("details_contact_details")

    def test_get_renders_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_valid_email_preference(self):
        response = self.client.post(self.url, {
            "email": "new@test.com",
            "phone": "",
            "preferred_contact_method": UserProfile.CONTACT_EMAIL,
        })
        self.assertRedirects(
            response, reverse("questionnaire_intro"), fetch_redirect_response=False,
        )

    def test_post_valid_sms_preference(self):
        response = self.client.post(self.url, {
            "email": "",
            "phone": "07700900123",
            "preferred_contact_method": UserProfile.CONTACT_SMS,
        })
        self.assertRedirects(
            response, reverse("questionnaire_intro"), fetch_redirect_response=False,
        )

    def test_post_invalid_no_preference(self):
        response = self.client.post(self.url, {
            "email": "", "phone": "", "preferred_contact_method": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Please choose a preferred contact method", response.content)

    def test_post_invalid_email(self):
        response = self.client.post(self.url, {
            "email": "notanemail", "phone": "",
            "preferred_contact_method": UserProfile.CONTACT_EMAIL,
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"valid email", response.content)

    def test_post_invalid_phone(self):
        response = self.client.post(self.url, {
            "email": "", "phone": "abc",
            "preferred_contact_method": UserProfile.CONTACT_SMS,
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"valid mobile", response.content)

    def test_post_duplicate_email(self):
        make_user(email="taken@test.com")
        response = self.client.post(self.url, {
            "email": "taken@test.com", "phone": "",
            "preferred_contact_method": UserProfile.CONTACT_EMAIL,
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"already in use", response.content)


class DetailsPostcodeViewTests(_AuthenticatedTestCase):
    """Tests for the details-postcode step."""

    def setUp(self):
        super().setUp()
        self.url = reverse("details_postcode")

    def test_get_renders_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    @mock_postcodes_io(is_valid=True)
    def test_post_valid_postcode(self, mock_get):
        """POST with valid postcode redirects to motivation page."""
        response = self.client.post(self.url, {"details-postcode": "SW1A 1AA"})
        self.assertRedirects(
            response, reverse("motivation"), fetch_redirect_response=False
        )

    def test_post_invalid_format(self):
        response = self.client.post(self.url, {"details-postcode": "NOTAPC"})
        self.assertEqual(response.status_code, 200)

    @mock_postcodes_io(is_valid=False)
    def test_post_api_invalid(self, mock_get):
        response = self.client.post(self.url, {"details-postcode": "SW1A 1AA"})
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# Questionnaire Q1–Q6 views
# ---------------------------------------------------------------------------


class QuestionnaireIntroViewTests(_AuthenticatedTestCase):
    """Tests for pre-postcode context screen before Q1."""

    def test_get_renders(self):
        response = self.client.get(reverse("questionnaire_intro"))
        self.assertEqual(response.status_code, 200)

    def test_post_redirects_to_details_postcode(self):
        response = self.client.post(reverse("questionnaire_intro"))
        self.assertRedirects(
            response, reverse("details_postcode"), fetch_redirect_response=False
        )


class MotivationViewTests(_AuthenticatedTestCase):
    """Tests for Q1 motivation (single-select radios)."""

    def test_get_renders(self):
        response = self.client.get(reverse("motivation"))
        self.assertEqual(response.status_code, 200)

    def test_post_valid_stores_and_redirects(self):
        response = self.client.post(
            reverse("motivation"), {"motivation": "motivation.want_to_feel_better"}
        )
        self.assertRedirects(
            response, reverse("priority_behaviour"), fetch_redirect_response=False
        )
        self.assertEqual(
            self.client.session["motivation"], "motivation.want_to_feel_better"
        )

    def test_post_empty_shows_error(self):
        response = self.client.post(reverse("motivation"), {})
        self.assertEqual(response.status_code, 200)

    def test_edit_mode_redirects_home(self):
        response = self.client.post(
            reverse("motivation") + "?mode=edit",
            {"motivation": "motivation.tried_before"},
        )
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_post_persists_to_questionnaire_response(self):
        self.client.post(
            reverse("motivation"), {"motivation": "motivation.health_scare"}
        )
        qr = QuestionnaireResponse.objects.get(user=self.user)
        self.assertEqual(qr.motivation, "motivation.health_scare")


class PriorityBehaviourViewTests(_AuthenticatedTestCase):
    """Tests for Q2 priority_behaviour (single-select radios)."""

    def test_get_renders(self):
        response = self.client.get(reverse("priority_behaviour"))
        self.assertEqual(response.status_code, 200)

    def test_post_valid_stores_and_redirects(self):
        response = self.client.post(
            reverse("priority_behaviour"),
            {"priority_behaviour": "priority_behaviour.more_physically_active"},
        )
        self.assertRedirects(
            response, reverse("past_barriers"), fetch_redirect_response=False
        )

    def test_post_empty_shows_error(self):
        response = self.client.post(reverse("priority_behaviour"), {})
        self.assertEqual(response.status_code, 200)


class PastBarriersViewTests(_AuthenticatedTestCase):
    """Tests for Q3 past_barriers (multi-select checkboxes)."""

    def test_get_renders(self):
        response = self.client.get(reverse("past_barriers"))
        self.assertEqual(response.status_code, 200)

    def test_post_valid_stores_and_redirects(self):
        response = self.client.post(
            reverse("past_barriers"),
            {"past_barriers": ["past_barriers.no_time", "past_barriers.too_expensive"]},
        )
        self.assertRedirects(
            response, reverse("current_barriers"), fetch_redirect_response=False
        )
        self.assertEqual(
            self.client.session["past_barriers"],
            ["past_barriers.no_time", "past_barriers.too_expensive"],
        )

    def test_post_empty_shows_error(self):
        response = self.client.post(reverse("past_barriers"), {})
        self.assertEqual(response.status_code, 200)


class CurrentBarriersViewTests(_AuthenticatedTestCase):
    """Tests for Q4 current_barriers (multi-select checkboxes)."""

    def test_get_renders(self):
        response = self.client.get(reverse("current_barriers"))
        self.assertEqual(response.status_code, 200)

    def test_post_valid_stores_and_redirects(self):
        response = self.client.post(
            reverse("current_barriers"),
            {"current_barriers": ["current_barriers.short_on_time"]},
        )
        self.assertRedirects(
            response, reverse("confidence_readiness"), fetch_redirect_response=False
        )

    def test_post_empty_shows_error(self):
        response = self.client.post(reverse("current_barriers"), {})
        self.assertEqual(response.status_code, 200)


class ConfidenceReadinessViewTests(_AuthenticatedTestCase):
    """Tests for Q5 confidence_readiness (single-select radios)."""

    def test_get_renders(self):
        response = self.client.get(reverse("confidence_readiness"))
        self.assertEqual(response.status_code, 200)

    def test_post_valid_stores_and_redirects(self):
        response = self.client.post(
            reverse("confidence_readiness"),
            {"confidence_readiness": "confidence_readiness.ready_and_confident"},
        )
        self.assertRedirects(
            response, reverse("enablers"), fetch_redirect_response=False
        )

    def test_post_empty_shows_error(self):
        response = self.client.post(reverse("confidence_readiness"), {})
        self.assertEqual(response.status_code, 200)


class EnablersViewTests(_AuthenticatedTestCase):
    """Tests for Q6 enablers (multi-select checkboxes)."""

    def test_get_renders(self):
        response = self.client.get(reverse("enablers"))
        self.assertEqual(response.status_code, 200)

    def test_post_valid_redirects_to_home_summary(self):
        response = self.client.post(
            reverse("enablers"), {"enablers": ["enablers.affordable"]},
        )
        self.assertRedirects(
            response, reverse("home"), fetch_redirect_response=False
        )

    def test_post_empty_shows_error(self):
        response = self.client.post(reverse("enablers"), {})
        self.assertEqual(response.status_code, 200)

    def test_edit_mode_redirects_home(self):
        response = self.client.post(
            reverse("enablers") + "?mode=edit",
            {"enablers": ["enablers.clear_guidance"]},
        )
        self.assertRedirects(response, "/", fetch_redirect_response=False)


class AllowCheckInViewTests(_AuthenticatedTestCase):
    """Tests for the allow-check-in step."""

    def setUp(self):
        super().setUp()
        self.url = reverse("allow-check-in")

    def test_get_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    @patch("web.views.requests.post")
    def test_post_yes(self, mock_post):
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
        response = self.client.post(self.url, {"allow_check_in": "no"})
        self.assertRedirects(
            response, reverse("no_check_in"), fetch_redirect_response=False,
        )
        self.assertTrue(self.client.session.get("onboarding_complete"))

    def test_post_invalid(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# Anonymous campaign user tests
# ---------------------------------------------------------------------------


class _AnonymousCampaignTestCase(TestCase):
    """Base class for anonymous users with valid campaign session."""

    def setUp(self):
        session = self.client.session
        session["campaign_code"] = "TESTCAMP"
        session.save()


class AnonymousStartViewTests(_AnonymousCampaignTestCase):

    def test_start_anonymous_with_campaign_shows_questionnaire_intro_href(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"questionnaire-intro", response.content)

    def test_start_anonymous_with_campaign_no_contact_details(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'href="/details-contact-details"', response.content)


class AnonymousDetailsPostcodeTests(_AnonymousCampaignTestCase):

    def test_get_renders(self):
        response = self.client.get(reverse("details_postcode"))
        self.assertEqual(response.status_code, 200)

    @mock_postcodes_io(is_valid=True)
    def test_post_valid_postcode_redirects_to_motivation(self, mock_get):
        response = self.client.post(
            reverse("details_postcode"), {"details-postcode": "SW1A 1AA"}
        )
        self.assertRedirects(
            response, reverse("motivation"), fetch_redirect_response=False
        )

    @mock_postcodes_io(is_valid=True)
    def test_post_does_not_persist_to_user_filter(self, mock_get):
        from htsh.models import UserFilter
        self.client.post(
            reverse("details_postcode"), {"details-postcode": "SW1A 1AA"}
        )
        self.assertEqual(UserFilter.objects.count(), 0)


class AnonymousMotivationTests(_AnonymousCampaignTestCase):

    def test_get_renders(self):
        response = self.client.get(reverse("motivation"))
        self.assertEqual(response.status_code, 200)

    def test_post_valid_redirects_to_priority_behaviour(self):
        response = self.client.post(
            reverse("motivation"), {"motivation": "motivation.want_to_feel_better"}
        )
        self.assertRedirects(
            response, reverse("priority_behaviour"), fetch_redirect_response=False
        )


class AnonymousPastBarriersTests(_AnonymousCampaignTestCase):

    def test_get_renders(self):
        response = self.client.get(reverse("past_barriers"))
        self.assertEqual(response.status_code, 200)

    def test_post_valid_redirects_to_current_barriers(self):
        response = self.client.post(
            reverse("past_barriers"), {"past_barriers": ["past_barriers.no_time"]}
        )
        self.assertRedirects(
            response, reverse("current_barriers"), fetch_redirect_response=False
        )


class AnonymousEnablersTests(_AnonymousCampaignTestCase):

    def test_post_redirects_to_home_summary(self):
        response = self.client.post(
            reverse("enablers"), {"enablers": ["enablers.affordable"]}
        )
        self.assertRedirects(
            response, reverse("home"), fetch_redirect_response=False
        )

    def test_post_sets_onboarding_complete(self):
        self.client.post(
            reverse("enablers"), {"enablers": ["enablers.affordable"]}
        )
        self.assertTrue(self.client.session.get("onboarding_complete"))

    def test_post_does_not_redirect_to_allow_check_in(self):
        response = self.client.post(
            reverse("enablers"), {"enablers": ["enablers.affordable"]}
        )
        self.assertNotIn("allow-check-in", response.url)


class AuthenticatedEnablersTests(_AuthenticatedTestCase):

    def test_post_redirects_to_home_summary(self):
        response = self.client.post(
            reverse("enablers"), {"enablers": ["enablers.affordable"]}
        )
        self.assertRedirects(
            response, reverse("home"), fetch_redirect_response=False
        )
