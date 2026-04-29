from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin


class HtshAccessMiddleware(MiddlewareMixin):
    def _requires_auth(self, path: str) -> bool:
        """Check if path requires full authentication (user + profile + disclaimer)."""
        path_with_slash = path if path.endswith("/") else path + "/"
        for prefix in settings.HTSH_AUTH_REQUIRED_PREFIXES:
            if path.startswith(prefix) or path_with_slash.startswith(prefix):
                return True
        return False

    def _is_exempt(self, path: str) -> bool:
        """Check if path is a system/infrastructure path exempt from all checks."""
        path_with_slash = path if path.endswith("/") else path + "/"
        for prefix in settings.HTSH_EXEMPT_PREFIXES:
            if path.startswith(prefix) or path_with_slash.startswith(prefix):
                return True
        return False

    def _is_auth_flow(self, path: str) -> bool:
        """Check if path is an HTSH auth flow path that always passes through."""
        path_with_slash = path if path.endswith("/") else path + "/"
        for prefix in settings.HTSH_AUTH_FLOW_PREFIXES:
            if path.startswith(prefix) or path_with_slash.startswith(prefix):
                return True
        return False

    def process_request(self, request):
        path = request.path

        # 1. Auth-required paths need fully authenticated HTSH user
        if self._requires_auth(path):
            if not request.user.is_authenticated:
                return redirect(reverse("landing"))
            if getattr(request.user, "is_staff", False):
                return redirect(reverse("landing"))
            profile = getattr(request.user, "profile", None)
            if profile is None:
                return redirect(reverse("landing"))
            if not profile.disclaimer_accepted_at:
                return redirect(reverse("landing"))
            request.htsh_profile = profile
            request.htsh_registered = True
            return None

        # 2. System/infrastructure paths always pass through
        if self._is_exempt(path):
            return None

        # 3. HTSH auth flow paths always pass through
        if self._is_auth_flow(path):
            return None

        # 4. Web journey routes — require auth OR valid campaign session
        if request.user.is_authenticated:
            profile = getattr(request.user, "profile", None)
            if profile and profile.disclaimer_accepted_at:
                request.htsh_profile = profile
                request.htsh_registered = True
                return None

        # Campaign session check — campaign validated at entry via landing view
        # No per-request DB lookup needed; session expiry handles stale campaigns
        if request.session.get("campaign_code"):
            request.htsh_registered = False
            return None

        # No auth and no campaign session — redirect to landing
        return redirect(reverse("landing"))

    def process_response(self, request, response):
        """Add cache control headers for web journey and account pages."""
        path = request.path
        # System/infrastructure paths: no cache control needed
        if self._is_exempt(path):
            return response
        # HTSH auth flow pages: no cache control needed
        if self._is_auth_flow(path):
            return response
        # Everything else (web journey + account pages): prevent back-button caching
        response["Cache-Control"] = "no-cache, no-store, must-revalidate, private"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        return response
