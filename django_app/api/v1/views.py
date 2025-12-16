"""
V1 REST API views.

These endpoints are retained for backwards compatibility with early
consumers of the service catalogue API. They are not actively maintained.

For all new integrations, use the V3 endpoints in api.v3.views.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import serializers
from django.http import Http404
from api.models_v1 import V1_Service
from .serializers import (
    V1_ServiceSummarySerializer,
    V1_ServiceDetailSerializer,
    V1_ServiceSearchRequestSerializer,
)
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer

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

class ServiceSearchV1(APIView):
    """
    Search for services.
    Returns a subset of service details.
    """

    @extend_schema(
        tags=["V1"],
        summary="Search services",
        description=(
            "Search services. Returns a subset of service details."
        ),
        request=inline_serializer(
                name="ServiceSearchRequestV1",
                fields={
                    "limit": serializers.IntegerField(required=False, min_value=1, max_value=200, default=50),
                    "offset": serializers.IntegerField(required=False, min_value=0, default=0),
                    "filter": serializers.ListField(
                        required=False,
                        child=inline_serializer(
                            name="FilterGroup",
                            fields={
                                "or": serializers.ListField(child=serializers.CharField())
                            }
                        )
                    ),
                },
            ),
        responses={200: V1_ServiceSummarySerializer(many=True)},
        examples=[
            OpenApiExample(
                "Search services",
                value={
                    "filter": [
                        {"or": ["taught_by_a_person", "following_a_plan", "self_led"]},
                        {"or": ["alone", "one_to_one", "in_a_group"]},
                        {"or": ["venue_or_a_place", "wherever_works_for_you"]},
                        {"or": ["scheduled", "self_paced_plan", "on_demand"]},
                        {"or": ["in_real_life", "digital"]}
                    ],
                    "limit": 50,
                    "offset": 0
                },
            )
        ],
    )
    def post(self, request):
        data = request.data or {}
        # validate inputs for nice 400s in docs/UI
        serializer = V1_ServiceSearchRequestSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        limit = payload.get("limit", 50)
        offset = payload.get("offset", 0)

        qs = V1_Service.objects.all()

        groups = _parse_filter_groups(payload)
        if groups:
            qs = _apply_and_of_ors(qs, groups)

        qs = qs.order_by("sort_order", "name")[offset : offset + limit]
        return Response(V1_ServiceSummarySerializer(qs, many=True).data)

class ServiceDetailV1(APIView):
    """
    Get full details of a service.
    """

    @extend_schema(
        tags=["V1"],
        summary="Get service",
        description=(
            "Returns full service details."
        ),
        responses={200: V1_ServiceDetailSerializer(many=True)}
    )
    def get(self, request, id):
        try:
            obj = V1_Service.objects.get(pk=id)
        except V1_Service.DoesNotExist:
            return Response(
                {"error": f"Service not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(V1_ServiceDetailSerializer(obj).data)
