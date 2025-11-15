# admin.py
from django.contrib import admin
from django.apps import apps as django_apps
from django.db import models

app_config = django_apps.get_containing_app_config(__name__)
if app_config is None:
    raise RuntimeError(
        "admin.py must live inside an installed Django app. "
        f"Module {__name__} is not inside any AppConfig."
    )

class GenericAdmin(admin.ModelAdmin):
    def __init__(self, model, admin_site):
        # concrete, non-m2m db fields
        concrete_fields = [
            f for f in model._meta.get_fields()
            if getattr(f, "concrete", False) and not getattr(f, "many_to_many", False)
        ]

        # Up to 5 columns, falling back to __str__ if empty
        self.list_display = [f.name for f in concrete_fields if hasattr(f, "attname")][:5] or ("__str__",)

        # Up to 3 texty fields for search
        self.search_fields = [
            f.name for f in concrete_fields if isinstance(f, (models.CharField, models.TextField))
        ][:3]

        # Safer than autocomplete_fields (no system-check dependency)
        self.raw_id_fields = [
            f.name for f in model._meta.fields if isinstance(f, models.ForeignKey)
        ]

        super().__init__(model, admin_site)

# Register every model in this app
for model in app_config.get_models():
    try:
        admin.site.register(model, GenericAdmin)
    except admin.sites.AlreadyRegistered:
        pass
