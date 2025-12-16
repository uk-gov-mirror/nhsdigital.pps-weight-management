"""
URL routes for the V3 service catalogue API.

Exposes:
    - POST /api/v3/services       (ServiceSearchV3)
    - GET  /api/v3/service/<id>   (ServiceDetailV3)
"""

from django.urls import path
from .views import ServiceSearchV3, ServiceDetailV3

urlpatterns = [
    path("services", ServiceSearchV3.as_view(), name="service-search"),        # POST (read-only search)
    path("service/<int:id>", ServiceDetailV3.as_view(), name="service-detail") # GET
]
