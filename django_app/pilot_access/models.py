from django.conf import settings
from django.db import models
from django.utils import timezone

class InviteRequest(models.Model):
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    status = models.CharField(
        max_length=16,
        choices=[
            (STATUS_PENDING, "Pending"),
            (STATUS_APPROVED, "Approved"),
            (STATUS_REJECTED, "Rejected"),
        ],
        default=STATUS_PENDING,
    )

    def __str__(self):
        return f"{self.email} ({self.status})"


class Invitation(models.Model):
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)

    token_hash = models.CharField(max_length=128, unique=True)

    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    def is_valid(self):
        return self.used_at is None and timezone.now() < self.expires_at

    def __str__(self):
        return self.email


class PilotProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pilot_profile",
    )
    invited_at = models.DateTimeField()
    disclaimer_accepted_at = models.DateTimeField(null=True, blank=True)

    def has_accepted_disclaimer(self):
        return self.disclaimer_accepted_at is not None

    def __str__(self):
        return self.user.get_username()

class MagicLink(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token_hash = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    def is_valid(self) -> bool:
        return self.used_at is None and timezone.now() < self.expires_at