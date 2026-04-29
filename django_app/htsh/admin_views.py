"""htsh/admin_views.py

A dedicated admin site for HTSH operations.

Requested behaviour:
- Available at /admin/htsh/
- Shows the standard Django "Authentication and Authorization" apps (Users, Groups)
- Shows a "HTSH" section (User Profiles, Magic Links, User Filters, Campaigns)

We keep the default /admin/ site in place (used by the API admin wiring) and
add this separate AdminSite instance for HTSH users.
"""

from __future__ import annotations

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.urls import reverse

from .models import UserProfile, MagicLink, UserFilter, Campaign

# Import the ModelAdmin configurations (list_display, actions, etc.).
# These are registered on Django's default admin site via decorators, but we
# also want them on the dedicated HTSH admin site.
from .admin import (
    UserProfileAdmin,
    MagicLinkAdmin,
    UserFilterAdmin,
    CampaignAdmin,
)


class HtshAdminSite(admin.AdminSite):
    site_header = "HTSH admin"
    site_title = "HTSH admin"
    index_title = "HTSH admin"

    def index(self, request, extra_context=None):
        """Default /admin/htsh/ to the UserProfile changelist.

        This keeps the standard admin chrome (including the nav sidebar) but
        immediately lands the user on the most-used table.
        """
        try:
            url = reverse("admin_views:htsh_userprofile_changelist")
        except Exception:
            # Fallback to the normal admin index if the model isn't registered.
            return super().index(request, extra_context=extra_context)
        return HttpResponseRedirect(url)


htsh_admin_site = HtshAdminSite(name="admin_views")


# --- Authentication and Authorization ---
htsh_admin_site.register(Group)
htsh_admin_site.register(get_user_model())


# --- HTSH ---
# Register with their ModelAdmin classes so actions appear in the HTSH admin UI.
htsh_admin_site.register(UserProfile, UserProfileAdmin)
htsh_admin_site.register(MagicLink, MagicLinkAdmin)
htsh_admin_site.register(UserFilter, UserFilterAdmin)
htsh_admin_site.register(Campaign, CampaignAdmin)
