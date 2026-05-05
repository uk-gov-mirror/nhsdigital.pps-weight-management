"""Tests for favourite toggle endpoint and star icon rendering."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from htsh.models import FavouriteService
from testing.helpers import make_favourite_service, make_profile, make_user
from web.views import SESSION_KEY_ANONYMOUS_FAVOURITES


class _AuthenticatedTestCase(TestCase):
    """Base class that logs in a user with a completed pilot profile."""

    def setUp(self):
        self.user = make_user()
        self.profile = make_profile(
            user=self.user,
            disclaimer_accepted_at=timezone.now(),
        )
        self.client.force_login(self.user)


class ToggleFavouriteTests(_AuthenticatedTestCase):
    """Tests for the POST /favourite/toggle/<service_id> endpoint."""

    def test_add_favourite(self):
        """POST to toggle adds a favourite for authenticated user."""
        url = reverse("toggle_favourite", args=[42])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            FavouriteService.objects.filter(user=self.user, service_id=42).exists()
        )

    def test_remove_favourite(self):
        """POST to toggle removes an existing favourite (toggle off)."""
        make_favourite_service(user=self.user, service_id=42)
        url = reverse("toggle_favourite", args=[42])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            FavouriteService.objects.filter(user=self.user, service_id=42).exists()
        )

    def test_unauthenticated_with_campaign_toggles_session_and_redirects_to_listing(self):
        """POST to toggle while unauthenticated with campaign mutates session and redirects to listing."""
        self.client.logout()
        session = self.client.session
        session["campaign_code"] = "123456"
        session.save()
        url = reverse("toggle_favourite", args=[42])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/listing", response.url)
        session = self.client.session
        self.assertEqual(session.get(SESSION_KEY_ANONYMOUS_FAVOURITES), [42])
        self.assertFalse(FavouriteService.objects.filter(service_id=42).exists())

    def test_unauthenticated_without_campaign_redirects_to_landing(self):
        """POST to toggle while unauthenticated without campaign redirects to landing."""
        self.client.logout()
        url = reverse("toggle_favourite", args=[42])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/landing", response.url)

    def test_get_returns_405(self):
        """GET request to toggle endpoint returns 405 Method Not Allowed."""
        url = reverse("toggle_favourite", args=[42])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_redirect_uses_referer_same_host(self):
        """POST redirects to HTTP_REFERER when it matches the host."""
        url = reverse("toggle_favourite", args=[42])
        response = self.client.post(
            url, HTTP_REFERER="http://testserver/detail/42"
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "http://testserver/detail/42")

    def test_redirect_ignores_external_referer(self):
        """POST ignores external HTTP_REFERER and redirects to listing."""
        url = reverse("toggle_favourite", args=[42])
        response = self.client.post(
            url, HTTP_REFERER="http://evil.com/steal"
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/listing", response.url)


class AnonymousTogglePromptTests(TestCase):
    """Tests for anonymous star toggle session behavior."""

    def setUp(self):
        session = self.client.session
        session["campaign_code"] = "123456"
        session.save()

    def test_anonymous_toggle_redirects_to_listing_without_referer(self):
        """POST /favourite/toggle/42 as anonymous without referer → 302 to /listing."""
        url = reverse("toggle_favourite", args=[42])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/listing", response.url)

    def test_anonymous_toggle_no_favourite_created(self):
        """POST /favourite/toggle/42 as anonymous → no FavouriteService row."""
        url = reverse("toggle_favourite", args=[42])
        self.client.post(url)
        self.assertFalse(FavouriteService.objects.filter(service_id=42).exists())

    def test_anonymous_toggle_uses_same_host_referer(self):
        """POST /favourite/toggle/42 with same-host referer redirects back to referer."""
        url = reverse("toggle_favourite", args=[42])
        response = self.client.post(url, HTTP_REFERER="http://testserver/detail/42")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "http://testserver/detail/42")

    def test_anonymous_toggle_is_idempotent_add_then_remove(self):
        """Repeated anonymous toggle adds then removes service ID from session list."""
        url = reverse("toggle_favourite", args=[42])
        self.client.post(url)
        self.assertEqual(self.client.session.get(SESSION_KEY_ANONYMOUS_FAVOURITES), [42])

        self.client.post(url)
        self.assertEqual(self.client.session.get(SESSION_KEY_ANONYMOUS_FAVOURITES), [])


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
class ListingStarTests(_AuthenticatedTestCase):
    """Tests for star icon rendering on the listing page."""

    def setUp(self):
        super().setUp()
        self.url = reverse("listing")
        session = self.client.session
        session["details-postcode"] = "SW1A 1AA"
        session.save()

    @patch("web.views.requests.post")
    def test_listing_shows_gold_star_for_favourited_service(self, mock_post):
        """Gold star (fill=#FFB800) renders for a favourited service."""
        make_favourite_service(user=self.user, service_id=1)
        mock_post.return_value = _mock_response({
            "total": 1,
            "results": [{"id": 1, "serviceName": "Fav Service"}],
        })
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('fill="#FFB800"', content)

    @patch("web.views.requests.post")
    def test_listing_shows_grey_star_for_non_favourited_service(self, mock_post):
        """Grey star (stroke=#768692) renders for a non-favourited service."""
        mock_post.return_value = _mock_response({
            "total": 1,
            "results": [{"id": 99, "serviceName": "Other Service"}],
        })
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('stroke="#768692"', content)

    @patch("web.views.requests.post")
    def test_listing_anonymous_shows_grey_stars(self, mock_post):
        """Anonymous user sees grey stars (no gold stars)."""
        self.client.logout()
        session = self.client.session
        session["campaign_code"] = "123456"
        session["details-postcode"] = "SW1A 1AA"
        session.save()
        mock_post.return_value = _mock_response({
            "total": 1,
            "results": [{"id": 1, "serviceName": "Service A"}],
        })
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('stroke="#768692"', content)
        self.assertNotIn('fill="#FFB800"', content)

    @patch("web.views.requests.post")
    def test_listing_anonymous_shows_gold_star_from_session_favourites(self, mock_post):
        """Anonymous listing star renders gold when service ID is favourited in session."""
        self.client.logout()
        session = self.client.session
        session["campaign_code"] = "123456"
        session["details-postcode"] = "SW1A 1AA"
        session[SESSION_KEY_ANONYMOUS_FAVOURITES] = [1]
        session.save()
        mock_post.return_value = _mock_response({
            "total": 1,
            "results": [{"id": 1, "serviceName": "Service A"}],
        })
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('fill="#FFB800"', response.content.decode())


@override_settings(SERVICE_API_BASE_URL="http://testserver")
class DetailStarTests(_AuthenticatedTestCase):
    """Tests for star icon rendering on the detail page."""

    @patch("web.views.requests.get")
    def test_detail_shows_gold_star_when_favourited(self, mock_get):
        """Gold star renders on detail page when service is favourited."""
        make_favourite_service(user=self.user, service_id=7)
        mock_get.return_value = _mock_response({
            "id": 7,
            "serviceName": "Fav Detail",
            "description": "Desc",
            "logoImage": "logo.png",
        })
        url = reverse("detail", args=[7])
        response = self.client.get(url + "?skip_prompt=1")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('fill="#FFB800"', content)

    @patch("web.views.requests.get")
    def test_detail_shows_grey_star_when_not_favourited(self, mock_get):
        """Grey star renders on detail page when service is not favourited."""
        mock_get.return_value = _mock_response({
            "id": 8,
            "serviceName": "Other Detail",
            "description": "Desc",
            "logoImage": "logo.png",
        })
        url = reverse("detail", args=[8])
        response = self.client.get(url + "?skip_prompt=1")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('stroke="#768692"', content)

    @patch("web.views.requests.get")
    def test_detail_anonymous_shows_gold_star_from_session_favourites(self, mock_get):
        """Anonymous detail star renders gold when service ID is favourited in session."""
        self.client.logout()
        session = self.client.session
        session["campaign_code"] = "123456"
        session[SESSION_KEY_ANONYMOUS_FAVOURITES] = [7]
        session.save()
        mock_get.return_value = _mock_response({
            "id": 7,
            "serviceName": "Anon Fav Detail",
            "description": "Desc",
            "logoImage": "logo.png",
        })
        url = reverse("detail", args=[7])
        response = self.client.get(url + "?skip_prompt=1")
        self.assertEqual(response.status_code, 200)
        self.assertIn('fill="#FFB800"', response.content.decode())


class FavouritesPageTests(_AuthenticatedTestCase):
    """Tests for the /favourites page."""

    def test_favourites_page_shows_saved_services(self):
        """Authenticated user sees their saved services rendered as cards."""
        from api.models_v3 import V3_Service

        svc_a = V3_Service.objects.create(
            name="Service A", description="Desc A", cost_text="Free", sort_order=1.0
        )
        svc_b = V3_Service.objects.create(
            name="Service B", description="Desc B", cost_text="Paid", sort_order=2.0
        )
        make_favourite_service(user=self.user, service_id=svc_a.id)
        make_favourite_service(user=self.user, service_id=svc_b.id)

        response = self.client.get("/favourites")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Service A", content)
        self.assertIn("Service B", content)
        self.assertIn("nhsuk-card", content)

    def test_favourites_page_empty_state(self):
        """No favourites shows empty state message with link to listing."""
        response = self.client.get("/favourites")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("saved any services yet", content)
        self.assertIn("Browse activities", content)

    def test_favourites_page_stale_service_not_500(self):
        """Stale favourite (no matching V3_Service) does not cause 500."""
        make_favourite_service(user=self.user, service_id=99999)
        response = self.client.get("/favourites")
        self.assertEqual(response.status_code, 200)

    def test_favourites_page_shows_gold_star(self):
        """Gold star renders for each favourited service."""
        from api.models_v3 import V3_Service

        svc = V3_Service.objects.create(
            name="Gold Star Svc", description="Desc", cost_text="Free", sort_order=1.0
        )
        make_favourite_service(user=self.user, service_id=svc.id)

        response = self.client.get("/favourites")
        self.assertEqual(response.status_code, 200)
        self.assertIn('fill="#FFB800"', response.content.decode())

    def test_favourites_page_has_remove_form(self):
        """Each card has a toggle form for removing the favourite."""
        from api.models_v3 import V3_Service

        svc = V3_Service.objects.create(
            name="Remove Svc", description="Desc", cost_text="Free", sort_order=1.0
        )
        make_favourite_service(user=self.user, service_id=svc.id)

        response = self.client.get("/favourites")
        self.assertEqual(response.status_code, 200)
        self.assertIn("favourite/toggle/", response.content.decode())


class AnonymousFavouritesPageTests(TestCase):
    """Tests for anonymous session-backed /favourites access."""

    def setUp(self):
        session = self.client.session
        session["campaign_code"] = "123456"
        session.save()

    def test_anonymous_favourites_page_shows_session_saved_services(self):
        """Anonymous campaign user can open /favourites and see session-backed services."""
        from api.models_v3 import V3_Service

        service = V3_Service.objects.create(
            name="Anon Saved Service",
            description="Desc",
            cost_text="Free",
            sort_order=1.0,
        )
        session = self.client.session
        session[SESSION_KEY_ANONYMOUS_FAVOURITES] = [service.id]
        session.save()

        response = self.client.get("/favourites")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Anon Saved Service", response.content.decode())

    def test_anonymous_favourites_page_empty_state_without_session_favourites(self):
        """Anonymous campaign user without favourites sees the empty state."""
        response = self.client.get("/favourites")
        self.assertEqual(response.status_code, 200)
        self.assertIn("saved any services yet", response.content.decode())

    def test_anonymous_favourites_page_has_remove_form(self):
        """Anonymous session-backed favourites page also renders the toggle form."""
        from api.models_v3 import V3_Service

        svc = V3_Service.objects.create(
            name="Remove Svc", description="Desc", cost_text="Free", sort_order=1.0
        )
        session = self.client.session
        session[SESSION_KEY_ANONYMOUS_FAVOURITES] = [svc.id]
        session.save()

        response = self.client.get("/favourites")
        self.assertEqual(response.status_code, 200)
        self.assertIn("favourite/toggle/", response.content.decode())


@override_settings(SERVICE_API_BASE_URL="http://testserver")
class ListingFavouritesButtonTests(_AuthenticatedTestCase):
    """Tests for the favourites button on the listing page."""

    def setUp(self):
        super().setUp()
        session = self.client.session
        session["details-postcode"] = "SW1A 1AA"
        session.save()

    @patch("web.views.requests.post")
    def test_authenticated_user_sees_favourites_button(self, mock_post):
        """Authenticated user sees 'Your saved services' button on listing."""
        mock_post.return_value = _mock_response({"total": 0, "results": []})
        response = self.client.get(reverse("listing"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Your saved services", content)
        self.assertIn('href="/favourites"', content)

    @patch("web.views.requests.post")
    def test_anonymous_user_does_not_see_favourites_button(self, mock_post):
        """Anonymous user without session favourites does not see the favourites button."""
        self.client.logout()
        session = self.client.session
        session["campaign_code"] = "123456"
        session["details-postcode"] = "SW1A 1AA"
        session.save()
        mock_post.return_value = _mock_response({"total": 0, "results": []})
        response = self.client.get(reverse("listing"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Your saved services", response.content.decode())

    @patch("web.views.requests.post")
    def test_anonymous_user_with_session_favourites_sees_favourites_button(self, mock_post):
        """Anonymous user with session favourites sees the favourites button on listing."""
        self.client.logout()
        session = self.client.session
        session["campaign_code"] = "123456"
        session["details-postcode"] = "SW1A 1AA"
        session[SESSION_KEY_ANONYMOUS_FAVOURITES] = [42]
        session.save()
        mock_post.return_value = _mock_response({"total": 0, "results": []})

        response = self.client.get(reverse("listing"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Your saved services", content)
        self.assertIn('href="/favourites"', content)
