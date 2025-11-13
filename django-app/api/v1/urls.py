from django.urls import path
from .views import ServiceSearchV1, ServiceDetailV1

urlpatterns = [
    path("services", ServiceSearchV1.as_view(), name="service-search"),        # POST (read-only search)
    path("service/<int:id>", ServiceDetailV1.as_view(), name="service-detail") # GET
]
