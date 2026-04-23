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
        db_table = "campaign"


class UserProfile(models.Model):
    CONTACT_EMAIL = "email"
    CONTACT_SMS = "sms"

    CONTACT_METHOD_CHOICES = [
        (CONTACT_EMAIL, "Email"),
        (CONTACT_SMS, "SMS"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
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

    class Meta:
        db_table = "profile"

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

    class Meta:
        db_table = "magiclink"

    def is_valid(self) -> bool:
        return self.used_at is None and timezone.now() < self.expires_at


class UserFilter(models.Model):
    """Persisted copy of a user's wizard answers / listing filters."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_filter",
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

    class Meta:
        db_table = "userfilter"

    def get_value(self, key: str, default=None):
        return (self.data or {}).get(key, default)


# ──────────────────────────────────────────────────────────────────────
# Questionnaire Response — behavioural tag mapping from spreadsheet
# ──────────────────────────────────────────────────────────────────────

RESPONSE_TAG_MAPPING: dict[str, dict] = {
    # Q1 — Motivation (single-select)
    "motivation.want_to_feel_better": {
        "com_b": [],
        "hbm": [],
        "sdt": ["Intrinsic Motivation"],
        "activity_attributes": ["Goal", "Type of activity"],
    },
    "motivation.noticed_changes": {
        "com_b": [],
        "hbm": ["Perceived Susceptibility"],
        "sdt": [],
        "activity_attributes": ["Goal"],
    },
    "motivation.health_professional": {
        "com_b": [],
        "hbm": ["Cue to Action"],
        "sdt": [],
        "activity_attributes": ["Health-tailored options", "Goal"],
    },
    "motivation.social_encouragement": {
        "com_b": [],
        "hbm": [],
        "sdt": ["Extrinsic Motivation", "Relatedness"],
        "activity_attributes": ["Social setting"],
    },
    "motivation.health_scare": {
        "com_b": [],
        "hbm": ["Cue to Action", "Perceived Severity"],
        "sdt": [],
        "activity_attributes": ["Health-tailored options", "Accessible options"],
    },
    "motivation.setting_example": {
        "com_b": [],
        "hbm": [],
        "sdt": ["Extrinsic Motivation"],
        "activity_attributes": ["Social setting", "Type of activity"],
    },
    "motivation.tried_before": {
        "com_b": [],
        "hbm": [],
        "sdt": ["Autonomous Motivation"],
        "activity_attributes": ["Beginner-suitable", "Goal"],
    },
    "motivation.life_transition": {
        "com_b": [],
        "hbm": [],
        "sdt": ["Autonomous Motivation"],
        "activity_attributes": ["Type of activity", "Duration / commitment"],
    },
    "motivation.just_exploring": {
        "com_b": [],
        "hbm": [],
        "sdt": ["Amotivation"],
        "activity_attributes": ["Beginner-suitable", "Goal"],
    },
    # Q2 — Priority behaviour (single-select)
    "priority_behaviour.more_physically_active": {
        "com_b": [],
        "hbm": [],
        "sdt": ["Autonomous Motivation"],
        "activity_attributes": ["Type of activity", "Level of intensity"],
    },
    "priority_behaviour.eating_drinking": {
        "com_b": [],
        "hbm": ["Perceived Benefit"],
        "sdt": [],
        "activity_attributes": ["Nutritional support"],
    },
    "priority_behaviour.managing_weight": {
        "com_b": [],
        "hbm": ["Perceived Benefit"],
        "sdt": ["Autonomous Motivation"],
        "activity_attributes": ["Goal", "Nutritional support"],
    },
    "priority_behaviour.mental_wellbeing": {
        "com_b": [],
        "hbm": [],
        "sdt": ["Intrinsic Motivation"],
        "activity_attributes": ["Type of activity", "Goal"],
    },
    "priority_behaviour.energy_stamina": {
        "com_b": [],
        "hbm": [],
        "sdt": ["Intrinsic Motivation"],
        "activity_attributes": ["Level of intensity", "Type of activity"],
    },
    "priority_behaviour.managing_condition": {
        "com_b": [],
        "hbm": ["Perceived Susceptibility"],
        "sdt": [],
        "activity_attributes": ["Health-tailored options", "Accessible options"],
    },
    "priority_behaviour.body_confidence": {
        "com_b": [],
        "hbm": [],
        "sdt": ["Intrinsic Motivation"],
        "activity_attributes": ["Social setting", "Gender appropriate", "Beginner-suitable"],
    },
    # Q3 — Past barriers (multi-select)
    "past_barriers.no_time": {
        "com_b": ["Physical Opportunity"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Duration / commitment"],
    },
    "past_barriers.too_expensive": {
        "com_b": ["Physical Opportunity"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Cost"],
    },
    "past_barriers.not_physically_able": {
        "com_b": ["Physical Capability"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Health-tailored options", "Accessible options", "Beginner-suitable"],
    },
    "past_barriers.didnt_know_where_to_start": {
        "com_b": ["Psychological Capability"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Beginner-suitable", "Goal"],
    },
    "past_barriers.lost_motivation": {
        "com_b": ["Reflective Motivation"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Social setting", "Goal"],
    },
    "past_barriers.no_one_to_do_it_with": {
        "com_b": ["Social Opportunity"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Social setting"],
    },
    "past_barriers.nothing_nearby": {
        "com_b": ["Physical Opportunity"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Location", "Distance", "Online vs in-person"],
    },
    "past_barriers.life_pressures": {
        "com_b": ["Physical Opportunity"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Duration / commitment", "Online vs in-person"],
    },
    "past_barriers.lack_of_confidence": {
        "com_b": ["Psychological Capability"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Beginner-suitable", "Social setting"],
    },
    # Q4 — Current barriers (multi-select)
    "current_barriers.short_on_time": {
        "com_b": ["Physical Opportunity"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Duration / commitment"],
    },
    "current_barriers.cant_afford_it": {
        "com_b": ["Physical Opportunity"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Cost"],
    },
    "current_barriers.health_condition": {
        "com_b": ["Physical Capability"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Health-tailored options", "Accessible options", "Level of intensity"],
    },
    "current_barriers.not_sure_what_works": {
        "com_b": ["Psychological Capability"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Goal", "Beginner-suitable"],
    },
    "current_barriers.low_motivation": {
        "com_b": ["Reflective Motivation"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Goal", "Social setting"],
    },
    "current_barriers.self_conscious": {
        "com_b": ["Psychological Capability"],
        "hbm": ["Perceived Barriers"],
        "sdt": [],
        "activity_attributes": ["Social setting", "Gender appropriate", "Beginner-suitable"],
    },
    "current_barriers.practical_barriers": {
        "com_b": ["Physical Opportunity"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Location", "Distance", "Online vs in-person"],
    },
    "current_barriers.routine": {
        "com_b": ["Psychological Capability"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Duration / commitment", "Type of activity"],
    },
    "current_barriers.low_perceived_need": {
        "com_b": [],
        "hbm": ["Perceived Susceptibility"],
        "sdt": [],
        "activity_attributes": ["Goal framing"],
    },
    # Q5 — Confidence & readiness (single-select)
    "confidence_readiness.ready_and_confident": {
        "com_b": ["Psychological Capability"],
        "hbm": [],
        "sdt": ["Competence"],
        "activity_attributes": ["Full range — optimise for preference match"],
    },
    "confidence_readiness.keen_but_worried": {
        "com_b": ["Reflective Motivation"],
        "hbm": [],
        "sdt": ["Competence"],
        "activity_attributes": ["Social setting", "Duration / commitment", "Goal"],
    },
    "confidence_readiness.want_to_but_barriers": {
        "com_b": ["Psychological Capability"],
        "hbm": ["Perceived Barriers"],
        "sdt": [],
        "activity_attributes": ["Online vs in-person", "Cost", "Accessible options"],
    },
    "confidence_readiness.not_quite_ready": {
        "com_b": ["Reflective Motivation"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Beginner-suitable", "Duration / commitment"],
    },
    "confidence_readiness.change_out_of_reach": {
        "com_b": ["Psychological Capability"],
        "hbm": [],
        "sdt": ["Competence"],
        "activity_attributes": ["Health-tailored options", "Beginner-suitable", "Level of intensity"],
    },
    # Q6 — Enablers (multi-select)
    "enablers.wont_take_too_much_time": {
        "com_b": ["Physical Opportunity"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Duration / commitment"],
    },
    "enablers.affordable": {
        "com_b": ["Physical Opportunity"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Cost"],
    },
    "enablers.support_from_others": {
        "com_b": [],
        "hbm": [],
        "sdt": ["Relatedness"],
        "activity_attributes": ["Social setting"],
    },
    "enablers.start_slowly": {
        "com_b": ["Physical Capability"],
        "hbm": [],
        "sdt": ["Competence"],
        "activity_attributes": ["Beginner-suitable", "Level of intensity"],
    },
    "enablers.suitable_for_me": {
        "com_b": [],
        "hbm": ["Perceived Barriers"],
        "sdt": ["Competence"],
        "activity_attributes": ["Health-tailored options", "Accessible options", "Gender appropriate"],
    },
    "enablers.home_online": {
        "com_b": ["Physical Opportunity"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Online vs in-person", "Location"],
    },
    "enablers.clear_guidance": {
        "com_b": ["Psychological Capability"],
        "hbm": [],
        "sdt": [],
        "activity_attributes": ["Beginner-suitable", "Facilities"],
    },
    "enablers.will_make_a_difference": {
        "com_b": [],
        "hbm": ["Perceived Benefit"],
        "sdt": [],
        "activity_attributes": ["Goal"],
    },
}

# Distinct activity attribute vocabulary derived from RESPONSE_TAG_MAPPING
ACTIVITY_ATTRIBUTE_CHOICES = sorted(set(
    attr
    for mapping in RESPONSE_TAG_MAPPING.values()
    for attr in mapping.get("activity_attributes", [])
))

# Question-level metadata for validation and display
QUESTIONNAIRE_QUESTIONS: dict[str, dict] = {
    "motivation": {
        "number": "Q1",
        "label": "Motivation",
        "text": "What prompted you to look for support with your health today?",
        "type": "single",
    },
    "priority_behaviour": {
        "number": "Q2",
        "label": "Priority behaviour",
        "text": "Which of the following would make the biggest difference to your health and wellbeing right now?",
        "type": "single",
    },
    "past_barriers": {
        "number": "Q3",
        "label": "Past barriers",
        "text": "Looking back, what has made it difficult for you to keep up healthy habits?",
        "type": "multi",
    },
    "current_barriers": {
        "number": "Q4",
        "label": "Current barriers",
        "text": "What is making it hardest for you to build healthy habits right now?",
        "type": "multi",
    },
    "confidence_readiness": {
        "number": "Q5",
        "label": "Confidence & readiness",
        "text": "How do you feel about making a change to your health habits right now?",
        "type": "single",
    },
    "enablers": {
        "number": "Q6",
        "label": "Enablers",
        "text": "What would make it easier for you to take that first step?",
        "type": "multi",
    },
}


class QuestionnaireResponse(models.Model):
    """Stores a user's behavioural questionnaire answers with model tags and derived attributes."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="questionnaire_response",
    )

    # Per-question answers — single-select: string, multi-select: list of strings
    motivation = models.CharField(max_length=255, blank=True, default="")  # Q1
    priority_behaviour = models.CharField(max_length=255, blank=True, default="")  # Q2
    past_barriers = models.JSONField(default=list, blank=True)  # Q3 multi-select
    current_barriers = models.JSONField(default=list, blank=True)  # Q4 multi-select
    confidence_readiness = models.CharField(max_length=255, blank=True, default="")  # Q5
    enablers = models.JSONField(default=list, blank=True)  # Q6 multi-select

    # Behavioural model tags derived from answers (computed on save)
    behavioural_tags = models.JSONField(default=dict, blank=True)
    # Structure: {"com_b": [...], "hbm": [...], "sdt": [...]}

    # Activity attributes derived from responses for Phase 11 service matching
    activity_attributes = models.JSONField(default=list, blank=True)
    # Structure: ["attr1", "attr2", ...]

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "questionnaire_response"

    def __str__(self):
        return f"QuestionnaireResponse for {self.user}"

    def set_answer(self, question_key: str, value):
        """Set an answer for a question field."""
        setattr(self, question_key, value)

    def get_answer(self, question_key: str, default=None):
        """Get an answer for a question field."""
        return getattr(self, question_key, default)

    def derive_behavioural_tags(self):
        """Compute COM-B, HBM, SDT tags from all answers using the spreadsheet mapping."""
        tags: dict[str, list[str]] = {"com_b": [], "hbm": [], "sdt": []}
        all_values: list[str] = []

        if self.motivation:
            all_values.append(self.motivation)
        if self.priority_behaviour:
            all_values.append(self.priority_behaviour)
        if self.past_barriers:
            all_values.extend(self.past_barriers)
        if self.current_barriers:
            all_values.extend(self.current_barriers)
        if self.confidence_readiness:
            all_values.append(self.confidence_readiness)
        if self.enablers:
            all_values.extend(self.enablers)

        for val in all_values:
            mapping = RESPONSE_TAG_MAPPING.get(val, {})
            for tag in mapping.get("com_b", []):
                if tag not in tags["com_b"]:
                    tags["com_b"].append(tag)
            for tag in mapping.get("hbm", []):
                if tag not in tags["hbm"]:
                    tags["hbm"].append(tag)
            for tag in mapping.get("sdt", []):
                if tag not in tags["sdt"]:
                    tags["sdt"].append(tag)

        self.behavioural_tags = tags

    def derive_activity_attributes(self):
        """Compute activity attributes from responses using the spreadsheet mapping."""
        attrs: list[str] = []
        all_values: list[str] = []

        if self.motivation:
            all_values.append(self.motivation)
        if self.priority_behaviour:
            all_values.append(self.priority_behaviour)
        if self.past_barriers:
            all_values.extend(self.past_barriers)
        if self.current_barriers:
            all_values.extend(self.current_barriers)
        if self.confidence_readiness:
            all_values.append(self.confidence_readiness)
        if self.enablers:
            all_values.extend(self.enablers)

        for val in all_values:
            mapping = RESPONSE_TAG_MAPPING.get(val, {})
            for attr in mapping.get("activity_attributes", []):
                if attr not in attrs:
                    attrs.append(attr)

        self.activity_attributes = attrs


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
        db_table = "favouriteservice"

    def __str__(self):
        return f"User {self.user_id} ♥ Service {self.service_id}"


class ActivityAttribute(models.Model):
    """Activity attribute vocabulary for service matching (e.g., 'Cost', 'Social setting')."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "activity_attribute"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ServiceActivityAttribute(models.Model):
    """Links a V3_Service to an ActivityAttribute for relevance matching."""

    service_id = models.PositiveIntegerField(
        help_text="V3_Service.id — not a FK because the service table is unmanaged",
        db_index=True,
    )
    attribute = models.ForeignKey(
        ActivityAttribute,
        on_delete=models.CASCADE,
        related_name="service_links",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("service_id", "attribute")
        db_table = "service_activity_attribute"
        ordering = ["service_id", "attribute__name"]

    def __str__(self):
        return f"Service {self.service_id} — {self.attribute.name}"
