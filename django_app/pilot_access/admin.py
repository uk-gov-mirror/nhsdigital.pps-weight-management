# pilot_access/admin.py
from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone

from .models import InviteRequest, Invitation, PilotProfile
from .services.sender import get_email_sender, get_sms_sender
from .services.tokens import generate_token, hash_token


def _invite_expiry() -> timedelta:
    days = getattr(settings, "PILOT_ACCESS_INVITE_EXPIRY_DAYS", 7)
    return timedelta(days=days)


@admin.register(InviteRequest)
class InviteRequestAdmin(admin.ModelAdmin):
    list_display = ("email", "phone", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("email", "phone")
    ordering = ("-created_at",)
    actions = ("approve_and_send_invitations",)

    @admin.action(description="Approve selected requests and send invitations (email + SMS)")
    def approve_and_send_invitations(self, request, queryset):
        email_sender = get_email_sender()
        sms_sender = get_sms_sender()

        approved = 0
        skipped = 0
        now = timezone.now()

        with transaction.atomic():
            for invite_request in queryset.select_for_update():
                if invite_request.status != InviteRequest.STATUS_PENDING:
                    skipped += 1
                    continue

                raw_token = generate_token()
                invitation = Invitation.objects.create(
                    email=invite_request.email,
                    phone=invite_request.phone,
                    expires_at=now + _invite_expiry(),
                    token_hash=hash_token(raw_token),
                )

                invite_request.status = InviteRequest.STATUS_APPROVED
                invite_request.save(update_fields=["status"])

                # Send the *raw* token to the user (not the hash)
                email_sender.send_invite(email=invitation.email, link_or_code=raw_token)

                if invitation.phone:
                    sms_sender.send_invite(phone=invitation.phone, link_or_code=raw_token)

                approved += 1

        if approved:
            self.message_user(request, f"Approved + invited: {approved}", level=messages.SUCCESS)
        if skipped:
            self.message_user(request, f"Skipped (not pending): {skipped}", level=messages.WARNING)


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "phone", "created_at", "expires_at", "used_at")
    search_fields = ("email", "phone", "token_hash")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "used_at", "token_hash")


@admin.register(PilotProfile)
class PilotProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "invited_at", "disclaimer_accepted_at")
    search_fields = ("user__username", "user__email")
    ordering = ("-invited_at",)
