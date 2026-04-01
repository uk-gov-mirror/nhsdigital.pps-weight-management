"""Factory functions for creating test model instances."""

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from api.models_v3 import V3_Category, V3_HelpsWith, V3_Service
from pilot_access.models import Campaign, MagicLink, PilotProfile, UserFilter


def make_user(**kwargs):
    """Create and return a saved User instance."""
    User = get_user_model()
    defaults = {
        "username": f"testuser_{uuid.uuid4().hex[:8]}",
    }
    defaults.update(kwargs)
    password = defaults.pop("password", "testpass123")
    user = User(**defaults)
    user.set_password(password)
    user.save()
    return user


def make_campaign(**kwargs):
    """Create and return a saved Campaign instance."""
    defaults = {
        "valid_from": timezone.now().date() - timedelta(days=1),
        "valid_to": timezone.now().date() + timedelta(days=30),
        "comment": "Test campaign",
    }
    defaults.update(kwargs)
    campaign = Campaign(**defaults)
    campaign.save()
    return campaign


def make_pilot_profile(user=None, campaign=None, **kwargs):
    """Create and return a saved PilotProfile instance."""
    if user is None:
        user = make_user()
    if campaign is None:
        campaign = make_campaign()
    defaults = {
        "email": "test@example.com",
        "phone": "07700900000",
        "postcode": "SW1A 1AA",
        "preferred_contact_method": PilotProfile.CONTACT_EMAIL,
        "disclaimer_accepted_at": None,
    }
    defaults.update(kwargs)
    return PilotProfile.objects.create(user=user, campaign=campaign, **defaults)


def make_magic_link(user=None, **kwargs):
    """Create and return a saved MagicLink instance."""
    if user is None:
        user = make_user()
    defaults = {
        "token_hash": f"testhash_{uuid.uuid4().hex}",
        "expires_at": timezone.now() + timedelta(hours=1),
        "used_at": None,
    }
    defaults.update(kwargs)
    return MagicLink.objects.create(user=user, **defaults)


def make_user_filter(user=None, **kwargs):
    """Create and return a saved UserFilter instance."""
    if user is None:
        user = make_user()
    defaults = {
        "data": {},
    }
    defaults.update(kwargs)
    return UserFilter.objects.create(user=user, **defaults)


def make_v3_category(**kwargs):
    """Create and return a saved V3_Category instance."""
    defaults = {
        "goal": "Lose weight",
    }
    defaults.update(kwargs)
    return V3_Category.objects.create(**defaults)


def make_v3_helps_with(**kwargs):
    """Create and return a saved V3_HelpsWith instance."""
    defaults = {
        "benefit": "Physical activity",
    }
    defaults.update(kwargs)
    return V3_HelpsWith.objects.create(**defaults)


def make_v3_service(**kwargs):
    """Create and return a saved V3_Service instance."""
    defaults = {
        "name": "Test Service",
        "description": "A test service",
        "cost_text": "Free",
        "sort_order": 1.0,
    }
    defaults.update(kwargs)
    return V3_Service.objects.create(**defaults)
