#urls.py
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from drf_spectacular.views import SpectacularRedocView
from api.admin import v1_admin_site, v2_admin_site, v3_admin_site
from api.admin_views import v3_location_detail_json
from htsh.admin_views import htsh_admin_site
from htsh.views import landing as htsh_landing

# Handle invalid page requests
handler404 = "web.errors.handler404"

# The default /admin/ landing page is just a hub (API versions + HTSH).
# Hide the nav sidebar there so it doesn't show an app/model tree.
admin.site.enable_nav_sidebar = False

urlpatterns = [
    path("admin/v3/location/<int:pk>/json/", v3_location_detail_json, name="v3_location_detail_json"),

    # Admin pages
    path("admin/v1/", v1_admin_site.urls),
    path("admin/v2/", v2_admin_site.urls),
    path("admin/v3/", v3_admin_site.urls),
    path("admin/htsh/", htsh_admin_site.urls),
    path("admin/", admin.site.urls),

    # REST API
    path("v1/", include(("api.v1.urls", "api-v1"), namespace="v1")),
    path("v2/", include(("api.v2.urls", "api-v2"), namespace="v2")),
    path("v3/", include(("api.v3.urls", "api-v3"), namespace="v3")),

    # API Documentation
    path("schema.yaml", SpectacularAPIView.as_view(), name="schema"),
    path("apidocs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # Health check
    path("health", include("api.health.urls")),

    # HTSH
    path("landing/", htsh_landing, name="landing"),
    path("", include(("htsh.urls", "htsh"), namespace="htsh")),

    # Website
    path("", include("web.urls")),
]
