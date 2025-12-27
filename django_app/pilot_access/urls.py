from django.urls import path

from . import views

app_name = "pilot_access"

urlpatterns = [
    path("landing/", views.landing, name="landing"),
    path("request-invite", views.request_invite, name="request_invite"),
    path("request-invite/done", views.request_invite_done, name="request_invite_done"),
    path("accept/", views.accept_invitation, name="accept_invitation"),
    path("logout/", views.logout_post, name="logout"),
    path("login/", views.magic_link_request, name="magic_link_request"),
    path("login/consume/", views.magic_link_consume, name="magic_link_consume"),
]
