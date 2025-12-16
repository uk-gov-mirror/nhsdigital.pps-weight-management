"""
Needed for logic in admin_v3.py that updates the inline location table when the location popup closes
"""

from django.http import JsonResponse, Http404
from django.contrib.admin.views.decorators import staff_member_required
from .models_v3 import V3_Location

@staff_member_required
def v3_location_detail_json(request, pk):
    try:
        loc = V3_Location.objects.get(pk=pk)
    except V3_Location.DoesNotExist:
        raise Http404("Location not found")

    data = {
        "id": loc.id,
        "address_1": loc.address_1,
        "address_2": loc.address_2,
        "town": loc.town,
        "postcode": loc.postcode,
        "opening_hours": loc.opening_hours,
    }
    return JsonResponse(data)
