"""Unit tests for V3 serializers."""

from django.test import TestCase

from api.models_v3 import (
    V3_Contact,
    V3_Location,
    V3_Service_Contact,
    V3_Service_HelpsWith,
    V3_Service_Category,
    V3_Service_Location,
)
from api.v3.serializers import (
    V3_ServiceSummarySerializer,
    V3_ServiceDetailSerializer,
    V3_ServiceSearchRequestSerializer,
)
from testing.helpers import make_v3_category, make_v3_helps_with, make_v3_service


class TestV3ServiceSummarySerializer(TestCase):
    """Tests for V3_ServiceSummarySerializer field mapping and location count."""

    def test_field_mapping(self):
        svc = make_v3_service(name="Foo", cost_text="Free", sort_order=2.0)
        data = V3_ServiceSummarySerializer(svc).data
        self.assertEqual(data["serviceName"], "Foo")
        self.assertEqual(data["costText"], "Free")
        self.assertEqual(data["sortOrder"], 2.0)

    def test_location_count(self):
        svc = make_v3_service()
        loc1 = V3_Location.objects.create(address_1="1 High St")
        loc2 = V3_Location.objects.create(address_1="2 Low St")
        V3_Service_Location.objects.create(service=svc, location=loc1)
        V3_Service_Location.objects.create(service=svc, location=loc2)
        data = V3_ServiceSummarySerializer(svc).data
        self.assertEqual(data["locations"], 2)

    def test_location_count_no_locations(self):
        svc = make_v3_service()
        data = V3_ServiceSummarySerializer(svc).data
        self.assertEqual(data["locations"], 0)


class TestV3ServiceDetailSerializer(TestCase):
    """Tests for V3_ServiceDetailSerializer computed fields and nested data."""

    def test_basic_fields(self):
        svc = make_v3_service(
            name="Detail Svc",
            description="A description",
            what_it_is="What it is text",
            how_it_works="How it works text",
            what_it_could_do="What it could do text",
        )
        data = V3_ServiceDetailSerializer(svc, context={"request": None}).data
        self.assertEqual(data["serviceName"], "Detail Svc")
        self.assertEqual(data["description"], "A description")
        self.assertEqual(data["whatItIs"], "What it is text")
        self.assertEqual(data["howItWorks"], "How it works text")
        self.assertEqual(data["whatItCouldDo"], "What it could do text")

    def test_helps_with_list(self):
        svc = make_v3_service()
        hw = make_v3_helps_with(benefit="Physical activity")
        V3_Service_HelpsWith.objects.create(service=svc, helpswith=hw)
        data = V3_ServiceDetailSerializer(svc, context={"request": None}).data
        self.assertEqual(data["helpsWith"], ["Physical activity"])

    def test_category_list(self):
        svc = make_v3_service()
        cat = make_v3_category(goal="Lose weight")
        V3_Service_Category.objects.create(service=svc, category=cat)
        data = V3_ServiceDetailSerializer(svc, context={"request": None}).data
        self.assertEqual(data["category"], ["Lose weight"])

    def test_contact_no_contacts(self):
        svc = make_v3_service()
        data = V3_ServiceDetailSerializer(svc, context={"request": None}).data
        self.assertEqual(data["contact"], {"name": "", "phone": "", "email": ""})

    def test_contact_with_contact(self):
        svc = make_v3_service()
        contact = V3_Contact.objects.create(name="Jo", phone="123", email="jo@x.com")
        V3_Service_Contact.objects.create(service=svc, contact=contact)
        data = V3_ServiceDetailSerializer(svc, context={"request": None}).data
        self.assertEqual(data["contact"]["name"], "Jo")
        self.assertEqual(data["contact"]["phone"], "123")
        self.assertEqual(data["contact"]["email"], "jo@x.com")

    def test_locations_empty(self):
        svc = make_v3_service()
        data = V3_ServiceDetailSerializer(svc, context={"request": None}).data
        self.assertEqual(data["locations"], [])


class TestV3ServiceSearchRequestSerializer(TestCase):
    """Tests for V3_ServiceSearchRequestSerializer input validation."""

    databases = set()

    def test_defaults(self):
        s = V3_ServiceSearchRequestSerializer(data={})
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data["limit"], 50)
        self.assertEqual(s.validated_data["offset"], 0)
        self.assertEqual(s.validated_data["distance"], 5)

    def test_valid_postcode(self):
        s = V3_ServiceSearchRequestSerializer(data={"postcode": "SW1A 1AA"})
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data["postcode"], "SW1A 1AA")

    def test_invalid_postcode(self):
        s = V3_ServiceSearchRequestSerializer(data={"postcode": "INVALID"})
        self.assertFalse(s.is_valid())
        self.assertIn("postcode", s.errors)

    def test_limit_too_low(self):
        s = V3_ServiceSearchRequestSerializer(data={"limit": 0})
        self.assertFalse(s.is_valid())
        self.assertIn("limit", s.errors)

    def test_limit_too_high(self):
        s = V3_ServiceSearchRequestSerializer(data={"limit": 201})
        self.assertFalse(s.is_valid())
        self.assertIn("limit", s.errors)

    def test_limit_valid(self):
        s = V3_ServiceSearchRequestSerializer(data={"limit": 100})
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data["limit"], 100)

    def test_filter_groups(self):
        s = V3_ServiceSearchRequestSerializer(
            data={"filter": [{"or": ["term1", "term2"]}]}
        )
        self.assertTrue(s.is_valid(), s.errors)
        filter_data = s.validated_data["filter"]
        self.assertEqual(len(filter_data), 1)
        self.assertEqual(filter_data[0]["or"], ["term1", "term2"])
