from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import random
import string


def generate_campaign_code():
    """Generate a unique 6-digit campaign code."""
    while True:
        code = ''.join(random.choices(string.digits, k=6))
        if not Campaign.objects.filter(campaign_code=code).exists():
            return code


def generate_username():
    """Generate a unique 10-character alphanumeric username."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    while True:
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        if not User.objects.filter(username=username).exists():
            return username


class Campaign(models.Model):
    """
    Campaign model for managing invitation campaigns with validity periods.
    """
    campaign_code = models.CharField(
        max_length=6,
        unique=True,
        editable=False,
        help_text="Auto-generated 6-digit unique campaign code"
    )
    valid_from = models.DateField(
        help_text="Campaign start date (inclusive)"
    )
    valid_to = models.DateField(
        help_text="Campaign end date (inclusive)"
    )
    comment = models.TextField(
        help_text="Campaign description/comment (displayed to users)"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        """Validate that valid_from is at least 1 day before valid_to."""
        super().clean()
        if self.valid_from and self.valid_to:
            if self.valid_from >= self.valid_to:
                raise ValidationError({
                    'valid_to': 'Valid to date must be at least 1 day after valid from date.'
                })
            if (self.valid_to - self.valid_from).days < 1:
                raise ValidationError({
                    'valid_to': 'Valid to date must be at least 1 day after valid from date.'
                })

    def save(self, *args, **kwargs):
        if not self.campaign_code:
            self.campaign_code = generate_campaign_code()
        self.full_clean()
        super().save(*args, **kwargs)

    def is_valid_today(self):
        """Check if the campaign is valid for today's date."""
        today = timezone.now().date()
        return self.valid_from <= today <= self.valid_to

    def __str__(self):
        return f"Campaign {self.campaign_code} ({self.valid_from} to {self.valid_to})"

    class Meta:
        ordering = ['-created_at']


class PilotProfile(models.Model):
    CONTACT_EMAIL = "email"
    CONTACT_SMS = "sms"

    CONTACT_METHOD_CHOICES = [
        (CONTACT_EMAIL, "Email"),
        (CONTACT_SMS, "SMS"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pilot_profile",
    )
    
    # Link to the campaign the user signed up through
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.PROTECT,
        related_name="profiles",
        to_field="campaign_code",
        null=True,  # Allow null for existing records migrated before campaigns existed
        blank=True,
    )
    
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=32, blank=True, default="")
    postcode = models.CharField(max_length=16, blank=True, default="")

    preferred_contact_method = models.CharField(
        max_length=8,
        choices=CONTACT_METHOD_CHOICES,
        default=CONTACT_EMAIL,
    )

    created_at = models.DateTimeField(default=timezone.now)
    disclaimer_accepted_at = models.DateTimeField(null=True, blank=True)

    def has_accepted_disclaimer(self):
        return self.disclaimer_accepted_at is not None

    def __str__(self):
        return self.user.get_username()


class MagicLink(models.Model):
    """
    Used for OTP verification. The token_hash stores the hashed OTP code.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token_hash = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    def is_valid(self) -> bool:
        return self.used_at is None and timezone.now() < self.expires_at


class UserFilter(models.Model):
    """Persisted copy of a user's wizard answers / listing filters."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pilot_filter",
    )

    data = models.JSONField(default=dict, blank=True)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(default=timezone.now)

    def set_value(self, key: str, value):
        d = dict(self.data or {})
        if value in (None, "", [], {}):
            d.pop(key, None)
        else:
            d[key] = value
        self.data = d

    def get_value(self, key: str, default=None):
        return (self.data or {}).get(key, default)


class FavouriteService(models.Model):
    """A user's favourited service. service_id references V3_Service.id (unmanaged)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favourite_services",
    )
    service_id = models.PositiveIntegerField(
        help_text="V3_Service.id — not a FK because the service table is unmanaged"
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "service_id")
        ordering = ["-created_at"]

    def __str__(self):
        return f"User {self.user_id} ♥ Service {self.service_id}"
