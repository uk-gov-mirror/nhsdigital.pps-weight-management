"""Tests for web listing and detail views (API-backed with mocked internal API)."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from htsh.models import QuestionnaireResponse
from testing.helpers import make_profile, make_user


class _AuthenticatedTestCase(TestCase):
    """Base class that logs in a user with a completed pilot profile."""

    def setUp(self):
        self.user = make_user()
        self.profile = make_profile(
            user=self.user,
            disclaimer_accepted_at=timezone.now(),
        )
        self.client.force_login(self.user)


def _mock_response(data, status=200):
    """Return a MagicMock imitating a requests.Response."""
    resp = MagicMock()
    resp.status_code = status
    resp.ok = 200 <= status < 300
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    resp.text = ""
    return resp


@override_settings(SERVICE_API_BASE_URL="http://testserver")
class ListingViewTests(_AuthenticatedTestCase):
    """Tests for the listing view (calls internal V3 API via requests.post)."""

    def setUp(self):
        super().setUp()
        self.url = reverse("listing")
        # Listing needs a session postcode to work properly
        session = self.client.session
        session["details-postcode"] = "SW1A 1AA"
        session.save()

    @patch("web.views.requests.post")
    def test_get_renders_with_empty_results(self, mock_post):
        """GET listing with empty API results returns 200."""
        mock_post.return_value = _mock_response({"total": 0, "results": []})
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    @patch("web.views.requests.post")
    def test_get_renders_with_results(self, mock_post):
        """GET listing with results returns 200."""
        mock_post.return_value = _mock_response({
            "total": 2,
            "results": [
                {"id": 1, "serviceName": "Service A"},
                {"id": 2, "serviceName": "Service B"},
            ],
        })
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    @patch("web.views.requests.post")
    def test_post_applies_filters(self, mock_post):
        """POST with filter values calls API with those filters."""
        mock_post.return_value = _mock_response({"total": 0, "results": []})
        self.client.post(self.url, {"goals": ["lose_weight"]})
        self.assertTrue(mock_post.called)
        payload = mock_post.call_args[1]["json"]
        self.assertIn("filter", payload)

    @patch("web.views.requests.post")
    def test_post_pagination_params(self, mock_post):
        """POST with page=2, page_size=5 sends correct offset."""
        mock_post.return_value = _mock_response({"total": 20, "results": []})
        self.client.post(self.url, {"page": "2", "page_size": "5"})
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["limit"], 5)
        self.assertEqual(payload["offset"], 5)

    @patch("web.views.requests.post")
    def test_post_distance_param(self, mock_post):
        """POST with distance=10 includes distance in payload."""
        mock_post.return_value = _mock_response({"total": 0, "results": []})
        self.client.post(self.url, {"distance": "10"})
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["distance"], 10)

    @patch("web.views.requests.post")
    def test_api_http_error(self, mock_post):
        """HTTP error from raise_for_status renders gracefully with api_error."""
        import requests as real_requests
        resp = _mock_response(None, status=500)
        resp.raise_for_status.side_effect = real_requests.HTTPError("500 Server Error")
        mock_post.return_value = resp
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    @patch("web.views.requests.post")
    def test_api_connection_error(self, mock_post):
        """Connection error from API renders gracefully."""
        import requests as real_requests
        mock_post.side_effect = real_requests.RequestException("Connection refused")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    @patch("web.views.requests.post")
    def test_api_invalid_json(self, mock_post):
        """Invalid JSON from API renders gracefully."""
        resp = _mock_response(None)
        resp.json.side_effect = ValueError("No JSON")
        mock_post.return_value = resp
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)


@override_settings(SERVICE_API_BASE_URL="http://testserver")
class DetailViewTests(_AuthenticatedTestCase):
    """Tests for the detail view (calls internal V3 API via requests.get)."""

    @patch("web.views.requests.get")
    def test_valid_service(self, mock_get):
        """GET detail with valid API response returns 200."""
        mock_get.return_value = _mock_response({
            "id": 1,
            "serviceName": "Test Service",
            "description": "A unique test service description",
        })
        response = self.client.get(reverse("detail", kwargs={"service_id": 1}))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Service", response.content)

    @patch("web.views.requests.get")
    def test_api_error_raises_404(self, mock_get):
        """API RequestException raises 404."""
        import requests as real_requests
        mock_get.side_effect = real_requests.RequestException("Connection error")
        response = self.client.get(reverse("detail", kwargs={"service_id": 999}))
        self.assertEqual(response.status_code, 404)

    @patch("web.views.requests.get")
    def test_invalid_json_raises_404(self, mock_get):
        """Invalid JSON from API raises 404."""
        resp = _mock_response(None)
        resp.json.side_effect = ValueError("No JSON")
        mock_get.return_value = resp
        # detail() calls resp.json() inside try block; ValueError → Http404
        response = self.client.get(reverse("detail", kwargs={"service_id": 1}))
        self.assertEqual(response.status_code, 404)

    @patch("web.views.requests.get")
    def test_http_error_raises_404(self, mock_get):
        """HTTP error from raise_for_status raises 404."""
        import requests as real_requests
        resp = _mock_response(None, status=500)
        resp.raise_for_status.side_effect = real_requests.HTTPError("500")
        mock_get.return_value = resp
        response = self.client.get(reverse("detail", kwargs={"service_id": 1}))
        self.assertEqual(response.status_code, 404)


class _AnonymousCampaignTestCase(TestCase):
    """Base for anonymous users with valid campaign session."""

    def setUp(self):
        session = self.client.session
        session["campaign_code"] = "TESTCAMP"
        session.save()


@override_settings(SERVICE_API_BASE_URL="http://testserver")
class AnonymousListingViewTests(_AnonymousCampaignTestCase):
    """Tests for the listing view with anonymous campaign users."""

    def setUp(self):
        super().setUp()
        session = self.client.session
        session["details-postcode"] = "SW1A 1AA"
        session.save()

    @patch("web.views.requests.post")
    def test_get_renders_with_empty_results(self, mock_post):
        """GET /listing as anonymous campaign user → 200."""
        mock_post.return_value = _mock_response({"total": 0, "results": []})
        response = self.client.get(reverse("listing"))
        self.assertEqual(response.status_code, 200)

    @patch("web.views.requests.post")
    def test_post_applies_filters(self, mock_post):
        """POST /listing with filter values as anonymous → 200."""
        mock_post.return_value = _mock_response({"total": 0, "results": []})
        response = self.client.post(reverse("listing"), {"goals": ["lose_weight"]})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_post.called)


@override_settings(SERVICE_API_BASE_URL="http://testserver")
class ListingActivityAttributeTests(_AuthenticatedTestCase):
    """Tests for activity_attributes passed from listing view to API."""

    def setUp(self):
        super().setUp()
        self.url = reverse("listing")
        session = self.client.session
        session["details-postcode"] = "SW1A 1AA"
        session.save()

    @patch("web.views.requests.post")
    def test_listing_sends_activity_attributes_when_questionnaire_exists(self, mock_post):
        """Authenticated user with QuestionnaireResponse sends activity_attributes in API payload."""
        mock_post.return_value = _mock_response({"total": 0, "results": []})
        QuestionnaireResponse.objects.create(
            user=self.user,
            activity_attributes=["Cost", "Social setting"],
        )
        self.client.get(self.url)
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["activity_attributes"], ["Cost", "Social setting"])

    @patch("web.views.requests.post")
    def test_listing_omits_activity_attributes_when_no_questionnaire(self, mock_post):
        """Authenticated user without QuestionnaireResponse omits activity_attributes."""
        mock_post.return_value = _mock_response({"total": 0, "results": []})
        self.client.get(self.url)
        payload = mock_post.call_args[1]["json"]
        self.assertNotIn("activity_attributes", payload)

    @patch("web.views.requests.post")
    def test_listing_handles_empty_activity_attributes(self, mock_post):
        """QuestionnaireResponse with empty activity_attributes omits field from payload."""
        mock_post.return_value = _mock_response({"total": 0, "results": []})
        QuestionnaireResponse.objects.create(
            user=self.user,
            activity_attributes=[],
        )
        self.client.get(self.url)
        payload = mock_post.call_args[1]["json"]
        self.assertNotIn("activity_attributes", payload)


@override_settings(SERVICE_API_BASE_URL="http://testserver")
class AnonymousListingActivityAttributeTests(_AnonymousCampaignTestCase):
    """Tests for activity_attributes with anonymous users."""

    def setUp(self):
        super().setUp()
        session = self.client.session
        session["details-postcode"] = "SW1A 1AA"
        session.save()

    @patch("web.views.requests.post")
    def test_anonymous_listing_omits_activity_attributes(self, mock_post):
        """Anonymous campaign user does not send activity_attributes."""
        mock_post.return_value = _mock_response({"total": 0, "results": []})
        self.client.get(reverse("listing"))
        payload = mock_post.call_args[1]["json"]
        self.assertNotIn("activity_attributes", payload)


@override_settings(SERVICE_API_BASE_URL="http://testserver")
class AnonymousDetailViewTests(_AnonymousCampaignTestCase):
    """Tests for the detail view with anonymous campaign users."""

    @patch("web.views.requests.get")
    def test_valid_service(self, mock_get):
        """GET /detail/1 as anonymous → 200."""
        mock_get.return_value = _mock_response({
            "id": 1,
            "serviceName": "Test Service",
            "description": "A test service",
        })
        response = self.client.get(reverse("detail", kwargs={"service_id": 1}))
        self.assertEqual(response.status_code, 200)


@override_settings(SERVICE_API_BASE_URL="http://testserver")
class AnonymousDetailNoPromptTests(_AnonymousCampaignTestCase):
    """Anonymous users should go straight to service details without prompt."""

    @patch("web.views.requests.get")
    def test_anonymous_first_visit_shows_detail(self, mock_get):
        """GET /detail/1 as anonymous → 200, shows detail content."""
        mock_get.return_value = _mock_response({
            "id": 1,
            "serviceName": "Test Service",
            "description": "A test",
        })
        response = self.client.get(reverse("detail", kwargs={"service_id": 1}))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Service", response.content)
        self.assertNotIn(b"Create an account", response.content)

    @patch("web.views.requests.get")
    def test_skip_prompt_query_is_ignored(self, mock_get):
        """GET /detail/1?skip_prompt=1 shows detail and does not set session flags."""
        mock_get.return_value = _mock_response({
            "id": 1,
            "serviceName": "Test Service",
            "description": "A test",
        })
        response = self.client.get(
            reverse("detail", kwargs={"service_id": 1}) + "?skip_prompt=1"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Service", response.content)
        self.assertIsNone(self.client.session.get("account_prompt_dismissed"))

    @patch("web.views.requests.get")
    def test_create_account_post_redirects_to_disclaimer(self, mock_get):
        """POST /detail/1 action=create_account redirects to disclaimer and stores prompt session."""
        mock_get.return_value = _mock_response({
            "id": 1,
            "serviceName": "Test Service",
            "description": "A test",
        })
        response = self.client.post(
            reverse("detail", kwargs={"service_id": 1}),
            {"action": "create_account"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("htsh:disclaimer"))
        self.assertEqual(self.client.session.get("account_prompt_service_id"), 1)


@override_settings(SERVICE_API_BASE_URL="http://testserver")
class AuthenticatedDetailBypassTests(_AuthenticatedTestCase):
    """Authenticated users never see the account prompt."""

    @patch("web.views.requests.get")
    def test_authenticated_user_never_sees_prompt(self, mock_get):
        """GET /detail/1 as authenticated → detail page, no interstitial."""
        mock_get.return_value = _mock_response({
            "id": 1,
            "serviceName": "Test Service",
            "description": "A test",
        })
        response = self.client.get(reverse("detail", kwargs={"service_id": 1}))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Service", response.content)
        self.assertNotIn(b"nhsuk-panel", response.content)


class AllowCheckInInterstitialRedirectTests(_AuthenticatedTestCase):
    """Tests for allow_check_in redirecting interstitial users to service detail."""

    def test_allow_check_in_redirects_to_service_detail_on_yes(self):
        """POST /allow-check-in yes with service_id → redirect to /detail/<id>."""
        session = self.client.session
        session["account_prompt_service_id"] = 42
        session.save()
        response = self.client.post(
            reverse("allow-check-in"),
            {"allow_check_in": "yes"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/detail/42", response.url)
        # Service ID should be popped from session
        self.assertNotIn("account_prompt_service_id", self.client.session)

    def test_allow_check_in_redirects_to_service_detail_on_no(self):
        """POST /allow-check-in no with service_id → redirect to /detail/<id>."""
        session = self.client.session
        session["account_prompt_service_id"] = 42
        session.save()
        response = self.client.post(
            reverse("allow-check-in"),
            {"allow_check_in": "no"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/detail/42", response.url)

    def test_allow_check_in_preserves_existing_behavior_without_service_id(self):
        """POST /allow-check-in yes without service_id → redirect to /listing."""
        response = self.client.post(
            reverse("allow-check-in"),
            {"allow_check_in": "yes"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/listing", response.url)


class AnonymousSuccessViewTests(_AnonymousCampaignTestCase):
    """Tests for the success view with anonymous campaign users."""

    def test_get_renders(self):
        """GET /success as anonymous → 200."""
        response = self.client.get(reverse("success"))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_success_content(self):
        """GET /success as anonymous → contains 'Thank you', not 'signed in'."""
        response = self.client.get(reverse("success"))
        self.assertIn(b"Thank you", response.content)
        self.assertNotIn(b"signed in", response.content)


class AuthenticatedSuccessViewTests(_AuthenticatedTestCase):
    """Regression guard: success page shows 'signed in' for authenticated users."""

    def test_authenticated_success_content(self):
        """GET /success as authenticated → contains 'signed in'."""
        response = self.client.get(reverse("success"))
        self.assertIn(b"signed in", response.content)
