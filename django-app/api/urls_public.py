from django.urls import path
from .views import public_ping

urlpatterns = [
    path("ping", public_ping, name="public-ping"),
]
