from django.db import models

class V1_HelpsWith(models.Model):
    id = models.AutoField(primary_key=True)
    benefit = models.CharField(max_length=120)
    class Meta: db_table = "V1_HELPS_WITH"; app_label = "api"

class V1_WhoFor(models.Model):
    id = models.AutoField(primary_key=True)
    target = models.CharField(max_length=120)
    class Meta: db_table = "V1_WHO_FOR"; app_label = "api"

class V1_WhoNotFor(models.Model):
    id = models.AutoField(primary_key=True)
    target = models.CharField(max_length=120)
    class Meta: db_table = "V1_WHO_NOT_FOR"; app_label = "api"

class V1_Mitigations(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=120)
    class Meta: db_table = "V1_MITIGATIONS"; app_label = "api"

class V1_TimeRequired(models.Model):
    id = models.AutoField(primary_key=True)
    required = models.CharField(max_length=120)
    class Meta: db_table = "V1_TIME_REQUIRED"; app_label = "api"

class V1_Access(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=120)
    class Meta: db_table = "V1_ACCESS"; app_label = "api"

class V1_Costs(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=120)
    class Meta: db_table = "V1_COSTS"; app_label = "api"

class V1_ActionType(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=120)
    class Meta: db_table = "V1_ACTION_TYPE"; app_label = "api"

class V1_ServiceType(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=120)
    class Meta: db_table = "V1_SERVICE_TYPE"; app_label = "api"

class V1_Taxonomy(models.Model):
    id = models.AutoField(primary_key=True)
    term = models.CharField(max_length=120)
    class Meta: db_table = "V1_TAXONOMY"; app_label = "api"


class V1_Service(models.Model):
    class Meta: db_table = "V1_SERVICE"; app_label = "api"

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

    action = models.ForeignKey(V1_ActionType, null=True, blank=True, on_delete=models.SET_NULL, db_column="action_id")
    service_type = models.ForeignKey(V1_ServiceType, null=True, blank=True, on_delete=models.SET_NULL, db_column="service_type_id")

    sort_order = models.FloatField(null=True, blank=True)

    # M2M via prefixed through tables
    helps_with = models.ManyToManyField(V1_HelpsWith, through="V1_Service_HelpsWith", related_name="services")
    who_for = models.ManyToManyField(V1_WhoFor, through="V1_Service_WhoFor", related_name="services")
    who_not_for = models.ManyToManyField(V1_WhoNotFor, through="V1_Service_WhoNotFor", related_name="services")
    mitigations = models.ManyToManyField(V1_Mitigations, through="V1_Service_Mitigation", related_name="services")
    time_required = models.ManyToManyField(V1_TimeRequired, through="V1_Service_TimeRequired", related_name="services")
    access = models.ManyToManyField(V1_Access, through="V1_Service_Access", related_name="services")
    costs = models.ManyToManyField(V1_Costs, through="V1_Service_Cost", related_name="services")
    taxonomy = models.ManyToManyField(V1_Taxonomy, through="V1_Service_Taxonomy", related_name="services")


# Through tables with prefixed names
class V1_Service_HelpsWith(models.Model):
    class Meta: db_table = "V1_SERVICE_HELPS_WITH"; app_label = "api"
    service = models.ForeignKey(V1_Service, on_delete=models.CASCADE)
    helpswith = models.ForeignKey(V1_HelpsWith, on_delete=models.CASCADE, db_column="helpswith_id")

class V1_Service_WhoFor(models.Model):
    class Meta: db_table = "V1_SERVICE_WHO_FOR"; app_label = "api"
    service = models.ForeignKey(V1_Service, on_delete=models.CASCADE)
    who_for = models.ForeignKey(V1_WhoFor, on_delete=models.CASCADE)

class V1_Service_WhoNotFor(models.Model):
    class Meta: db_table = "V1_SERVICE_WHO_NOT_FOR"; app_label = "api"
    service = models.ForeignKey(V1_Service, on_delete=models.CASCADE)
    who_not_for = models.ForeignKey(V1_WhoNotFor, on_delete=models.CASCADE)

class V1_Service_Mitigation(models.Model):
    class Meta: db_table = "V1_SERVICE_MITIGATIONS"; app_label = "api"
    service = models.ForeignKey(V1_Service, on_delete=models.CASCADE)
    mitigation = models.ForeignKey(V1_Mitigations, on_delete=models.CASCADE)

class V1_Service_TimeRequired(models.Model):
    class Meta: db_table = "V1_SERVICE_TIME_REQUIRED"; app_label = "api"
    service = models.ForeignKey(V1_Service, on_delete=models.CASCADE)
    time = models.ForeignKey(V1_TimeRequired, on_delete=models.CASCADE, db_column="time_id")

class V1_Service_Access(models.Model):
    class Meta: db_table = "V1_SERVICE_ACCESS"; app_label = "api"
    service = models.ForeignKey(V1_Service, on_delete=models.CASCADE)
    access = models.ForeignKey(V1_Access, on_delete=models.CASCADE)

class V1_Service_Cost(models.Model):
    class Meta: db_table = "V1_SERVICE_COSTS"; app_label = "api"
    service = models.ForeignKey(V1_Service, on_delete=models.CASCADE)
    cost = models.ForeignKey(V1_Costs, on_delete=models.CASCADE, db_column="cost_id")

class V1_Service_Taxonomy(models.Model):
    class Meta: db_table = "V1_SERVICE_TAXONOMY"; app_label = "api"
    service = models.ForeignKey(V1_Service, on_delete=models.CASCADE)
    taxonomy = models.ForeignKey(V1_Taxonomy, on_delete=models.CASCADE)
