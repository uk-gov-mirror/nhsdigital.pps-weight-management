from django.urls import path
from . import views

urlpatterns = [
    path('', views.start, name='home'),
    path('details-contact-details', views.details_contact_details, name='details_contact_details'),
    path('details-postcode', views.details_postcode, name='details_postcode'),
    path('motivation', views.motivation, name='motivation'),
    path('priority-behaviour', views.priority_behaviour, name='priority_behaviour'),
    path('past-barriers', views.past_barriers, name='past_barriers'),
    path('current-barriers', views.current_barriers, name='current_barriers'),
    path('confidence-readiness', views.confidence_readiness, name='confidence_readiness'),
    path('enablers', views.enablers, name='enablers'),
    path('listing', views.listing, name='listing'),
    path('detail/<int:service_id>', views.detail, name='detail'),
    path('favourite/toggle/<int:service_id>', views.toggle_favourite, name='toggle_favourite'),
    path('favourites', views.favourites_list, name='favourites'),
    path('success', views.success, name='success'),
    path('allow-check-in', views.allow_check_in, name='allow-check-in'),
    path('no-check-in', views.no_check_in, name='no_check_in'),
]
