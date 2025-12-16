"""
URL routes for the V2 service catalogue API.

Exposes:
    - POST /api/v2/services       (search)
    - GET  /api/v2/service/<id>   (detail)

These routes are considered legacy. Prefer the V3 equivalents.
"""

from django.urls import path
from .views import ServiceSearchV2, ServiceDetailV2

urlpatterns = [
    path("services", ServiceSearchV2.as_view(), name="service-search"),        # POST (read-only search)
    path("service/<int:id>", ServiceDetailV2.as_view(), name="service-detail") # GET
]
