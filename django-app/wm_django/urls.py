from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from drf_spectacular.views import SpectacularRedocView

urlpatterns = [
    path("v1/", include(("api.v1.urls", "api-v1"), namespace="v1")),
    path("v2/", include(("api.v2.urls", "api-v2"), namespace="v2")),
    path("schema.yaml", SpectacularAPIView.as_view(), name="schema"),
    path("apidocs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("health", include("api.health.urls")),
    path("", include("web.urls")),
]
