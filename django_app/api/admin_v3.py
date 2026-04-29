"""
admin_v3.py

Version 3 (V3_) admin configuration for the HTSH API.

This module is responsible for *all* v3-specific admin customisation.
It exposes a single entry point used by api.admin:

    configure_v3_admin(site, models, generic_admin_cls)
"""

from django import forms
from django.contrib import admin
from django.db import models
from django.http import HttpResponseRedirect
from django.urls import reverse

import json

from django.contrib.admin import helpers
from django.utils.translation import gettext
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from django.core import serializers
from django.http import HttpResponse
from django.urls import path

from .models_v3 import (
    V3_Service,
    V3_ActionType,
    V3_ServiceType,
    V3_Access,
    V3_Category,
    V3_Costs,
    V3_HelpsWith,
    V3_Mitigations,
    V3_Taxonomy,
    V3_TimeRequired,
    V3_WhoFor,
    V3_WhoNotFor,
    V3_Contact,
    V3_Location,
    V3_Service_Category,
    V3_Service_HelpsWith,
    V3_Service_WhoFor,
    V3_Service_WhoNotFor,
    V3_Service_Mitigation,
    V3_Service_TimeRequired,
    V3_Service_Access,
    V3_Service_Cost,
    V3_Service_Taxonomy,
    V3_Service_Contact,
    V3_Service_Location,
)

# --------------------------------------------------------------------
# Helper functions for human-readable labels and ordering
# --------------------------------------------------------------------
LABEL_ATTR_CANDIDATES = (
    "name",
    "type",
    "benefit",
    "required",
    "target",
    "term",
    "goal",
    "title",
    "label",
    "description",
    "address_1",
    "town",
    "postcode",
)

def label_for_instance(obj) -> str:
    """Return a human-readable label for a lookup instance."""
    for attr in LABEL_ATTR_CANDIDATES:
        if hasattr(obj, attr):
            value = getattr(obj, attr)
            if isinstance(value, str) and value.strip():
                return value
    return str(obj)


def order_queryset_for_model(model_cls, base_qs=None):
    """Order a queryset alphabetically using the best available text field."""
    if base_qs is None:
        base_qs = model_cls.objects.all()

    text_fields = {
        f.name
        for f in model_cls._meta.get_fields()
        if isinstance(f, (models.CharField, models.TextField))
    }
    for attr in LABEL_ATTR_CANDIDATES:
        if attr in text_fields:
            return base_qs.order_by(attr)

    field_names = {f.name for f in model_cls._meta.get_fields() if hasattr(f, "attname")}
    if "id" in field_names:
        return base_qs.order_by("id")

    return base_qs

# --------------------------------------------------------------------
# Custom form for V3_Service
# --------------------------------------------------------------------
class V3_ServiceForm(forms.ModelForm):
    """
    Custom form for V3_Service.
    """

    # Form-only multi-select fields
    helps_with_choices = forms.ModelMultipleChoiceField(
        queryset=V3_HelpsWith.objects.none(),
        required=False,
        label="Helps with",
    )
    who_for_choices = forms.ModelMultipleChoiceField(
        queryset=V3_WhoFor.objects.none(),
        required=False,
        label="Who for",
    )
    who_not_for_choices = forms.ModelMultipleChoiceField(
        queryset=V3_WhoNotFor.objects.none(),
        required=False,
        label="Who not for",
    )
    mitigations_choices = forms.ModelMultipleChoiceField(
        queryset=V3_Mitigations.objects.none(),
        required=False,
        label="Mitigations",
    )
    time_required_choices = forms.ModelMultipleChoiceField(
        queryset=V3_TimeRequired.objects.none(),
        required=False,
        label="Time required",
    )
    access_choices = forms.ModelMultipleChoiceField(
        queryset=V3_Access.objects.none(),
        required=False,
        label="Access",
    )
    costs_choices = forms.ModelMultipleChoiceField(
        queryset=V3_Costs.objects.none(),
        required=False,
        label="Costs",
    )
    taxonomy_choices = forms.ModelMultipleChoiceField(
        queryset=V3_Taxonomy.objects.none(),
        required=False,
        label="Taxonomy",
    )
    categories_choices = forms.ModelMultipleChoiceField(
        queryset=V3_Category.objects.none(),
        required=False,
        label="Categories",
    )

    class Meta:
        model = V3_Service
        fields = [
            "name",
            "description",
            "what_it_is",
            "action",
            "service_type",
            "sort_order",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Consistent widths for controls
        text_style = {"style": "width: 420px;"}
        select_style = {"style": "width: 420px;"}
        multiselect_style = {"style": "width: 420px; height: 200px;"}

        # Single-select lookup fields
        single_lookups = {
            "action": V3_ActionType,
            "service_type": V3_ServiceType,
        }

        for field_name, model_cls in single_lookups.items():
            if field_name in self.fields:
                field = self.fields[field_name]
                if isinstance(field, forms.ModelChoiceField):
                    field.queryset = order_queryset_for_model(model_cls, field.queryset)
                    field.label_from_instance = label_for_instance
                    field.widget.attrs.update(select_style)

        # Multi-select lookup fields: map form field name -> (model relation name, model class)
        multi_lookups = {
            "helps_with_choices": ("helps_with", V3_HelpsWith),
            "who_for_choices": ("who_for", V3_WhoFor),
            "who_not_for_choices": ("who_not_for", V3_WhoNotFor),
            "mitigations_choices": ("mitigations", V3_Mitigations),
            "time_required_choices": ("time_required", V3_TimeRequired),
            "access_choices": ("access", V3_Access),
            "costs_choices": ("costs", V3_Costs),
            "taxonomy_choices": ("taxonomy", V3_Taxonomy),
            "categories_choices": ("categories", V3_Category),
        }

        for field_name, (rel_name, model_cls) in multi_lookups.items():
            field = self.fields[field_name]
            if isinstance(field, forms.ModelMultipleChoiceField):
                field.queryset = order_queryset_for_model(model_cls)
                field.label_from_instance = label_for_instance
                field.widget.attrs.update(multiselect_style)

                # Set initial values when editing an existing instance
                if self.instance and self.instance.pk:
                    field.initial = getattr(self.instance, rel_name).all()

        # Style text inputs / textareas to match width
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.TextInput, forms.Textarea)):
                widget.attrs.setdefault("style", "")
                widget.attrs["style"] += (" " if widget.attrs["style"] else "") + text_style["style"]
                
    def save(self, commit=True):
        return super().save(commit=commit)

# --------------------------------------------------------------------
# Inline form for service contact (edit fields directly on the service page)
# --------------------------------------------------------------------
class V3_ServiceContactForm(forms.ModelForm):
    """Inline form backed by V3_Service_Contact but exposing V3_Contact fields."""

    contact_name = forms.CharField(label="Name", max_length=255, required=True)
    contact_phone = forms.CharField(label="Phone", max_length=64, required=False)
    contact_email = forms.EmailField(label="Email", max_length=255, required=False)

    class Meta:
        model = V3_Service_Contact
        # We do not expose the FK fields directly; they are managed in save().
        fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        contact = getattr(self.instance, "contact", None)
        if contact is not None:
            self.fields["contact_name"].initial = getattr(contact, "name", "")
            self.fields["contact_phone"].initial = getattr(contact, "phone", "")
            self.fields["contact_email"].initial = getattr(contact, "email", "")

    def save(self, commit=True):
        """Create/update the related V3_Contact, then the join row."""
        instance = super().save(commit=False)
        cd = self.cleaned_data

        # Either reuse the existing contact or create a new one
        contact = getattr(instance, "contact", None) or V3_Contact()
        contact.name = cd.get("contact_name", "") or ""
        contact.phone = cd.get("contact_phone", "") or ""
        contact.email = cd.get("contact_email", "") or ""

        if commit:
            contact.save()
            instance.contact = contact
            instance.save()
        else:
            instance.contact = contact

        return instance

# --------------------------------------------------------------------
# Inline form for location contact (edit fields directly on the loction page)
# --------------------------------------------------------------------
class V3_LocationForm(forms.ModelForm):
    contact_name = forms.CharField(label="Contact name", max_length=255, required=False)
    contact_phone = forms.CharField(label="Contact phone", max_length=64, required=False)
    contact_email = forms.EmailField(label="Contact email", max_length=255, required=False)

    class Meta:
        model = V3_Location
        fields = [
            "address_1",
            "address_2",
            "town",
            "postcode",
            "opening_hours",
            "lat",
            "lon",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        contact = getattr(self.instance, "contact", None)
        if contact is not None:
            self.fields["contact_name"].initial = getattr(contact, "name", "")
            self.fields["contact_phone"].initial = getattr(contact, "phone", "")
            self.fields["contact_email"].initial = getattr(contact, "email", "")

    def save(self, commit=True):
        # Let the parent build the instance, but don't save to DB yet
        instance = super().save(commit=False)
        cd = self.cleaned_data

        has_contact_data = any(
            bool(cd.get(key))
            for key in ("contact_name", "contact_phone", "contact_email")
        )

        if has_contact_data:
            # Reuse existing contact if any, else create a new one
            contact = getattr(instance, "contact", None) or V3_Contact()
            contact.name = cd.get("contact_name", "") or ""
            contact.phone = cd.get("contact_phone", "") or ""
            contact.email = cd.get("contact_email", "") or ""

            # IMPORTANT: Always save the contact here; the admin will NOT do it
            contact.save()
            instance.contact = contact
        else:
            # No contact details entered: clear any existing link
            instance.contact = None

        # Only save the Location if commit=True
        if commit:
            instance.save()

        return instance

# --------------------------------------------------------------------
# Inlines for contacts and locations
# --------------------------------------------------------------------
class V3_ServiceContactInline(admin.TabularInline):
    """Inline for the join between service and contact.

    - Shows only the contact linked to this service (zero or one row).
    - Allows editing of the contact fields (name, phone, email) directly inline.
    """

    model = V3_Service_Contact
    form = V3_ServiceContactForm
    extra = 0
    max_num = 1
    can_delete = True
    fields = ("contact_name", "contact_phone", "contact_email")


class V3_ServiceLocationInline(admin.TabularInline):
    """Inline for locations for a service.

    Shows one row per linked location:

    - Uses the location FK raw-id widget under the hood so the standard
      Django “add” popup (green plus) works.
    - Displays the location details as read-only columns (address, town,
      postcode, opening hours) in the table.
    - A Javascript function updates those columns when a new location is added
      via the popup, without reloading the whole page.
    """

    model = V3_Service_Location
    extra = 0
    can_delete = True

    fields = (
        "location",     # Include the underlying FK field so the raw-id widget + icons render
        "address_1_display",
        "address_2_display",
        "town_display",
        "postcode_display",
    )

    # Make the row read-only from the inline’s point of view –
    readonly_fields = (
        "address_1_display",
        "address_2_display",
        "town_display",
        "postcode_display",
    )

    # Get the related location
    def _loc(self, obj):
        return getattr(obj, "location", None)

    # Read-only columns
    def address_1_display(self, obj):
        loc = self._loc(obj)
        return loc.address_1 if loc else ""

    def address_2_display(self, obj):
        loc = self._loc(obj)
        return loc.address_2 if loc else ""

    def town_display(self, obj):
        loc = self._loc(obj)
        return loc.town if loc else ""

    def postcode_display(self, obj):
        loc = self._loc(obj)
        return loc.postcode if loc else ""

    # Column headings
    address_1_display.short_description = _("Address 1")
    address_2_display.short_description = _("Address 2")
    town_display.short_description = _("Town / City")
    postcode_display.short_description = _("Postcode")

    class Media:
        css = {"all": ("assets/css/admin.css",),}
        js  = ("assets/javascript/v3_locations_inline.js",)

# --------------------------------------------------------------------
# Override text to remove "another"
# --------------------------------------------------------------------
class ContactInlineAdminFormSet(helpers.InlineAdminFormSet):
    """Use 'Add a contact' instead of 'Add another Contact'."""

    def inline_formset_data(self):
        return json.dumps({
            "name": f"#{self.formset.prefix}",
            "options": {
                "prefix": self.formset.prefix,
                "addText": gettext("Add a contact"),
                "deleteText": gettext("Remove"),
            },
        })


class LocationInlineAdminFormSet(helpers.InlineAdminFormSet):
    """Use 'Add a location' instead of 'Add another Location'."""

    def inline_formset_data(self):
        return json.dumps({
            "name": f"#{self.formset.prefix}",
            "options": {
                "prefix": self.formset.prefix,
                "addText": gettext("Add a location"),
                "deleteText": gettext("Remove"),
            },
        })

# --------------------------------------------------------------------
# ModelAdmin for V3_Service
# --------------------------------------------------------------------
class V3_ServiceAdmin(admin.ModelAdmin):
    """Custom admin for the V3_Service model used by the v3 admin site."""

    form = V3_ServiceForm
    inlines = [V3_ServiceContactInline, V3_ServiceLocationInline]

    # Shows an "Export V3 Data" button on the admin page
    change_list_template = "admin/api/v3_service/change_list.html"

    # Changelist configuration
    list_display = ("name", "service_type_label", "description", "sort_order")
    list_display_links = ("name",)
    list_filter = ()  # remove the filter sidebar
    search_fields = ("name", "description")
    ordering = ("name",)

    fieldsets = (
        ("Main information", {
            "fields": (
                "name",
                "description",
                "what_it_is",
                "how_it_works",
                "what_it_could_do",
                "opening_hours",
                "service_type",
                "cost_text",
            )
        }),
        ("Action Links", {
            "fields": (
                "action",
                "action_text",
                "action_url",
                "action_url_playstore",
                "action_url_appstore",
                "action_url_moreinfo",
            )
        }),
        ("Images", {
            "fields": (
                "logo_image",
                "promo",
            )
        }),
        ("Ordering", {"fields": ("sort_order",)}),
        ("Who and what it helps", {
            "fields": (
                "helps_with_choices",
                "who_for_choices",
                "who_not_for_choices",
                "mitigations_choices",
                "time_required_choices",
            )
        }),
        ("Access, costs and taxonomy", {
            "fields": (
                "access_choices",
                "costs_choices",
                "taxonomy_choices",
                "categories_choices",
            )
        }),
    )

    def get_inline_formsets(self, request, formsets, inline_instances, obj=None):
        """
        Swap in custom InlineAdminFormSet classes so the 'Add another ...'
        text for contacts/locations becomes 'Add a contact/location'.
        """
        inline_formsets = list(
            super().get_inline_formsets(request, formsets, inline_instances, obj)
        )

        for inline_formset in inline_formsets:
            model = inline_formset.opts.model
            if model is V3_Service_Contact:
                inline_formset.__class__ = ContactInlineAdminFormSet
            elif model is V3_Service_Location:
                inline_formset.__class__ = LocationInlineAdminFormSet

        return inline_formsets
        
    def service_type_label(self, obj):
        """Display the human-readable service type instead of the raw repr."""
        if obj.service_type_id is None:
            return ""
        st = obj.service_type
        for attr in ("name", "type", "title", "label", "description"):
            if hasattr(st, attr):
                value = getattr(st, attr)
                if isinstance(value, str) and value.strip():
                    return value
        return str(st)

    def save_related(self, request, form, formsets, change):
        """
        After the main object and inlines are saved, sync the form-only
        *_choices fields back to the real M2M relations.
        """
        super().save_related(request, form, formsets, change)

        instance = form.instance
        if not instance.pk:
            return

        mapping = {
            "helps_with_choices": "helps_with",
            "who_for_choices": "who_for",
            "who_not_for_choices": "who_not_for",
            "mitigations_choices": "mitigations",
            "time_required_choices": "time_required",
            "access_choices": "access",
            "costs_choices": "costs",
            "taxonomy_choices": "taxonomy",
            "categories_choices": "categories",
        }

        for form_name, rel_name in mapping.items():
            values = form.cleaned_data.get(form_name)
            if values is not None:
                getattr(instance, rel_name).set(values)

    service_type_label.short_description = "Service Type"
    service_type_label.admin_order_field = "service_type__type"

# --------------------------------------------------------------------
# ModelAdmin for V3_Location
# --------------------------------------------------------------------
class V3_LocationAdmin(admin.ModelAdmin):
    """
    Custom admin for V3_Location used by the v3 admin site.

    - Uses V3_LocationForm to expose contact_name/phone/email instead of the
      raw contact FK.
    """

    form = V3_LocationForm

    fieldsets = (
        (None, {
            "fields": (
                "address_1",
                "address_2",
                "town",
                "postcode",
                "opening_hours",
                "lat",
                "lon",
            )
        }),
        ("Contact", {
            "fields": (
                "contact_name",
                "contact_phone",
                "contact_email",
            )
        }),
    )

    class Media:
        css = {"all": ("assets/css/admin.css",)}

# --------------------------------------------------------------------
# Lookup ModelAdmin classes for V3 lookup tables
# --------------------------------------------------------------------
class SimpleTextColumnAdmin(admin.ModelAdmin):
    """Base class: single text column, used as the edit link, no ID."""

    text_field_name: str = ""

    list_filter = ()
    search_fields = ()
    ordering = ()

    def get_list_display(self, request):
        return (self.text_field_name,)

    def get_list_display_links(self, request, list_display):
        return (self.text_field_name,)

    def get_search_fields(self, request):
        return (self.text_field_name,)

    def get_ordering(self, request):
        return (self.text_field_name,)

class V3_AccessAdmin(SimpleTextColumnAdmin):
    text_field_name = "type"

class V3_ActionTypeAdmin(SimpleTextColumnAdmin):
    text_field_name = "type"

class V3_CategoryAdmin(SimpleTextColumnAdmin):
    text_field_name = "goal"

class V3_CostsAdmin(SimpleTextColumnAdmin):
    text_field_name = "name"

class V3_HelpsWithAdmin(SimpleTextColumnAdmin):
    text_field_name = "benefit"

class V3_MitigationsAdmin(SimpleTextColumnAdmin):
    text_field_name = "type"

class V3_ServiceTypeAdmin(SimpleTextColumnAdmin):
    text_field_name = "type"

class V3_TaxonomyAdmin(SimpleTextColumnAdmin):
    text_field_name = "term"

class V3_TimeRequiredAdmin(SimpleTextColumnAdmin):
    text_field_name = "required"

class V3_WhoForAdmin(SimpleTextColumnAdmin):
    text_field_name = "target"

class V3_WhoNotForAdmin(SimpleTextColumnAdmin):
    text_field_name = "target"

# --------------------------------------------------------------------
# Public entry point used by api.admin
# --------------------------------------------------------------------
def configure_v3_admin(site: admin.AdminSite, models: list, generic_admin_cls: type) -> None:
    """
    Wire all V3_* models into the given AdminSite.
    """

    # ------------------------------------------------------------------
    # Custom "Export V3 data" view
    # ------------------------------------------------------------------
    def export_v3_data_view(request):
        """
        Admin view: clean up orphan contacts/locations and return all V3_*
        data as a JSON fixture download.
        """

        # Clean up orphans:
        # Orphan contacts: no service contacts and no locations.
        orphan_contacts = V3_Contact.objects.filter(
            v3_service_contact__isnull=True,
            v3_location__isnull=True,
        )

        # Orphan locations: no service locations.
        orphan_locations = V3_Location.objects.filter(
            v3_service_location__isnull=True,
        )

        # Delete orphans
        orphan_contacts.delete()
        orphan_locations.delete()

        # Collect all V3_* objects
        model_order = [
            # Lookup tables
            V3_ActionType,
            V3_ServiceType,
            V3_HelpsWith,
            V3_WhoFor,
            V3_WhoNotFor,
            V3_Mitigations,
            V3_TimeRequired,
            V3_Access,
            V3_Costs,
            V3_Taxonomy,
            V3_Category,
            # Core entities
            V3_Contact,
            V3_Location,
            V3_Service,
            # Through tables
            V3_Service_Category,
            V3_Service_HelpsWith,
            V3_Service_WhoFor,
            V3_Service_WhoNotFor,
            V3_Service_Mitigation,
            V3_Service_TimeRequired,
            V3_Service_Access,
            V3_Service_Cost,
            V3_Service_Taxonomy,
            V3_Service_Contact,
            V3_Service_Location,
        ]

        all_objects = []
        for model_cls in model_order:
            all_objects.extend(model_cls.objects.all().order_by("id"))

        data = serializers.serialize("json", all_objects)

        # Return as downloadable JSON
        response = HttpResponse(data, content_type="application/json")
        response["Content-Disposition"] = 'attachment; filename="v3_seed.json"'
        return response

    # Hook the view into this AdminSite's URLconf
    original_get_urls = site.get_urls

    def get_urls():
        urls = original_get_urls()
        custom = [
            path(
                "export-v3-data/",
                site.admin_view(export_v3_data_view),
                name="v3_export_data",
            ),
        ]
        return custom + urls

    site.get_urls = get_urls

    # Override index() to redirect to the service changelist
    original_index = site.index

    def index(request, extra_context=None):
        try:
            url = reverse(f"{site.name}:api_v3_service_changelist")
            return HttpResponseRedirect(url)
        except Exception:
            return original_index(request, extra_context=extra_context)

    site.index = index

    # Tweak app list so that services appear first under 'api', and hide
    # contacts/locations from the left-hand list.
    original_get_app_list = site.get_app_list

    def get_app_list(request, app_label=None):
        # Call the original with the same signature Django expects
        app_list = original_get_app_list(request, app_label=app_label)

        for app in app_list:
            if app.get("app_label") == "api":
                # Remove V3_Contact and V3_Location from the visible model list
                app["models"] = [
                    m for m in app["models"]
                    if m.get("object_name") not in {"V3_Contact", "V3_Location"}
                ]

                def sort_key(model_dict):
                    if model_dict.get("object_name") == "V3_Service":
                        return (0, "")
                    return (1, model_dict.get("name", "").lower())

                app["models"].sort(key=sort_key)

        return app_list

    site.get_app_list = get_app_list

    # Models that should never appear as top-level entries
    through_models = {
        V3_Service_Category,
        V3_Service_HelpsWith,
        V3_Service_WhoFor,
        V3_Service_WhoNotFor,
        V3_Service_Mitigation,
        V3_Service_TimeRequired,
        V3_Service_Access,
        V3_Service_Cost,
        V3_Service_Taxonomy,
        V3_Service_Contact,
        V3_Service_Location,
    }

    # Register the core service + lookup tables with specialised admins
    site.register(V3_Service, V3_ServiceAdmin)
    site.register(V3_Access, V3_AccessAdmin)
    site.register(V3_ActionType, V3_ActionTypeAdmin)
    site.register(V3_Category, V3_CategoryAdmin)
    site.register(V3_Costs, V3_CostsAdmin)
    site.register(V3_HelpsWith, V3_HelpsWithAdmin)
    site.register(V3_Mitigations, V3_MitigationsAdmin)
    site.register(V3_ServiceType, V3_ServiceTypeAdmin)
    site.register(V3_Taxonomy, V3_TaxonomyAdmin)
    site.register(V3_TimeRequired, V3_TimeRequiredAdmin)
    site.register(V3_WhoFor, V3_WhoForAdmin)
    site.register(V3_WhoNotFor, V3_WhoNotForAdmin)

    # Register contacts and locations with the generic admin so that
    # inline add/edit works (but they won't show in the sidebar).
    site.register(V3_Contact, generic_admin_cls)
    site.register(V3_Location, V3_LocationAdmin)

    handled = {
        V3_Service,
        V3_Access,
        V3_ActionType,
        V3_Category,
        V3_Costs,
        V3_HelpsWith,
        V3_Mitigations,
        V3_ServiceType,
        V3_Taxonomy,
        V3_TimeRequired,
        V3_WhoFor,
        V3_WhoNotFor,
        V3_Contact,
        V3_Location,
    } | through_models

    # Any remaining V3 models get the generic admin treatment
    for model in models:
        if model in handled:
            continue
        try:
            site.register(model, generic_admin_cls)
        except admin.sites.AlreadyRegistered:
            pass
