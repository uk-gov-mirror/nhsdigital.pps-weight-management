from django.urls import path
from . import views

urlpatterns = [
    path('', views.start, name='home'),
    path('details-contact-details', views.details_contact_details, name='details_contact_details'),
    path('details-postcode', views.details_postcode, name='details_postcode'),
    path('goals', views.goals, name='goals'),
    path('barriers', views.barriers, name='barriers'),
    path('preference-who-with', views.preference_who_with, name='preference_who_with'),
    path('preference-timetable', views.preference_timetable, name='preference_timetable'),
    path('preference-channel', views.preference_channel, name='preference_channel'),
    path('listing', views.listing, name='listing'),
    path('detail/<int:service_id>', views.detail, name='detail'),
    path('favourite/toggle/<int:service_id>', views.toggle_favourite, name='toggle_favourite'),
    path('favourites', views.favourites_list, name='favourites'),
    path('success', views.success, name='success'),
    path('allow-check-in', views.allow_check_in, name='allow-check-in'),
    path('no-check-in', views.no_check_in, name='no_check_in'),
]
