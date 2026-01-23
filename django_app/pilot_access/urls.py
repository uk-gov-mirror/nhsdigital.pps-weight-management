from django.urls import path

from . import views

app_name = "pilot_access"

urlpatterns = [
    path("landing/", views.landing, name="landing"),
    path("contact-info/", views.campaign_contact_info, name="campaign_contact_info"),
    path("otp/", views.otp_verify, name="otp_verify"),
    path("disclaimer/", views.disclaimer, name="disclaimer"),
    path("logout/", views.logout_post, name="logout"),
    path("login/", views.magic_link_request, name="magic_link_request"),
    path("account/", views.account, name="account"),
    path("account/delete/", views.delete_account, name="delete_account"),
    path("returning/",views.returning, name="returning"),
    path("details-not-shared/", views.details_not_shared, name="details_not_shared"),
]
