from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin


class PilotAccessMiddleware(MiddlewareMixin):
    def _requires_auth(self, path: str) -> bool:
        """Check if path requires full authentication (user + profile + disclaimer)."""
        path_with_slash = path if path.endswith("/") else path + "/"
        for prefix in settings.PILOT_ACCESS_AUTH_REQUIRED_PREFIXES:
            if path.startswith(prefix) or path_with_slash.startswith(prefix):
                return True
        return False

    def _is_exempt(self, path: str) -> bool:
        """Check if path is a system/infrastructure path exempt from all checks."""
        path_with_slash = path if path.endswith("/") else path + "/"
        for prefix in settings.PILOT_ACCESS_EXEMPT_PREFIXES:
            if path.startswith(prefix) or path_with_slash.startswith(prefix):
                return True
        return False

    def process_request(self, request):
        path = request.path

        # 1. Auth-required paths need fully authenticated pilot user
        if self._requires_auth(path):
            if not request.user.is_authenticated:
                return redirect(reverse("pilot_access:landing"))
            if getattr(request.user, "is_staff", False):
                return redirect(reverse("pilot_access:landing"))
            pilot_profile = getattr(request.user, "pilot_profile", None)
            if pilot_profile is None:
                return redirect(reverse("pilot_access:landing"))
            if not pilot_profile.disclaimer_accepted_at:
                return redirect(reverse("pilot_access:landing"))
            request.pilot_access_profile = pilot_profile
            request.pilot_access_registered = True
            return None

        # 2. System/infrastructure paths always pass through
        if self._is_exempt(path):
            return None

        # 3. Pilot auth flow paths (/pilot/*) always pass through
        #    (/pilot/account/ is caught above by _requires_auth)
        if path.startswith("/pilot/"):
            return None

        # 4. Web journey routes — require auth OR valid campaign session
        if request.user.is_authenticated:
            pilot_profile = getattr(request.user, "pilot_profile", None)
            if pilot_profile and pilot_profile.disclaimer_accepted_at:
                request.pilot_access_profile = pilot_profile
                request.pilot_access_registered = True
                return None

        # Campaign session check — campaign validated at entry via landing view
        # No per-request DB lookup needed; session expiry handles stale campaigns
        if request.session.get("campaign_code"):
            request.pilot_access_registered = False
            return None

        # No auth and no campaign session — redirect to landing
        return redirect(reverse("pilot_access:landing"))

    def process_response(self, request, response):
        """Add cache control headers for web journey and account pages."""
        path = request.path
        # System/infrastructure paths: no cache control needed
        if self._is_exempt(path):
            return response
        # Pilot auth flow pages (except account): no cache control needed
        if path.startswith("/pilot/") and not self._requires_auth(path):
            return response
        # Everything else (web journey + account pages): prevent back-button caching
        response["Cache-Control"] = "no-cache, no-store, must-revalidate, private"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        return response
