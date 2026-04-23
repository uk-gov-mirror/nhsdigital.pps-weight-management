"""Unit tests for the health check endpoint."""

from django.test import TestCase


class TestHealthEndpoint(TestCase):
    """Tests for GET /health."""

    def test_health_returns_200(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")
        self.assertEqual(response["Content-Type"], "text/plain")
