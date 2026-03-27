"""Tests for the custom 404 error handler."""

from django.test import RequestFactory, TestCase

from web.errors import handler404


class Handler404Tests(TestCase):
    """Tests for handler404."""

    def test_returns_404_status(self):
        """handler404 returns HttpResponseNotFound (status 404)."""
        factory = RequestFactory()
        request = factory.get("/nonexistent-page")
        response = handler404(request)
        self.assertEqual(response.status_code, 404)
