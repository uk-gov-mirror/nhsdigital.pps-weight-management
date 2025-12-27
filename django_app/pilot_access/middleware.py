from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin


class PilotAccessMiddleware(MiddlewareMixin):
    def process_request(self, request):
        path = request.path

        # Allow public paths
        for prefix in settings.PILOT_ACCESS_PUBLIC_PATH_PREFIXES:
            if path.startswith(prefix):
                return None

        # Require authentication via invite flow
        if not request.user.is_authenticated:
            return redirect(reverse("pilot_access:landing"))

        # Require pilot profile
        pilot_profile = getattr(request.user, "pilot_profile", None)
        if pilot_profile is None:
            return redirect(reverse("pilot_access:landing"))

        # Require disclaimer acceptance
        if not pilot_profile.disclaimer_accepted_at:
            return redirect(reverse("pilot_access:accept_invitation"))

        return None
