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

        # Staff users are admins, not pilot-registered users.
        if getattr(request.user, "is_staff", False):
            return redirect(reverse("pilot_access:landing"))
        
        # Require pilot profile
        pilot_profile = getattr(request.user, "pilot_profile", None)
        if pilot_profile is None:
            return redirect(reverse("pilot_access:landing"))

        # Require disclaimer acceptance
        if not pilot_profile.disclaimer_accepted_at:
            return redirect(reverse("pilot_access:accept_invitation"))

        # Make it easy for templates to show account/logout links.
        request.pilot_access_profile = pilot_profile
        request.pilot_access_registered = True

        return self.get_response(request)
    
    def process_response(self, request, response):
        """Add cache control headers to prevent back button showing pages after logout."""
        # Only add headers for authenticated pages (not public paths)
        path = request.path
        is_public = any(path.startswith(prefix) for prefix in settings.PILOT_ACCESS_PUBLIC_PATH_PREFIXES)
        
        if not is_public:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response
