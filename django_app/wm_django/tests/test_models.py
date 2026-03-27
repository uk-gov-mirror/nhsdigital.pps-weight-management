"""Unit tests for pilot_access models: Campaign, PilotProfile, MagicLink, UserFilter."""

from datetime import date, timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from pilot_access.models import Campaign
from testing.helpers import (
    make_campaign,
    make_magic_link,
    make_pilot_profile,
    make_user,
    make_user_filter,
)


class CampaignModelTests(TestCase):
    """Tests for Campaign model methods and validation."""

    def test_is_valid_today_within_range(self):
        campaign = make_campaign(
            valid_from=date.today() - timedelta(days=1),
            valid_to=date.today() + timedelta(days=1),
        )
        self.assertTrue(campaign.is_valid_today())

    @patch("pilot_access.models.timezone.now")
    def test_is_valid_today_before_range(self, mock_now):
        mock_now.return_value = timezone.make_aware(
            timezone.datetime(2020, 1, 1, 12, 0, 0)
        )
        campaign = make_campaign(
            valid_from=date(2025, 6, 1),
            valid_to=date(2025, 12, 31),
        )
        self.assertFalse(campaign.is_valid_today())

    @patch("pilot_access.models.timezone.now")
    def test_is_valid_today_after_range(self, mock_now):
        mock_now.return_value = timezone.make_aware(
            timezone.datetime(2030, 1, 1, 12, 0, 0)
        )
        campaign = make_campaign(
            valid_from=date(2025, 6, 1),
            valid_to=date(2025, 12, 31),
        )
        self.assertFalse(campaign.is_valid_today())

    def test_clean_raises_when_valid_from_equals_valid_to(self):
        today = date.today()
        campaign = Campaign(
            valid_from=today,
            valid_to=today,
            comment="test",
        )
        with self.assertRaises(ValidationError) as ctx:
            campaign.clean()
        self.assertIn("valid_to", ctx.exception.message_dict)

    def test_clean_raises_when_valid_from_after_valid_to(self):
        campaign = Campaign(
            valid_from=date.today() + timedelta(days=1),
            valid_to=date.today() - timedelta(days=1),
            comment="test",
        )
        with self.assertRaises(ValidationError) as ctx:
            campaign.clean()
        self.assertIn("valid_to", ctx.exception.message_dict)

    def test_save_auto_generates_campaign_code(self):
        campaign = make_campaign()
        self.assertEqual(len(campaign.campaign_code), 6)
        self.assertTrue(campaign.campaign_code.isdigit())

    def test_save_preserves_existing_campaign_code(self):
        campaign = make_campaign(campaign_code="123456")
        self.assertEqual(campaign.campaign_code, "123456")


class PilotProfileModelTests(TestCase):
    """Tests for PilotProfile model methods."""

    def test_has_accepted_disclaimer_true(self):
        profile = make_pilot_profile(disclaimer_accepted_at=timezone.now())
        self.assertTrue(profile.has_accepted_disclaimer())

    def test_has_accepted_disclaimer_false(self):
        profile = make_pilot_profile(disclaimer_accepted_at=None)
        self.assertFalse(profile.has_accepted_disclaimer())


class MagicLinkModelTests(TestCase):
    """Tests for MagicLink.is_valid method."""

    def test_is_valid_true_when_unused_and_not_expired(self):
        link = make_magic_link(
            used_at=None,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.assertTrue(link.is_valid())

    def test_is_valid_false_when_used(self):
        link = make_magic_link(
            used_at=timezone.now(),
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.assertFalse(link.is_valid())

    def test_is_valid_false_when_expired(self):
        link = make_magic_link(
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertFalse(link.is_valid())


class UserFilterModelTests(TestCase):
    """Tests for UserFilter.set_value and get_value methods."""

    def test_set_value_stores_value(self):
        uf = make_user_filter()
        uf.set_value("key", "val")
        self.assertEqual(uf.data["key"], "val")

    def test_set_value_removes_none(self):
        uf = make_user_filter()
        uf.set_value("key", "val")
        uf.set_value("key", None)
        self.assertNotIn("key", uf.data)

    def test_get_value_returns_stored(self):
        uf = make_user_filter()
        uf.set_value("k", "v")
        self.assertEqual(uf.get_value("k"), "v")
