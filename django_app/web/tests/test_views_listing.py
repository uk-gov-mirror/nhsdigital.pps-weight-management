"""Tests for web listing and detail views (API-backed with mocked internal API)."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from testing.helpers import make_pilot_profile, make_user


class _AuthenticatedTestCase(TestCase):
    """Base class that logs in a user with a completed pilot profile."""

    def setUp(self):
        self.user = make_user()
        self.profile = make_pilot_profile(
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
