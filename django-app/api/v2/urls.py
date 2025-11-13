from django.urls import path
from .views import ServiceSearchV2, ServiceDetailV2

urlpatterns = [
    path("services", ServiceSearchV2.as_view(), name="service-search"),        # POST (read-only search)
    path("service/<int:id>", ServiceDetailV2.as_view(), name="service-detail") # GET
]
