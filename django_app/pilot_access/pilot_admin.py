"""pilot_access/pilot_admin.py

A dedicated admin site for pilot operations.

Requested behaviour:
- Available at /admin/pilot/
- Shows the standard Django "Authentication and Authorization" apps (Users, Groups)
- Shows a "Pilot access" section (Pilot Profiles, Magic Links, User Filters, Campaigns)

We keep the default /admin/ site in place (used by the API admin wiring) and
add this separate AdminSite instance for pilot users.
"""

from __future__ import annotations

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.urls import reverse

from .models import PilotProfile, MagicLink, UserFilter, Campaign

# Import the ModelAdmin configurations (list_display, actions, etc.).
# These are registered on Django's default admin site via decorators, but we
# also want them on the dedicated pilot admin site.
from .admin import (
    PilotProfileAdmin,
    MagicLinkAdmin,
    UserFilterAdmin,
    CampaignAdmin,
)


class PilotAdminSite(admin.AdminSite):
    site_header = "Pilot admin"
    site_title = "Pilot admin"
    index_title = "Pilot admin"

    def index(self, request, extra_context=None):
        """Default /admin/pilot/ to the PilotProfile changelist.

        This keeps the standard admin chrome (including the nav sidebar) but
        immediately lands the user on the most-used table.
        """
        try:
            url = reverse("pilot_admin:pilot_access_pilotprofile_changelist")
        except Exception:
            # Fallback to the normal admin index if the model isn't registered.
            return super().index(request, extra_context=extra_context)
        return HttpResponseRedirect(url)


pilot_admin_site = PilotAdminSite(name="pilot_admin")


# --- Authentication and Authorization ---
pilot_admin_site.register(Group)
pilot_admin_site.register(get_user_model())


# --- Pilot Access ---
# Register with their ModelAdmin classes so actions appear in the pilot admin UI.
pilot_admin_site.register(PilotProfile, PilotProfileAdmin)
pilot_admin_site.register(MagicLink, MagicLinkAdmin)
pilot_admin_site.register(UserFilter, UserFilterAdmin)
pilot_admin_site.register(Campaign, CampaignAdmin)
