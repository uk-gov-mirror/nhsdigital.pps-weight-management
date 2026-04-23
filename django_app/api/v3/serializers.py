"""
Serializers for the V3 service catalogue API.

These serializers define:

    - V3_ServiceSummarySerializer:
        Compact representation used in search results.

    - V3_ServiceDetailSerializer:
        Full details for a single service, including goals, who it's for,
        mitigations, locations, and other metadata.

    - V3_ServiceSearchRequestSerializer:
        Input schema for the /services search endpoint, including the AND-of-ORs
        filter structure and optional postcode/distance fields.

They operate over the V3_* models defined in api.models_v3.
"""

import re
from rest_framework import serializers
from api.models_v3 import (
    V3_Service, V3_Category
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
from .geo import (
    UK_POSTCODE_REGEX,
    resolve_centre_and_radius,
    haversine_km,
)

class FilterGroupsField(serializers.ListField):
    """
    Accepts: [{"or": [...]}, ...] on input
    Normalizes to: [{"or_": [...]}, ...] so the nested serializer can validate.
    """
    def to_internal_value(self, data):
        if isinstance(data, list):
            normalized = []
            for g in data:
                if isinstance(g, dict) and "or" in g and "or_" not in g:
                    g = {**g, "or_": g["or"]}
                normalized.append(g)
            data = normalized
        return super().to_internal_value(data)
    
class V3_ServiceSummarySerializer(serializers.ModelSerializer):
    serviceName = serializers.CharField(source="name")
    sortOrder = serializers.FloatField(source="sort_order")
    logoImage = serializers.CharField(source="logo_image")
    costText  = serializers.CharField(source="cost_text")
    serviceType = serializers.CharField(source="service_type.type", allow_null=True)
    locations = serializers.SerializerMethodField()
    relevance_score = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = V3_Service
        fields = ["id","sortOrder","serviceName","description","logoImage","costText","serviceType","locations","relevance_score"]

    def get_locations(self, obj):
        if hasattr(obj, "locations"):
            return obj.locations.count()
            
class V3_ServiceDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    serviceName = serializers.CharField(source="name")
    description = serializers.CharField()
    whatItIs = serializers.CharField(source="what_it_is")
    howItWorks = serializers.CharField(source="how_it_works")
    whatItCouldDo = serializers.CharField(source="what_it_could_do")
    helpsWith = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    whoItsFor = serializers.SerializerMethodField()
    whoItsNotFor = serializers.SerializerMethodField()
    mitigationType = serializers.SerializerMethodField()
    howMuchTime = serializers.SerializerMethodField()
    howToAccess = serializers.SerializerMethodField()
    costText = serializers.CharField(source="cost_text")
    cost = serializers.SerializerMethodField()
    actionType = serializers.CharField(source="action.type", allow_null=True)
    actionText = serializers.CharField(source="action_text")
    actionUrl = serializers.CharField(source="action_url")
    appStoreUrl = serializers.CharField(source="action_url_appstore")
    playStoreUrl = serializers.CharField(source="action_url_playstore")
    moreInfoUrl = serializers.CharField(source="action_url_moreinfo")
    serviceType = serializers.CharField(source="service_type.type", allow_null=True)
    taxonomy = serializers.SerializerMethodField()
    logoImage = serializers.CharField(source="logo_image")
    promoImage = serializers.CharField(source="promo")
    contact = serializers.SerializerMethodField()
    opening_hours = serializers.CharField(allow_blank=True, allow_null=True)
    locations = serializers.SerializerMethodField()
    
    def get_helpsWith(self, obj):
        return list(obj.helps_with.values_list("benefit", flat=True))

    def get_category(self, obj):
        return list(obj.categories.values_list("goal", flat=True))

    def get_whoItsFor(self, obj):
        return list(obj.who_for.values_list("target", flat=True))

    def get_whoItsNotFor(self, obj):
        return list(obj.who_not_for.values_list("target", flat=True))

    def get_mitigationType(self, obj):
        return list(obj.mitigations.values_list("type", flat=True))

    def get_howMuchTime(self, obj):
        return list(obj.time_required.values_list("required", flat=True))

    def get_howToAccess(self, obj):
        return list(obj.access.values_list("type", flat=True))

    def get_cost(self, obj):
        return list(obj.costs.values_list("name", flat=True))

    def get_taxonomy(self, obj):
        return list(obj.taxonomy.values_list("term", flat=True))

    def _build_contact_dict(self, contact):
        if contact is None:
            return {
                "name": "",
                "phone": "",
                "email": "",
            }

        return {
            "name": getattr(contact, "name", "") or "",
            "phone": getattr(contact, "phone", "") or "",
            "email": getattr(contact, "email", "") or "",
        }

    def get_contact(self, obj):
        contact = None
        if hasattr(obj, "contacts"):
            contact = obj.contacts.first()
        return self._build_contact_dict(contact)

    def _get_centre_and_radius_from_request(self):
        """
        Extract centre (lat, lon) and radius (km) from the request using
        postcode + distance (miles) from query parameters.
        """
        request = self.context.get("request")
        if not request:
            return None, None, None

        qp = request.query_params
        raw_postcode = qp.get("postcode")
        raw_distance = qp.get("distance")

        return resolve_centre_and_radius(raw_postcode, raw_distance)

    def get_locations(self, obj):
        """
        Build the list of locations for this service.

        Each location includes:
        - address_1, address_2, town, postcode, lat, lon
        - contact (same as service-level contact)
        - opening_hours (same as service-level opening_hours)
        - in_radius: within the given radius (miles) of the postcode centre
        - distance: distance in miles (string), or "" if not computable
        """
        locations_qs = getattr(obj, "locations", None)
        if locations_qs is None:
            return []

        centre_lat, centre_lon, radius_km = self._get_centre_and_radius_from_request()

        result = []
        for loc in locations_qs.all():
            loc_lat = getattr(loc, "lat", None)
            loc_lon = getattr(loc, "lon", None)

            distance_km = None
            in_radius = False

            if (
                centre_lat is not None and centre_lon is not None and
                loc_lat is not None and loc_lon is not None
            ):
                try:
                    distance_km = haversine_km(
                        float(centre_lat),
                        float(centre_lon),
                        float(loc_lat),
                        float(loc_lon),
                    )
                    if radius_km is not None:
                        in_radius = distance_km <= radius_km
                except (TypeError, ValueError):
                    distance_km = None
                    in_radius = False

            # Convert km → miles for output
            if distance_km is not None:
                distance_miles = distance_km / 1.60934
                distance_str = f"{distance_miles:.2f}"
            else:
                distance_str = ""

            loc_contact = getattr(loc, "contact", None)
            contact_dict = self._build_contact_dict(loc_contact)

            loc_opening_hours = getattr(loc, "opening_hours", None)
            opening_hours = (loc_opening_hours or "")
        
            result.append({
                "address_1": getattr(loc, "address_1", "") or "",
                "address_2": getattr(loc, "address_2", "") or "",
                "town": getattr(loc, "town", "") or "",
                "postcode": getattr(loc, "postcode", "") or "",
                "lat": loc_lat,
                "lon": loc_lon,
                "contact": contact_dict,
                "opening_hours": opening_hours,
                "in_radius": in_radius,
                "distance": distance_str,
            })

        return result

        
class V3_CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = V3_Category
        fields = ["id","goal"]

class V3_ServiceSerializer(serializers.ModelSerializer):
    categories = V3_CategorySerializer(many=True, read_only=True)
    class Meta:
        model = V3_Service
        fields = [
            "id","name","description","what_it_is","how_it_works","what_it_could_do",
            "cost_text","action_text","action_url","action_url_playstore","action_url_appstore","action_url_moreinfo",
            "logo_image","promo","sort_order","action","service_type","categories",
        ]

class V3_FilterGroupSerializer(serializers.Serializer):
    # Python-safe field name; still renders as "or" on output because of source="or"
    or_ = serializers.ListField(
        source="or",
        child=serializers.CharField(),
        help_text='Any of these taxonomy terms may match within this group (OR).'
    )

class V3_ServiceSearchRequestSerializer(serializers.Serializer):
    limit = serializers.IntegerField(
        required=False,
        min_value=MIN_LIMIT,
        max_value=MAX_LIMIT,
        default=DEFAULT_LIMIT,
    )
    offset = serializers.IntegerField(
        required=False,
        min_value=MIN_OFFSET,
        default=DEFAULT_OFFSET,
    )
    filter = FilterGroupsField(
        required=False,
        child=V3_FilterGroupSerializer(),
        help_text=(
            'AND-of-ORs taxonomy filter. If omitted/empty, no taxonomy filter. '
            'Each object in "filter" is a group that is AND-ed; values in "or" are OR-ed.'
        ),
    )
    postcode = serializers.RegexField(
        UK_POSTCODE_REGEX,
        required=False,
        help_text='Centre postcode for distance-based logic, e.g. "SW1A 1AA".',
    )
    distance = serializers.FloatField(
        required=False,
        min_value=MIN_DISTANCE_MILES,
        max_value=MAX_DISTANCE_MILES,
        default=DEFAULT_DISTANCE_MILES,
        help_text=f"Radius in miles ({MIN_DISTANCE_MILES}–{MAX_DISTANCE_MILES}).",
    )

    def validate_postcode(self, value):
        # Normalise spacing/casing so you always get a clean value back
        return re.sub(r"\s+", " ", value.strip().upper())

    activity_attributes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="Activity attribute names from QuestionnaireResponse for relevance ranking.",
    )