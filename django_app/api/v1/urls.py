"""
URL routes for the V1 service catalogue API.

Exposes:
    - POST /api/v1/services       (search)
    - GET  /api/v1/service/<id>   (detail)

These routes are considered legacy. Prefer the V3 equivalents.
"""

from django.urls import path
from .views import ServiceSearchV1, ServiceDetailV1

urlpatterns = [
    path("services", ServiceSearchV1.as_view(), name="service-search"),        # POST (read-only search)
    path("service/<int:id>", ServiceDetailV1.as_view(), name="service-detail") # GET
]
