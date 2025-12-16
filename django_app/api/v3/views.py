"""
V3 REST API views for the weight management service catalogue.

These views expose the public, read-only API used by the web frontend and
other consumers:

    - ServiceSearchV3 (POST /api/v3/services)
      Accepts a filter payload and returns a list of matching services.

    - ServiceDetailV3 (GET /api/v3/service/<id>)
      Returns full details for a single service.

The request/response schema is documented via drf-spectacular (@extend_schema)
and the serializers defined in api.v3.serializers.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from django.http import Http404
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer
from api.models_v3 import V3_Service
from .serializers import (
    V3_ServiceSummarySerializer,
    V3_ServiceDetailSerializer,
    V3_ServiceSearchRequestSerializer,
)
from .geo import (
    resolve_centre_and_radius,
    haversine_km,
)
from .constants import (
    DEFAULT_LIMIT,
    MIN_LIMIT,
    MAX_LIMIT,
    DEFAULT_OFFSET,
    MIN_OFFSET,
    DEFAULT_DISTANCE_MILES,
    MIN_DISTANCE_MILES,
    MAX_DISTANCE_MILES,
)

# --------------------------------
# Helpers
# --------------------------------

def _parse_filter_groups(payload):
    groups = []
    raw = (payload or {}).get("filter", [])
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return groups
    for g in raw:
        if isinstance(g, dict):
            terms = g.get("or") or []
            if isinstance(terms, str):
                terms = [terms]
            terms = [t.strip() for t in terms if isinstance(t, str) and t.strip()]
            if terms:
                groups.append(terms)
    return groups


def _apply_and_of_ors(qs, groups):
    for terms in groups:
        qs = qs.filter(taxonomy__term__in=terms)
    return qs.distinct()

# --------------------------------
# Views
# --------------------------------

class ServiceSearchV3(APIView):
    """
    Search for services.
    Returns a subset of service details.
    """

    @extend_schema(
        tags=["V3"],
        summary="Search services",
        description=("Search services. Returns a subset of service details."),
        request=inline_serializer(
            name="ServiceSearchRequestV3",
            fields={
                "limit": serializers.IntegerField(
                    required=False,
                    min_value=MIN_LIMIT,
                    max_value=MAX_LIMIT,
                    default=DEFAULT_LIMIT,
                ),
                "offset": serializers.IntegerField(
                    required=False,
                    min_value=MIN_OFFSET,
                    default=DEFAULT_OFFSET,
                ),
                "filter": serializers.ListField(
                    required=False,
                    child=inline_serializer(
                        name="FilterGroup",
                        fields={
                            "or": serializers.ListField(
                                child=serializers.CharField()
                            )
                        },
                    ),
                ),
                "postcode": serializers.CharField(
                    required=False,
                    help_text=(
                        'Postcode used as the centre point for distance '
                        'calculations, e.g. "SW1A 1AA".'
                    ),
                ),
                "distance": serializers.FloatField(
                    required=False,
                    help_text=(
                        f"Search radius in miles "
                        f"({MIN_DISTANCE_MILES}–{MAX_DISTANCE_MILES})."
                    ),
                    min_value=MIN_DISTANCE_MILES,
                    max_value=MAX_DISTANCE_MILES,
                    default=DEFAULT_DISTANCE_MILES,
                ),
            },
        ),
        responses={
            200: inline_serializer(
                name="ServiceSearchResponseV3",
                fields={
                    "total": serializers.IntegerField(),
                    "results": V3_ServiceSummarySerializer(many=True),
                },
            )
        },
        examples=[
            OpenApiExample(
                "Search services",
                value={
                    "filter": [
                        {"or": ["taught.taught_by_a_person"]},
                        {"or": ["who_with.alone", "who_with.in_a_group"]},
                        {
                            "or": [
                                "location.venue_or_a_place",
                                "location.wherever_works_for_you",
                            ]
                        },
                        {
                            "or": [
                                "timetable.scheduled",
                                "timetable.self_paced_plan",
                            ]
                        },
                        {"or": ["channel.in_real_life", "channel.digital"]},
                    ],
                    "limit": DEFAULT_LIMIT,
                    "offset": DEFAULT_OFFSET,
                },
            )
        ],
    )    
    def post(self, request):
        data = request.data or {}

        # validate inputs for nice 400s in docs/UI
        serializer = V3_ServiceSearchRequestSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        limit = payload.get("limit", DEFAULT_LIMIT)
        offset = payload.get("offset", DEFAULT_OFFSET)

        qs = V3_Service.objects.all()

        groups = _parse_filter_groups(payload)
        if groups:
            qs = _apply_and_of_ors(qs, groups)

        # Apply stable ordering before any in-Python filtering
        qs = qs.order_by("sort_order", "name")

        centre_lat, centre_lon, radius_km = resolve_centre_and_radius(
            payload.get("postcode"),
            payload.get("distance"),
        )

        # If we have a valid centre and radius, filter by distance:
        # - services with NO locations are always included
        # - services with 1+ locations are included if ANY location is within radius
        if (
            centre_lat is not None
            and centre_lon is not None
            and radius_km is not None
        ):
            services = list(qs.prefetch_related("locations"))
            filtered = []

            for service in services:
                locations_qs = getattr(service, "locations", None)
                if locations_qs is None:
                    # No locations relation at all – include by default
                    filtered.append(service)
                    continue

                locations = list(locations_qs.all())
                if not locations:
                    # Explicitly no locations – include by default
                    filtered.append(service)
                    continue

                in_radius = False
                for loc in locations:
                    loc_lat = getattr(loc, "lat", None)
                    loc_lon = getattr(loc, "lon", None)
                    if loc_lat is None or loc_lon is None:
                        continue
                    try:
                        distance_km = haversine_km(
                            float(centre_lat),
                            float(centre_lon),
                            float(loc_lat),
                            float(loc_lon),
                        )
                    except (TypeError, ValueError):
                        continue

                    if radius_km is not None and distance_km <= radius_km:
                        in_radius = True
                        break

                if in_radius:
                    filtered.append(service)

            total = len(filtered)
            page_services = filtered[offset : offset + limit]
            results = V3_ServiceSummarySerializer(page_services, many=True).data
        else:
            # No valid postcode/distance – behave as before (taxonomy-only)
            total = qs.count()
            page_qs = qs[offset : offset + limit]
            results = V3_ServiceSummarySerializer(page_qs, many=True).data

        return Response({"total": total, "results": results})

class ServiceDetailV3(APIView):
    """
    Get full details of a service.
    """

    @extend_schema(
        tags=["V3"],
        summary="Get service",
        description=("Returns full service details."),
        responses={200: V3_ServiceDetailSerializer(many=False)},
    )
    def get(self, request, id):
        try:
            obj = V3_Service.objects.get(pk=id)
        except V3_Service.DoesNotExist:
            return Response(
                {"error": "Service not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = V3_ServiceDetailSerializer(obj, context={"request": request})
        return Response(serializer.data)
