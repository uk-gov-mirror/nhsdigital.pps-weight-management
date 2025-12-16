"""
Version 3 database models for the weight management API.

These models map onto database tables/views with names starting "V3_".
They represent the current iteration of the service catalogue, including
locations, mitigations, time required, and other filter dimensions used by
the v3 API.

All models are:

- unmanaged (managed = False)
- registered under the "api" app (APP_LABEL)
- consumed by v3 serializers/views and admin for read-only inspection

Schema changes happen in the database layer, not via Django migrations.
"""

from django.db import models

APP_LABEL = "api"

class V3_Category(models.Model):
    id = models.AutoField(primary_key=True)
    goal = models.CharField(max_length=120)
    class Meta:
        db_table = "V3_CATEGORY"
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        return self.goal or f"Category #{getattr(self, 'id', '-')}"


class V3_HelpsWith(models.Model):
    id = models.AutoField(primary_key=True)
    benefit = models.CharField(max_length=120)
    class Meta:
        db_table = "V3_HELPS_WITH"
        verbose_name = "Helps With"
        verbose_name_plural = "Helps With"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        return self.benefit or f"Benefit #{getattr(self, 'id', '-')}"


class V3_WhoFor(models.Model):
    id = models.AutoField(primary_key=True)
    target = models.CharField(max_length=120)
    class Meta:
        db_table = "V3_WHO_FOR"
        verbose_name = "Who For"
        verbose_name_plural = "Who For"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        return self.target or f"Who For #{getattr(self, 'id', '-')}"


class V3_WhoNotFor(models.Model):
    id = models.AutoField(primary_key=True)
    target = models.CharField(max_length=120)
    class Meta:
        db_table = "V3_WHO_NOT_FOR"
        verbose_name = "Who Not For"
        verbose_name_plural = "Who Not For"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        return self.target or f"Who Not For #{getattr(self, 'id', '-')}"


class V3_Mitigations(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=120)
    class Meta:
        db_table = "V3_MITIGATIONS"
        verbose_name = "Mitigations"
        verbose_name_plural = "Mitigations"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        return self.type or f"Mitigation #{getattr(self, 'id', '-')}"


class V3_TimeRequired(models.Model):
    id = models.AutoField(primary_key=True)
    required = models.CharField(max_length=120)
    class Meta:
        db_table = "V3_TIME_REQUIRED"
        verbose_name = "Time Required"
        verbose_name_plural = "Time Required"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        return self.required or f"Time Required #{getattr(self, 'id', '-')}"


class V3_Access(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=120)
    class Meta:
        db_table = "V3_ACCESS"
        verbose_name = "Access"
        verbose_name_plural = "Accesses"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        return self.type or f"Access #{getattr(self, 'id', '-')}"


class V3_Costs(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=120)
    class Meta:
        db_table = "V3_COSTS"
        verbose_name = "Costs"
        verbose_name_plural = "Costs"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        return self.name or f"Cost #{getattr(self, 'id', '-')}"


class V3_ActionType(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=120)
    class Meta:
        db_table = "V3_ACTION_TYPE"
        verbose_name = "Action Type"
        verbose_name_plural = "Action Types"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        return self.type or f"Action Type #{getattr(self, 'id', '-')}"


class V3_ServiceType(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=120)
    class Meta:
        db_table = "V3_SERVICE_TYPE"
        verbose_name = "Service Type"
        verbose_name_plural = "Service Types"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        return self.type or f"Service Type #{getattr(self, 'id', '-')}"

class V3_Taxonomy(models.Model):
    id = models.AutoField(primary_key=True)
    term = models.CharField(max_length=120)
    class Meta:
        db_table = "V3_TAXONOMY"
        verbose_name = "Taxonomy"
        verbose_name_plural = "Taxonomies"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        return self.term or f"Taxonomy #{getattr(self, 'id', '-')}"


class V3_Contact(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=64, blank=True)
    email = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "V3_CONTACT"
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"
        app_label = APP_LABEL
        managed = False

    def __str__(self):
        return self.name or f"Contact #{getattr(self, 'id', '-')}"

class V3_Location(models.Model):
    id = models.AutoField(primary_key=True)
    address_1 = models.CharField(max_length=255)
    address_2 = models.CharField(max_length=255, blank=True)
    town = models.CharField(max_length=255, blank=True)
    postcode = models.CharField(max_length=32, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    opening_hours = models.CharField(max_length=255, blank=True)

    contact = models.ForeignKey(
        V3_Contact,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column="contact_id",
    )

    class Meta:
        db_table = "V3_LOCATION"
        verbose_name = "Location"
        verbose_name_plural = "Locations"
        app_label = APP_LABEL
        managed = False

    def __str__(self):
        """Return a compact string that encodes the main columns.

        This is used by the admin popup; the JS on the Service page
        splits this back into the individual table columns.
        """
        parts = [
            self.address_1 or "",
            self.address_2 or "",
            self.town or "",
            self.postcode or "",
            self.opening_hours or "",
        ]
        # Use ' | ' as a separator that is unlikely to appear in the data
        return " | ".join(parts).strip() or f"Location #{getattr(self, 'id', '-')}"

class V3_Service(models.Model):
    class Meta:
        db_table = "V3_SERVICE"
        verbose_name = "Service"
        verbose_name_plural = "Services"
        app_label = APP_LABEL
        managed = False
    def __str__(self):
        return self.name or f"Service #{getattr(self, 'id', '-')}"


    id = models.AutoField("Id", primary_key=True)
    name = models.CharField("Name", max_length=120)
    description = models.TextField("Description", blank=True)
    what_it_is = models.TextField("What it is", blank=True)
    how_it_works = models.TextField("How it works", blank=True)
    what_it_could_do = models.TextField("What it could do", blank=True)

    cost_text = models.CharField("Cost text", max_length=120, blank=True)
    action_text = models.CharField("Action text", max_length=120, blank=True)

    action_url = models.CharField("Action URL", max_length=255, blank=True)
    action_url_playstore = models.CharField("Playstore URL", max_length=255, blank=True)
    action_url_appstore = models.CharField("Appstore URL", max_length=255, blank=True)
    action_url_moreinfo = models.CharField("More Info URL", max_length=255, blank=True)

    logo_image = models.CharField("Logo image", max_length=255, blank=True)
    promo = models.CharField("Promo image", max_length=255, blank=True)
    opening_hours = models.CharField("Opening hours", max_length=255, blank=True)

    action = models.ForeignKey(V3_ActionType, null=True, blank=True, on_delete=models.SET_NULL, db_column="action_id")
    service_type = models.ForeignKey(V3_ServiceType, null=True, blank=True, on_delete=models.SET_NULL, db_column="service_type_id")

    sort_order = models.FloatField("Sort order", null=True, blank=True)

    # M2M via prefixed through tables (includes categories for V3)
    helps_with = models.ManyToManyField(V3_HelpsWith, through="V3_Service_HelpsWith", related_name="services")
    who_for = models.ManyToManyField(V3_WhoFor, through="V3_Service_WhoFor", related_name="services")
    who_not_for = models.ManyToManyField(V3_WhoNotFor, through="V3_Service_WhoNotFor", related_name="services")
    mitigations = models.ManyToManyField(V3_Mitigations, through="V3_Service_Mitigation", related_name="services")
    time_required = models.ManyToManyField(V3_TimeRequired, through="V3_Service_TimeRequired", related_name="services")
    access = models.ManyToManyField(V3_Access, through="V3_Service_Access", related_name="services")
    costs = models.ManyToManyField(V3_Costs, through="V3_Service_Cost", related_name="services")
    taxonomy = models.ManyToManyField(V3_Taxonomy, through="V3_Service_Taxonomy", related_name="services")
    categories = models.ManyToManyField(V3_Category, through="V3_Service_Category", related_name="services")
    contacts = models.ManyToManyField(V3_Contact, through="V3_Service_Contact", related_name="services")
    locations = models.ManyToManyField(V3_Location, through="V3_Service_Location", related_name="services")

# Through tables for V3
class V3_Service_Category(models.Model):
    class Meta:
        db_table = "V3_SERVICE_CATEGORY"
        verbose_name = "Service Category"
        verbose_name_plural = "Service Categories"
        app_label = APP_LABEL
        managed = False
    service = models.ForeignKey(V3_Service, on_delete=models.CASCADE)
    category = models.ForeignKey(V3_Category, on_delete=models.CASCADE)
    def __str__(self):
        return f"V3_Service_Category #{getattr(self, 'id', '-')}"


class V3_Service_HelpsWith(models.Model):
    class Meta:
        db_table = "V3_SERVICE_HELPS_WITH"
        verbose_name = "Service Helps With"
        verbose_name_plural = "Service Helps With"
        app_label = APP_LABEL
        managed = False
    service = models.ForeignKey(V3_Service, on_delete=models.CASCADE)
    helpswith = models.ForeignKey(V3_HelpsWith, on_delete=models.CASCADE, db_column="helpswith_id")
    def __str__(self):
        return f"V3_Service_HelpsWith #{getattr(self, 'id', '-') }"


class V3_Service_WhoFor(models.Model):
    class Meta:
        db_table = "V3_SERVICE_WHO_FOR"
        verbose_name = "Service Who For"
        verbose_name_plural = "Service Who For"
        app_label = APP_LABEL
        managed = False
    service = models.ForeignKey(V3_Service, on_delete=models.CASCADE)
    who_for = models.ForeignKey(V3_WhoFor, on_delete=models.CASCADE)
    def __str__(self):
        return f"V3_Service_WhoFor #{getattr(self, 'id', '-') }"


class V3_Service_WhoNotFor(models.Model):
    class Meta:
        db_table = "V3_SERVICE_WHO_NOT_FOR"
        verbose_name = "Service Who Not For"
        verbose_name_plural = "Service Who Not For"
        app_label = APP_LABEL
        managed = False
    service = models.ForeignKey(V3_Service, on_delete=models.CASCADE)
    who_not_for = models.ForeignKey(V3_WhoNotFor, on_delete=models.CASCADE)
    def __str__(self):
        return f"V3_Service_WhoNotFor #{getattr(self, 'id', '-') }"


class V3_Service_Mitigation(models.Model):
    class Meta:
        db_table = "V3_SERVICE_MITIGATIONS"
        verbose_name = "Service Mitigation"
        verbose_name_plural = "Service Mitigations"
        app_label = APP_LABEL
        managed = False
    service = models.ForeignKey(V3_Service, on_delete=models.CASCADE)
    mitigation = models.ForeignKey(V3_Mitigations, on_delete=models.CASCADE)
    def __str__(self):
        return f"V3_Service_Mitigation #{getattr(self, 'id', '-') }"


class V3_Service_TimeRequired(models.Model):
    class Meta:
        db_table = "V3_SERVICE_TIME_REQUIRED"
        verbose_name = "Service Time Required"
        verbose_name_plural = "Service Time Required"
        app_label = APP_LABEL
        managed = False
    service = models.ForeignKey(V3_Service, on_delete=models.CASCADE)
    time = models.ForeignKey(V3_TimeRequired, on_delete=models.CASCADE, db_column="time_id")
    def __str__(self):
        return f"V3_Service_TimeRequired #{getattr(self, 'id', '-') }"


class V3_Service_Access(models.Model):
    class Meta:
        db_table = "V3_SERVICE_ACCESS"
        verbose_name = "Service Access"
        verbose_name_plural = "Service Accesses"
        app_label = APP_LABEL
        managed = False
    service = models.ForeignKey(V3_Service, on_delete=models.CASCADE)
    access = models.ForeignKey(V3_Access, on_delete=models.CASCADE)
    def __str__(self):
        return f"V3_Service_Access #{getattr(self, 'id', '-') }"


class V3_Service_Cost(models.Model):
    class Meta:
        db_table = "V3_SERVICE_COSTS"
        verbose_name = "Service Cost"
        verbose_name_plural = "Service Costs"
        app_label = APP_LABEL
        managed = False
    service = models.ForeignKey(V3_Service, on_delete=models.CASCADE)
    cost = models.ForeignKey(V3_Costs, on_delete=models.CASCADE, db_column="cost_id")
    def __str__(self):
        return f"V3_Service_Cost #{getattr(self, 'id', '-') }"


class V3_Service_Taxonomy(models.Model):
    class Meta:
        db_table = "V3_SERVICE_TAXONOMY"
        verbose_name = "Service Taxonomy"
        verbose_name_plural = "Service Taxonomies"
        app_label = APP_LABEL
        managed = False
    service = models.ForeignKey(V3_Service, on_delete=models.CASCADE)
    taxonomy = models.ForeignKey(V3_Taxonomy, on_delete=models.CASCADE)
    def __str__(self):
        return f"V3_Service_Taxonomy #{getattr(self, 'id', '-') }"

class V3_Service_Contact(models.Model):
    class Meta:
        db_table = "V3_SERVICE_CONTACT"
        verbose_name = "Service Contact"
        verbose_name_plural = "Service Contacts"
        app_label = APP_LABEL
        managed = False

    service = models.ForeignKey(V3_Service, on_delete=models.CASCADE)
    contact = models.ForeignKey(V3_Contact, on_delete=models.CASCADE)

    def __str__(self):
        # Show the underlying contact’s name in the inline header
        if getattr(self, "contact", None) and getattr(self.contact, "name", "").strip():
            return self.contact.name
        return "Contact"

class V3_Service_Location(models.Model):
    class Meta:
        db_table = "V3_SERVICE_LOCATION"
        verbose_name = "Location"
        verbose_name_plural = "Locations"
        app_label = APP_LABEL
        managed = False
        unique_together = (("service", "location"),)

    service = models.ForeignKey(V3_Service, on_delete=models.CASCADE)
    location = models.ForeignKey(V3_Location, on_delete=models.CASCADE)

    def __str__(self):
        return f"V3_Service_Location #{getattr(self, 'id', '-')}"
