"""Tests for PilotAccessMiddleware."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from pilot_access.middleware import PilotAccessMiddleware
from testing.helpers import make_pilot_profile, make_user

User = get_user_model()


class PilotAccessMiddlewareAuthRequiredTests(TestCase):
    """Tests for auth-required paths (/pilot/account/)."""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = PilotAccessMiddleware(
            get_response=lambda r: HttpResponse("OK")
        )

    def test_unauthenticated_account_redirects_to_landing(self):
        request = self.factory.get("/pilot/account/")
        request.user = AnonymousUser()
        request.session = {}
        response = self.middleware.process_request(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/pilot/landing/", response.url)

    def test_authenticated_no_profile_account_redirects(self):
        request = self.factory.get("/pilot/account/")
        request.user = make_user()
        request.session = {}
        response = self.middleware.process_request(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/pilot/landing/", response.url)

    def test_authenticated_no_disclaimer_account_redirects(self):
        user = make_user()
        make_pilot_profile(user=user, disclaimer_accepted_at=None)
        request = self.factory.get("/pilot/account/")
        request.user = user
        request.session = {}
        response = self.middleware.process_request(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/pilot/landing/", response.url)

    def test_staff_user_account_redirects(self):
        request = self.factory.get("/pilot/account/")
        request.user = make_user(is_staff=True)
        request.session = {}
        response = self.middleware.process_request(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/pilot/landing/", response.url)

    def test_authenticated_with_full_profile_account_passes(self):
        user = make_user()
        make_pilot_profile(user=user, disclaimer_accepted_at=timezone.now())
        request = self.factory.get("/pilot/account/")
        request.user = user
        request.session = {}
        response = self.middleware.process_request(request)
        self.assertIsNone(response)
        self.assertTrue(hasattr(request, "pilot_access_profile"))
        self.assertTrue(request.pilot_access_registered)

    def test_account_delete_requires_auth(self):
        request = self.factory.get("/pilot/account/delete/")
        request.user = AnonymousUser()
        request.session = {}
        response = self.middleware.process_request(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/pilot/landing/", response.url)


class PilotAccessMiddlewareExemptTests(TestCase):
    """Tests for system exempt paths."""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = PilotAccessMiddleware(
            get_response=lambda r: HttpResponse("OK")
        )

    def test_health_exempt(self):
        request = self.factory.get("/health")
        request.user = AnonymousUser()
        request.session = {}
        response = self.middleware.process_request(request)
        self.assertIsNone(response)

    def test_static_exempt(self):
        request = self.factory.get("/static/nonexistent.css")
        request.user = AnonymousUser()
        request.session = {}
        response = self.middleware.process_request(request)
        self.assertIsNone(response)

    def test_admin_exempt(self):
        request = self.factory.get("/admin/")
        request.user = AnonymousUser()
        request.session = {}
        response = self.middleware.process_request(request)
        self.assertIsNone(response)

    def test_api_v3_exempt(self):
        request = self.factory.get("/v3/")
        request.user = AnonymousUser()
        request.session = {}
        response = self.middleware.process_request(request)
        self.assertIsNone(response)

    def test_apidocs_exempt(self):
        request = self.factory.get("/apidocs/")
        request.user = AnonymousUser()
        request.session = {}
        response = self.middleware.process_request(request)
        self.assertIsNone(response)


class PilotAccessMiddlewarePilotFlowTests(TestCase):
    """Tests for pilot auth flow passthrough (/pilot/* except /pilot/account/)."""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = PilotAccessMiddleware(
            get_response=lambda r: HttpResponse("OK")
        )

    def test_landing_passes_through(self):
        response = self.client.get(reverse("pilot_access:landing"))
        self.assertEqual(response.status_code, 200)

    def test_otp_page_not_redirected_to_landing(self):
        request = self.factory.get("/pilot/otp/")
        request.user = AnonymousUser()
        request.session = {}
        response = self.middleware.process_request(request)
        self.assertIsNone(response)

    def test_login_page_not_redirected_to_landing(self):
        request = self.factory.get("/pilot/login/")
        request.user = AnonymousUser()
        request.session = {}
        response = self.middleware.process_request(request)
        self.assertIsNone(response)

    def test_disclaimer_page_not_redirected_to_landing(self):
        request = self.factory.get("/pilot/disclaimer/")
        request.user = AnonymousUser()
        request.session = {}
        response = self.middleware.process_request(request)
        self.assertIsNone(response)


class PilotAccessMiddlewareWebJourneyTests(TestCase):
    """Tests for campaign-gated web journey routes."""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = PilotAccessMiddleware(
            get_response=lambda r: HttpResponse("OK")
        )

    def test_anonymous_with_campaign_session_passes(self):
        request = self.factory.get("/")
        request.user = AnonymousUser()
        request.session = {"campaign_code": "123456"}
        response = self.middleware.process_request(request)
        self.assertIsNone(response)
        self.assertFalse(request.pilot_access_registered)

    def test_anonymous_with_campaign_accesses_details(self):
        request = self.factory.get("/details-postcode")
        request.user = AnonymousUser()
        request.session = {"campaign_code": "123456"}
        response = self.middleware.process_request(request)
        self.assertIsNone(response)

    def test_anonymous_without_campaign_redirects_from_root(self):
        request = self.factory.get("/")
        request.user = AnonymousUser()
        request.session = {}
        response = self.middleware.process_request(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/pilot/landing/", response.url)

    def test_anonymous_without_campaign_redirects_from_goals(self):
        request = self.factory.get("/goals")
        request.user = AnonymousUser()
        request.session = {}
        response = self.middleware.process_request(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/pilot/landing/", response.url)

    def test_authenticated_user_with_profile_passes(self):
        user = make_user()
        make_pilot_profile(user=user, disclaimer_accepted_at=timezone.now())
        request = self.factory.get("/")
        request.user = user
        request.session = {}
        response = self.middleware.process_request(request)
        self.assertIsNone(response)
        self.assertTrue(hasattr(request, "pilot_access_profile"))
        self.assertTrue(request.pilot_access_registered)

    def test_authenticated_no_profile_with_campaign_passes(self):
        request = self.factory.get("/")
        request.user = make_user()
        request.session = {"campaign_code": "123456"}
        response = self.middleware.process_request(request)
        self.assertIsNone(response)


class PilotAccessMiddlewareCacheHeaderTests(TestCase):
    """Tests for cache control headers on responses."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_web_route_has_cache_headers(self):
        user = make_user()
        make_pilot_profile(user=user, disclaimer_accepted_at=timezone.now())
        inner_response = HttpResponse("OK")
        middleware = PilotAccessMiddleware(get_response=lambda r: inner_response)
        request = self.factory.get("/")
        request.user = user
        request.session = {}
        response = middleware(request)
        self.assertIn("no-cache", response.get("Cache-Control", ""))

    def test_account_route_has_cache_headers(self):
        user = make_user()
        make_pilot_profile(user=user, disclaimer_accepted_at=timezone.now())
        inner_response = HttpResponse("OK")
        middleware = PilotAccessMiddleware(get_response=lambda r: inner_response)
        request = self.factory.get("/pilot/account/")
        request.user = user
        request.session = {}
        response = middleware(request)
        self.assertIn("no-cache", response.get("Cache-Control", ""))

    def test_exempt_route_no_cache_headers(self):
        inner_response = HttpResponse("OK")
        middleware = PilotAccessMiddleware(get_response=lambda r: inner_response)
        request = self.factory.get("/health")
        request.user = AnonymousUser()
        request.session = {}
        response = middleware(request)
        self.assertNotIn("no-cache", response.get("Cache-Control", ""))


class FavouritesAuthGateTests(TestCase):
    """Tests for /favourites auth gating via middleware."""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = PilotAccessMiddleware(
            get_response=lambda r: HttpResponse("OK")
        )

    def test_unauthenticated_favourites_redirects_to_landing(self):
        request = self.factory.get("/favourites")
        request.user = AnonymousUser()
        request.session = {}
        response = self.middleware.process_request(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/pilot/landing/", response.url)

    def test_unauthenticated_favourites_trailing_slash_redirects(self):
        request = self.factory.get("/favourites/")
        request.user = AnonymousUser()
        request.session = {}
        response = self.middleware.process_request(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/pilot/landing/", response.url)

    def test_pilot_flow_no_cache_headers(self):
        inner_response = HttpResponse("OK")
        middleware = PilotAccessMiddleware(get_response=lambda r: inner_response)
        request = self.factory.get("/pilot/landing/")
        request.user = AnonymousUser()
        request.session = {}
        response = middleware(request)
        self.assertNotIn("no-cache", response.get("Cache-Control", ""))
