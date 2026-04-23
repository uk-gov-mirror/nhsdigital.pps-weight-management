"""
Django admin wiring for the HTSH API.

Responsibilities of this module:

- Define a small, generic GenericAdmin used for "simple" models.
- Detect API version from db_table prefix (V1_, V2_, V3_, ...).
- Create one AdminSite per API version (v1_admin_site, v2_admin_site, v3_admin_site)
- Register:
    * all V1_ models on v1_admin_site using GenericAdmin;
    * all V2_ models on v2_admin_site using GenericAdmin;
    * all V3_ models by delegating to admin_v3.configure_v3_admin();
    * all non-versioned models on the default admin.site at /admin/ using GenericAdmin.

All *version-specific* behaviour (custom forms, hiding through tables, custom
list displays, etc.) is delegated to separate admin_vX.py modules. For v3,
this lives in admin_v3.py and exposes a single function:

    configure_v3_admin(site: AdminSite, models: list[Model], generic_admin_cls: type)

which is called from this module. 

To create v4 in future:

- copy admin_v3.py -> admin_v4.py;
- adjust it for v4 models; and
- call configure_v4_admin() from this file, mirroring the v3 pattern.

"""

from django.conf import settings
from django.contrib import admin
from django.apps import apps as django_apps
from django.db import models

from .admin_v3 import configure_v3_admin

# --------------------------------------------------------------------
# Generic ModelAdmin
# --------------------------------------------------------------------
class GenericAdmin(admin.ModelAdmin):
    """
    A simple, generic ModelAdmin used for most models.

    - Shows up to 5 concrete fields in list_display.
    - Enables simple text search on up to 3 CharField/TextField columns.
    - Uses raw_id_fields for ForeignKey fields to keep the UI fast.
    """

    def __init__(self, model, admin_site):
        # concrete, non-m2m, non-reverse fields
        concrete_fields = [
            f
            for f in model._meta.get_fields()
            if getattr(f, "concrete", False)
            and not getattr(f, "many_to_many", False)
            and not getattr(f, "one_to_many", False)
        ]

        # up to 5 columns, falling back to __str__ if none
        self.list_display = [
            f.name for f in concrete_fields if hasattr(f, "attname")
        ][:5] or ("__str__",)

        # up to 3 text fields for search
        self.search_fields = [
            f.name
            for f in concrete_fields
            if isinstance(f, (models.CharField, models.TextField))
        ][:3]

        # use raw_id_fields for FKs
        self.raw_id_fields = [
            f.name for f in model._meta.fields if isinstance(f, models.ForeignKey)
        ]

        super().__init__(model, admin_site)


# --------------------------------------------------------------------
# Version detection helpers
# --------------------------------------------------------------------
def _db_table_prefix(model) -> str:
    """Return the prefix of the model's db_table before the first underscore."""
    table = model._meta.db_table or ""
    return table.split("_", 1)[0]


def get_model_version(model) -> str | None:
    """
    Return the version string ('V1', 'V2', 'V3', ...) for a model, or None
    if the table name does not look like a versioned API table.
    """
    prefix = _db_table_prefix(model)
    return prefix if prefix.startswith("V") and prefix[1:].isdigit() else None


# --------------------------------------------------------------------
# Environment / site titles
# --------------------------------------------------------------------
def _env_suffix() -> str:
    """Return a short environment suffix based on Django settings, e.g. ' (dev)'."""
    for attr in ("ENV_NAME", "ENVIRONMENT", "ENV", "ENVIRON"):
        value = getattr(settings, attr, None)
        if value:
            return f" ({value})"
    return ""

env_suffix = _env_suffix()

# Rebrand the *default* admin site used at /admin/
admin.site.site_header = f"HTSH API admin{env_suffix}"
admin.site.site_title = admin.site.site_header
admin.site.index_title = "Admin"

class VersionedAdminSite(admin.AdminSite):
    """AdminSite variant used for each API version (v1, v2, v3...)."""

    def __init__(self, version_label: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        label = f" - {version_label}" if version_label else ""
        # e.g. "HTSH API admin – v3 (Development)"
        self.site_header = f"HTSH API admin{label}{env_suffix}"
        self.site_title = self.site_header
        self.index_title = "Admin"

# Instantiate version-specific admin sites
v1_admin_site = VersionedAdminSite(version_label="v1", name="v1_admin")
v2_admin_site = VersionedAdminSite(version_label="v2", name="v2_admin")
v3_admin_site = VersionedAdminSite(version_label="v3", name="v3_admin")

# --------------------------------------------------------------------
# Model registration
# --------------------------------------------------------------------
app_config = django_apps.get_containing_app_config(__name__)
if app_config is None:
    raise RuntimeError(
        "admin.py must live inside an installed Django app. "
        f"Module {__name__} is not inside any AppConfig."
    )

all_models = list(app_config.get_models())

v1_models = []
v2_models = []
v3_models = []
other_models = []

for model in all_models:
    version = get_model_version(model)
    if version == "V1":
        v1_models.append(model)
    elif version == "V2":
        v2_models.append(model)
    elif version == "V3":
        v3_models.append(model)
    else:
        other_models.append(model)

# V1 and V2 models: simple registration using GenericAdmin
for model in v1_models:
    v1_admin_site.register(model, GenericAdmin)

for model in v2_models:
    v2_admin_site.register(model, GenericAdmin)

# V3 models: delegate to admin_v3 so all v3-specific behaviour
configure_v3_admin(site=v3_admin_site, models=v3_models, generic_admin_cls=GenericAdmin)

# Default /admin/: register only non-versioned models
for model in other_models:
    try:
        admin.site.register(model, GenericAdmin)
    except admin.sites.AlreadyRegistered:
        pass
