"""Tests for PilotAccessMiddleware."""

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from pilot_access.middleware import PilotAccessMiddleware
from testing.helpers import make_pilot_profile, make_user

User = get_user_model()


class PilotAccessMiddlewarePublicPathTests(TestCase):
    """Tests that public paths are accessible without authentication."""

    def test_public_path_landing(self):
        """GET /pilot/landing/ returns 200 (not redirect)."""
        response = self.client.get(reverse("pilot_access:landing"))
        self.assertEqual(response.status_code, 200)

    def test_public_path_health(self):
        """GET /health returns 200."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

    def test_public_path_static(self):
        """GET /static/ path should NOT redirect to landing."""
        response = self.client.get("/static/nonexistent.css")
        # May 404 but should NOT redirect to /pilot/landing/
        self.assertNotEqual(response.status_code, 302)

    def test_public_path_api_v3(self):
        """GET /v3/ returns response (not redirect to pilot landing)."""
        response = self.client.get("/v3/")
        # Should not redirect to landing
        if response.status_code == 302:
            self.assertNotIn(
                "/pilot/landing/", response.url
            )


class PilotAccessMiddlewareAuthTests(TestCase):
    """Tests that middleware enforces authentication on protected paths."""

    def test_unauthenticated_protected_path_redirects(self):
        """Unauthenticated GET to protected path redirects to landing."""
        factory = RequestFactory()
        from django.contrib.auth.models import AnonymousUser

        request = factory.get("/some-protected-path/")
        request.user = AnonymousUser()
        request.session = {}

        middleware = PilotAccessMiddleware(
            get_response=lambda r: HttpResponse("OK")
        )
        response = middleware.process_request(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/pilot/landing/", response.url)

    def test_authenticated_no_profile_redirects(self):
        """Authenticated user without PilotProfile redirects to landing."""
        factory = RequestFactory()
        user = make_user()
        request = factory.get("/some-protected-path/")
        request.user = user
        request.session = {}

        middleware = PilotAccessMiddleware(
            get_response=lambda r: HttpResponse("OK")
        )
        response = middleware.process_request(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/pilot/landing/", response.url)

    def test_authenticated_no_disclaimer_redirects(self):
        """User with profile but no disclaimer_accepted_at redirects."""
        factory = RequestFactory()
        user = make_user()
        make_pilot_profile(user=user, disclaimer_accepted_at=None)
        request = factory.get("/some-protected-path/")
        request.user = user
        request.session = {}

        middleware = PilotAccessMiddleware(
            get_response=lambda r: HttpResponse("OK")
        )
        response = middleware.process_request(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/pilot/landing/", response.url)

    def test_authenticated_with_profile_and_disclaimer_passes(self):
        """User with full profile and disclaimer passes through."""
        factory = RequestFactory()
        user = make_user()
        make_pilot_profile(user=user, disclaimer_accepted_at=timezone.now())
        request = factory.get("/some-protected-path/")
        request.user = user
        request.session = {}

        middleware = PilotAccessMiddleware(
            get_response=lambda r: HttpResponse("OK")
        )
        response = middleware.process_request(request)
        # process_request returns get_response result when allowed through
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")

    def test_staff_user_redirects_to_landing(self):
        """Staff user redirects to landing (staff are not pilot users)."""
        factory = RequestFactory()
        user = make_user(is_staff=True)
        request = factory.get("/some-protected-path/")
        request.user = user
        request.session = {}

        middleware = PilotAccessMiddleware(
            get_response=lambda r: HttpResponse("OK")
        )
        response = middleware.process_request(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/pilot/landing/", response.url)


class PilotAccessMiddlewareCacheHeaderTests(TestCase):
    """Tests for cache control headers on responses."""

    def test_protected_path_has_no_cache_headers(self):
        """Authenticated protected path response has no-cache headers."""
        factory = RequestFactory()
        user = make_user()
        make_pilot_profile(user=user, disclaimer_accepted_at=timezone.now())

        inner_response = HttpResponse("OK")
        request = factory.get("/some-protected-path/")
        request.user = user
        request.session = {}

        middleware = PilotAccessMiddleware(
            get_response=lambda r: inner_response
        )
        response = middleware(request)
        self.assertIn("no-cache", response.get("Cache-Control", ""))
        self.assertIn("no-store", response.get("Cache-Control", ""))

    def test_public_path_no_cache_headers(self):
        """Public path response does NOT have no-cache headers."""
        factory = RequestFactory()
        from django.contrib.auth.models import AnonymousUser

        inner_response = HttpResponse("OK")
        request = factory.get("/pilot/landing/")
        request.user = AnonymousUser()
        request.session = {}

        middleware = PilotAccessMiddleware(
            get_response=lambda r: inner_response
        )
        response = middleware(request)
        cache_control = response.get("Cache-Control", "")
        self.assertNotIn("no-cache", cache_control)
