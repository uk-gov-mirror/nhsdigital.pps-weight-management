# pilot_access/admin.py
from __future__ import annotations

from django.contrib import admin

from .models import PilotProfile, UserFilter, MagicLink, Campaign


@admin.register(PilotProfile)
class PilotProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "email", "phone", "campaign", "created_at", "disclaimer_accepted_at")
    search_fields = ("user__username", "email", "phone")
    list_filter = ("campaign", "preferred_contact_method")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


@admin.register(UserFilter)
class UserFilterAdmin(admin.ModelAdmin):
    list_display = ("user", "updated_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")


@admin.register(MagicLink)
class MagicLinkAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at", "used_at")
    search_fields = ("user__username", "user__email", "token_hash")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "used_at", "token_hash")


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("campaign_code", "valid_from", "valid_to", "comment_preview", "is_active", "created_at")
    list_filter = ("valid_from", "valid_to")
    search_fields = ("campaign_code", "comment")
    ordering = ("-created_at",)
    readonly_fields = ("campaign_code", "created_at", "updated_at")
    
    fieldsets = (
        (None, {
            'fields': ('campaign_code',)
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_to')
        }),
        ('Details', {
            'fields': ('comment',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def comment_preview(self, obj):
        """Show first 50 characters of comment."""
        if obj.comment:
            return obj.comment[:50] + ('...' if len(obj.comment) > 50 else '')
        return ''
    comment_preview.short_description = 'Comment'

    def is_active(self, obj):
        """Show if campaign is currently active."""
        return obj.is_valid_today()
    is_active.boolean = True
    is_active.short_description = 'Active Now'
