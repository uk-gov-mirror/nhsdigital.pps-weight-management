from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("public/api/", include("api.urls_public")),    # /public/api/...
    path("secure/api/", include("api.urls_secure")),    # /secure/api/...
    path("health", include("core.urls_health")),        # /health
    path("", include("web.urls")),                      # Root pages
]

def secure_diag(request):
    return JsonResponse({
        "method": request.method,
        "auth_header": request.META.get("HTTP_AUTHORIZATION", "<missing>"),
        "content_type": request.META.get("CONTENT_TYPE"),
        "path": request.path,
    })

urlpatterns += [
    path("secure/api/_diag", secure_diag),
]