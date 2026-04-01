"""Unit tests for V3 API views and V1/V2 smoke tests."""

import json

from django.test import TestCase

from api.models_v1 import V1_Service
from api.models_v2 import V2_Service
from api.models_v3 import V3_Service, V3_Taxonomy, V3_Service_Taxonomy
from testing.helpers import make_v3_service


class TestServiceSearchV3(TestCase):
    """Tests for POST /v3/services."""

    def test_empty_search(self):
        response = self.client.post(
            "/v3/services",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total", data)
        self.assertIn("results", data)
        self.assertEqual(data["total"], 0)

    def test_search_returns_services(self):
        make_v3_service(name="Svc A")
        make_v3_service(name="Svc B")
        response = self.client.post(
            "/v3/services",
            data=json.dumps({}),
            content_type="application/json",
        )
        data = response.json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(len(data["results"]), 2)

    def test_search_pagination(self):
        make_v3_service(name="A", sort_order=1.0)
        make_v3_service(name="B", sort_order=2.0)
        make_v3_service(name="C", sort_order=3.0)

        # First page
        response = self.client.post(
            "/v3/services",
            data=json.dumps({"limit": 2, "offset": 0}),
            content_type="application/json",
        )
        data = response.json()
        self.assertEqual(data["total"], 3)
        self.assertEqual(len(data["results"]), 2)

        # Second page
        response = self.client.post(
            "/v3/services",
            data=json.dumps({"limit": 2, "offset": 2}),
            content_type="application/json",
        )
        data = response.json()
        self.assertEqual(len(data["results"]), 1)

    def test_search_with_filter(self):
        svc1 = make_v3_service(name="Digital Svc")
        tax = V3_Taxonomy.objects.create(term="digital")
        V3_Service_Taxonomy.objects.create(service=svc1, taxonomy=tax)
        make_v3_service(name="No Tax Svc")

        response = self.client.post(
            "/v3/services",
            data=json.dumps({"filter": [{"or": ["digital"]}]}),
            content_type="application/json",
        )
        data = response.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["results"][0]["serviceName"], "Digital Svc")

    def test_search_invalid_postcode(self):
        response = self.client.post(
            "/v3/services",
            data=json.dumps({"postcode": "INVALID"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


class TestServiceDetailV3(TestCase):
    """Tests for GET /v3/service/<id>."""

    def test_detail_valid_pk(self):
        svc = make_v3_service(name="Test Svc")
        response = self.client.get(f"/v3/service/{svc.pk}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["serviceName"], "Test Svc")

    def test_detail_invalid_pk(self):
        response = self.client.get("/v3/service/99999")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("error", data)


class TestV1V2SmokeTests(TestCase):
    """Smoke tests for V1 and V2 API endpoints."""

    def test_v1_search_returns_200(self):
        V1_Service.objects.create(
            name="V1 Svc", description="test", cost_text="Free", sort_order=1.0
        )
        response = self.client.post(
            "/v1/services",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    def test_v2_search_returns_200(self):
        V2_Service.objects.create(
            name="V2 Svc", description="test", cost_text="Free", sort_order=1.0
        )
        response = self.client.post(
            "/v2/services",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
