"""
Version 2 database models for the weight management API.

These models map onto database tables/views with names starting "V2_".
They represent the second iteration of the service catalogue and filtering
schema used by the v2 API.

All models are:

- unmanaged (managed = False)
- registered under the "api" Django app (APP_LABEL)
- queried by v2 serializers/views and, optionally, Django admin

Schema is owned externally; Django should not generate migrations for these.
"""

from django.db import models

APP_LABEL = "api"

class V2_Category(models.Model):
    id = models.AutoField(primary_key=True)
    goal = models.CharField(max_length=120)
    class Meta:
        db_table = "V2_CATEGORY"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_Category #{getattr(self, 'id', '-') }"


class V2_HelpsWith(models.Model):
    id = models.AutoField(primary_key=True)
    benefit = models.CharField(max_length=120)
    class Meta:
        db_table = "V2_HELPS_WITH"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_HelpsWith #{getattr(self, 'id', '-') }"


class V2_WhoFor(models.Model):
    id = models.AutoField(primary_key=True)
    target = models.CharField(max_length=120)
    class Meta:
        db_table = "V2_WHO_FOR"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_WhoFor #{getattr(self, 'id', '-') }"


class V2_WhoNotFor(models.Model):
    id = models.AutoField(primary_key=True)
    target = models.CharField(max_length=120)
    class Meta:
        db_table = "V2_WHO_NOT_FOR"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_WhoNotFor #{getattr(self, 'id', '-') }"


class V2_Mitigations(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=120)
    class Meta:
        db_table = "V2_MITIGATIONS"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_Mitigations #{getattr(self, 'id', '-') }"


class V2_TimeRequired(models.Model):
    id = models.AutoField(primary_key=True)
    required = models.CharField(max_length=120)
    class Meta:
        db_table = "V2_TIME_REQUIRED"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_TimeRequired #{getattr(self, 'id', '-') }"


class V2_Access(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=120)
    class Meta:
        db_table = "V2_ACCESS"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_Access #{getattr(self, 'id', '-') }"


class V2_Costs(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=120)
    class Meta:
        db_table = "V2_COSTS"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_Costs #{getattr(self, 'id', '-') }"


class V2_ActionType(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=120)
    class Meta:
        db_table = "V2_ACTION_TYPE"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_ActionType #{getattr(self, 'id', '-') }"


class V2_ServiceType(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=120)
    class Meta:
        db_table = "V2_SERVICE_TYPE"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_ServiceType #{getattr(self, 'id', '-') }"


class V2_Taxonomy(models.Model):
    id = models.AutoField(primary_key=True)
    term = models.CharField(max_length=120)
    class Meta:
        db_table = "V2_TAXONOMY"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_Taxonomy #{getattr(self, 'id', '-') }"



class V2_Service(models.Model):
    class Meta:
        db_table = "V2_SERVICE"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_Service #{getattr(self, 'id', '-') }"


    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    what_it_is = models.TextField(blank=True)
    how_it_works = models.TextField(blank=True)
    what_it_could_do = models.TextField(blank=True)

    cost_text = models.CharField(max_length=120, blank=True)
    action_text = models.CharField(max_length=120, blank=True)

    action_url = models.CharField(max_length=255, blank=True)
    action_url_playstore = models.CharField(max_length=255, blank=True)
    action_url_appstore = models.CharField(max_length=255, blank=True)
    action_url_moreinfo = models.CharField(max_length=255, blank=True)

    logo_image = models.CharField(max_length=255, blank=True)
    promo = models.CharField(max_length=255, blank=True)

    action = models.ForeignKey(V2_ActionType, null=True, blank=True, on_delete=models.SET_NULL, db_column="action_id")
    service_type = models.ForeignKey(V2_ServiceType, null=True, blank=True, on_delete=models.SET_NULL, db_column="service_type_id")

    sort_order = models.FloatField(null=True, blank=True)

    # M2M via prefixed through tables (includes categories for v2)
    helps_with = models.ManyToManyField(V2_HelpsWith, through="V2_Service_HelpsWith", related_name="services")
    who_for = models.ManyToManyField(V2_WhoFor, through="V2_Service_WhoFor", related_name="services")
    who_not_for = models.ManyToManyField(V2_WhoNotFor, through="V2_Service_WhoNotFor", related_name="services")
    mitigations = models.ManyToManyField(V2_Mitigations, through="V2_Service_Mitigation", related_name="services")
    time_required = models.ManyToManyField(V2_TimeRequired, through="V2_Service_TimeRequired", related_name="services")
    access = models.ManyToManyField(V2_Access, through="V2_Service_Access", related_name="services")
    costs = models.ManyToManyField(V2_Costs, through="V2_Service_Cost", related_name="services")
    taxonomy = models.ManyToManyField(V2_Taxonomy, through="V2_Service_Taxonomy", related_name="services")
    categories = models.ManyToManyField(V2_Category, through="V2_Service_Category", related_name="services")


# Through tables for v2
class V2_Service_Category(models.Model):
    class Meta:
        db_table = "V2_SERVICE_CATEGORY"
        app_label = APP_LABEL
        managed = False
    service = models.ForeignKey(V2_Service, on_delete=models.CASCADE)
    category = models.ForeignKey(V2_Category, on_delete=models.CASCADE)
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_Service_Category #{getattr(self, 'id', '-') }"


class V2_Service_HelpsWith(models.Model):
    class Meta:
        db_table = "V2_SERVICE_HELPS_WITH"
        app_label = APP_LABEL
        managed = False
    service = models.ForeignKey(V2_Service, on_delete=models.CASCADE)
    helpswith = models.ForeignKey(V2_HelpsWith, on_delete=models.CASCADE, db_column="helpswith_id")
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_Service_HelpsWith #{getattr(self, 'id', '-') }"


class V2_Service_WhoFor(models.Model):
    class Meta:
        db_table = "V2_SERVICE_WHO_FOR"
        app_label = APP_LABEL
        managed = False
    service = models.ForeignKey(V2_Service, on_delete=models.CASCADE)
    who_for = models.ForeignKey(V2_WhoFor, on_delete=models.CASCADE)
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_Service_WhoFor #{getattr(self, 'id', '-') }"


class V2_Service_WhoNotFor(models.Model):
    class Meta:
        db_table = "V2_SERVICE_WHO_NOT_FOR"
        app_label = APP_LABEL
        managed = False
    service = models.ForeignKey(V2_Service, on_delete=models.CASCADE)
    who_not_for = models.ForeignKey(V2_WhoNotFor, on_delete=models.CASCADE)
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_Service_WhoNotFor #{getattr(self, 'id', '-') }"


class V2_Service_Mitigation(models.Model):
    class Meta:
        db_table = "V2_SERVICE_MITIGATIONS"
        app_label = APP_LABEL
        managed = False
    service = models.ForeignKey(V2_Service, on_delete=models.CASCADE)
    mitigation = models.ForeignKey(V2_Mitigations, on_delete=models.CASCADE)
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_Service_Mitigation #{getattr(self, 'id', '-') }"


class V2_Service_TimeRequired(models.Model):
    class Meta:
        db_table = "V2_SERVICE_TIME_REQUIRED"
        app_label = APP_LABEL
        managed = False
    service = models.ForeignKey(V2_Service, on_delete=models.CASCADE)
    time = models.ForeignKey(V2_TimeRequired, on_delete=models.CASCADE, db_column="time_id")
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_Service_TimeRequired #{getattr(self, 'id', '-') }"


class V2_Service_Access(models.Model):
    class Meta:
        db_table = "V2_SERVICE_ACCESS"
        app_label = APP_LABEL
        managed = False
    service = models.ForeignKey(V2_Service, on_delete=models.CASCADE)
    access = models.ForeignKey(V2_Access, on_delete=models.CASCADE)
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_Service_Access #{getattr(self, 'id', '-') }"


class V2_Service_Cost(models.Model):
    class Meta:
        db_table = "V2_SERVICE_COSTS"
        app_label = APP_LABEL
        managed = False
    service = models.ForeignKey(V2_Service, on_delete=models.CASCADE)
    cost = models.ForeignKey(V2_Costs, on_delete=models.CASCADE, db_column="cost_id")
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_Service_Cost #{getattr(self, 'id', '-') }"


class V2_Service_Taxonomy(models.Model):
    class Meta:
        db_table = "V2_SERVICE_TAXONOMY"
        app_label = APP_LABEL
        managed = False
    service = models.ForeignKey(V2_Service, on_delete=models.CASCADE)
    taxonomy = models.ForeignKey(V2_Taxonomy, on_delete=models.CASCADE)
    def __str__(self):
        for attr in ('name', 'title', 'label', 'description'):
            if hasattr(self, attr) and getattr(self, attr):
                return str(getattr(self, attr))
        return f"V2_Service_Taxonomy #{getattr(self, 'id', '-') }"

