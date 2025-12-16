"""
V2 serializers for the service catalogue API.

These serializers define the response shapes for the V2 endpoints and are kept
only to support existing V2 clients.

New development should target api.v3.serializers instead.
"""

from rest_framework import serializers
from api.models_v2 import (
    V2_Service, V2_Category
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
    
class V2_ServiceSummarySerializer(serializers.ModelSerializer):
    serviceName = serializers.CharField(source="name")
    sortOrder = serializers.FloatField(source="sort_order")
    logoImage = serializers.CharField(source="logo_image")
    costText  = serializers.CharField(source="cost_text")
    serviceType = serializers.CharField(source="service_type.type", allow_null=True)

    class Meta:
        model = V2_Service
        fields = ["id","sortOrder","serviceName","description","logoImage","costText","serviceType"]

class V2_ServiceDetailSerializer(serializers.Serializer):
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

class V2_CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = V2_Category
        fields = ["id","goal"]

class V2_ServiceSerializer(serializers.ModelSerializer):
    categories = V2_CategorySerializer(many=True, read_only=True)
    class Meta:
        model = V2_Service
        fields = [
            "id","name","description","what_it_is","how_it_works","what_it_could_do",
            "cost_text","action_text","action_url","action_url_playstore","action_url_appstore","action_url_moreinfo",
            "logo_image","promo","sort_order","action","service_type","categories",
        ]

class V2_FilterGroupSerializer(serializers.Serializer):
    # Python-safe field name; still renders as "or" on output because of source="or"
    or_ = serializers.ListField(
        source="or",
        child=serializers.CharField(),
        help_text='Any of these taxonomy terms may match within this group (OR).'
    )

class V2_ServiceSearchRequestSerializer(serializers.Serializer):
    limit = serializers.IntegerField(required=False, min_value=1, max_value=200, default=50)
    offset = serializers.IntegerField(required=False, min_value=0, default=0)
    filter = FilterGroupsField(
        required=False,
        child=V2_FilterGroupSerializer(),
        help_text=('AND-of-ORs taxonomy filter. If omitted/empty, no taxonomy filter. '
                   'Each object in "filter" is a group that is AND-ed; values in "or" are OR-ed.')
    )
