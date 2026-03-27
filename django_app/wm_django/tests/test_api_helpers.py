"""Unit tests for V3 filter helper functions."""

from django.test import TestCase

from api.models_v3 import V3_Service, V3_Taxonomy, V3_Service_Taxonomy
from api.v3.views import _parse_filter_groups, _apply_and_of_ors
from testing.helpers import make_v3_service


class TestParseFilterGroups(TestCase):
    """Tests for _parse_filter_groups pure function."""

    databases = set()

    def test_empty_payload(self):
        self.assertEqual(_parse_filter_groups({}), [])

    def test_none_payload(self):
        self.assertEqual(_parse_filter_groups(None), [])

    def test_single_group(self):
        result = _parse_filter_groups({"filter": [{"or": ["a", "b"]}]})
        self.assertEqual(result, [["a", "b"]])

    def test_multiple_groups(self):
        result = _parse_filter_groups(
            {"filter": [{"or": ["a"]}, {"or": ["b", "c"]}]}
        )
        self.assertEqual(result, [["a"], ["b", "c"]])

    def test_dict_filter(self):
        result = _parse_filter_groups({"filter": {"or": ["a"]}})
        self.assertEqual(result, [["a"]])

    def test_strips_whitespace(self):
        result = _parse_filter_groups({"filter": [{"or": [" a "]}]})
        self.assertEqual(result, [["a"]])


class TestApplyAndOfOrs(TestCase):
    """Tests for _apply_and_of_ors queryset filter."""

    def test_no_groups_returns_all(self):
        make_v3_service(name="Svc1")
        make_v3_service(name="Svc2")
        qs = V3_Service.objects.all()
        result = _apply_and_of_ors(qs, [])
        self.assertEqual(result.count(), 2)

    def test_single_group_filters(self):
        svc1 = make_v3_service(name="Digital Svc")
        tax = V3_Taxonomy.objects.create(term="digital")
        V3_Service_Taxonomy.objects.create(service=svc1, taxonomy=tax)
        make_v3_service(name="No Tax Svc")

        qs = V3_Service.objects.all()
        result = _apply_and_of_ors(qs, [["digital"]])
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().name, "Digital Svc")
