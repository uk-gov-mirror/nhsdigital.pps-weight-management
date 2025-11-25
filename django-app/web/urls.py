from django.urls import path
from . import views

urlpatterns = [
    path('', views.start, name='home'),
    path('consent-to-pilot', views.consent_to_pilot, name='consent_to_pilot'),
    path('consent-to-ur', views.consent_to_ur, name='consent_to_ur'),
    path('details-name', views.details_name, name='details_name'),
    path('details-postcode', views.details_postcode, name='details_postcode'),
    path('details-contact-details', views.details_contact_details, name='details_contact_details'),
    path('goals', views.goals, name='goals'),
    path('barriers', views.barriers, name='barriers'),
    path('preference-who-with', views.preference_who_with, name='preference_who_with'),
    path('preference-timetable', views.preference_timetable, name='preference_timetable'),
    path('preference-channel', views.preference_channel, name='preference_channel'),
    path('listing', views.listing, name='listing'),
    path('detail/<int:service_id>', views.detail, name='detail'),
]
