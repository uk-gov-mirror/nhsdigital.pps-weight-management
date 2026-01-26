from django import forms
from django.core.exceptions import ValidationError

from .models import PilotProfile


class DisclaimerForm(forms.Form):
    """Form for accepting the disclaimer to use personal information."""

    disclaimer_accepted = forms.CharField(
        required=True,
        widget=forms.RadioSelect(
            choices=[
                ("accepted", "Yes, that's OK"),
                ("not-accepted", "No, I don't want to continue"),
            ]
        ),
        label="We'll need your contact details and postcode. Is that OK?",
    )


class ReturningForm(forms.Form):
    """Form for checking if user is a returning user."""

    returning = forms.CharField(
        required=True,
        widget=forms.RadioSelect(
            choices=[
                ("first-time", "First time"),
                ("returning", "I've used it before"),
            ]
        ),
        label="Is this your first time using 'NHS Help to stay healthy'?",
    )

class CampaignContactTypeForm(forms.Form):
    """Form for selecting preferred contact method during campaign signup."""

    CONTACT_EMAIL = "email"
    CONTACT_SMS = "sms"

    CONTACT_CHOICES = (
        ("", "Select an option"),
        (CONTACT_EMAIL, "Email"),
        (CONTACT_SMS, "Text message (SMS)"),
    )

    preferred_contact_method = forms.ChoiceField(
        label="How would you like us to contact you?",
        choices=CONTACT_CHOICES,
        widget=forms.RadioSelect,
        required=True,
    )

class EmailInputForm(forms.Form):
    """Form for collecting email input."""

    email = forms.EmailField(
        label="Email address",
        required=True,
    )

    def clean(self):
        cleaned = super().clean()
        email = (cleaned.get("email") or "").strip().lower()

        # Validate email uniqueness in PilotProfile
        if email:
            if PilotProfile.objects.filter(email__iexact=email).exists():
                self.add_error("email", "That email address is already registered.")
        cleaned["email"] = email
        return cleaned


class PhoneInputForm(forms.Form):
    """Form for collecting contact details during campaign signup."""

    phone = forms.CharField(
        label="Mobile number",
        max_length=32,
        required=True,
    )

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            return ""

        # Remove common formatting characters
        import re

        normalized = re.sub(r"[\s\-\(\)]+", "", phone)

        # Basic validation: should be digits, optionally starting with +
        if not re.match(r"^\+?[0-9]{10,15}$", normalized):
            raise ValidationError("Please enter a valid mobile number.")

        return normalized

    def clean(self):
        cleaned = super().clean()
        phone = cleaned.get("phone") or ""  # Already cleaned by clean_phone

        # Validate phone uniqueness in PilotProfile
        if phone:
            if PilotProfile.objects.filter(phone=phone).exists():
                self.add_error("phone", "That mobile number is already registered.")
                
        cleaned["phone"] = phone
        return cleaned


class OTPForm(forms.Form):
    """Form for entering OTP code."""

    otp = forms.CharField(
        label="Enter the 6-digit code",
        max_length=6,
        min_length=6,
        required=True,
    )

    def clean_otp(self):
        otp = self.cleaned_data.get("otp", "").strip()
        if not otp.isdigit():
            raise ValidationError("Please enter a valid 6-digit code.")
        if len(otp) != 6:
            raise ValidationError("Please enter a valid 6-digit code.")
        return otp


class LoginRequestForm(forms.Form):
    """Form for requesting OTP login - accepts email or phone."""

    contact = forms.CharField(
        label="Email address or mobile number",
        required=True,
    )

    def clean_contact(self):
        contact = (self.cleaned_data.get("contact") or "").strip()
        if not contact:
            raise ValidationError("Enter your email address or mobile number.")
        return contact


class PilotAccountForm(forms.Form):
    CONTACT_EMAIL = "email"
    CONTACT_SMS = "sms"

    CONTACT_CHOICES = (
        (CONTACT_EMAIL, "Email"),
        (CONTACT_SMS, "Text message (SMS)"),
    )

    email = forms.EmailField(label="Email address", required=False)
    phone = forms.CharField(label="Mobile number", max_length=32, required=False)
    postcode = forms.CharField(
        label="Postcode",
        max_length=16,
        required=True,
        help_text="For example, SW1A 1AA",
    )

    preferred_contact_method = forms.ChoiceField(
        label="Preferred contact method",
        choices=CONTACT_CHOICES,
        widget=forms.RadioSelect,
        required=True,
    )

    def __init__(self, *, user, profile: PilotProfile, data=None):
        self.user = user
        self.profile = profile

        initial = {
            "email": getattr(profile, "email", "") or user.email or "",
            "phone": getattr(profile, "phone", "") or "",
            "postcode": getattr(profile, "postcode", "") or "",
            "preferred_contact_method": getattr(profile, "preferred_contact_method", "")
            or "",
        }

        if not initial["preferred_contact_method"]:
            if initial["phone"] and not initial["email"]:
                initial["preferred_contact_method"] = self.CONTACT_SMS
            else:
                initial["preferred_contact_method"] = self.CONTACT_EMAIL

        super().__init__(data=data, initial=initial)

    def clean(self):
        cleaned = super().clean()
        email = (cleaned.get("email") or "").strip()
        phone = (cleaned.get("phone") or "").strip()
        pref = cleaned.get("preferred_contact_method") or ""
        postcode = (cleaned.get("postcode") or "").strip().upper()

        if not postcode:
            self.add_error("postcode", "Enter a postcode.")
        else:
            import re as _re

            _pc_re = _re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$", _re.I)
            if not _pc_re.match(postcode):
                self.add_error("postcode", "Enter a valid UK postcode.")
            else:
                postcode = postcode.replace(" ", "")
                postcode = postcode[:-3] + " " + postcode[-3:]

        if pref == self.CONTACT_EMAIL:
            if not email:
                self.add_error(
                    "email",
                    "Enter an email address if email is your preferred contact method.",
                )
        elif pref == self.CONTACT_SMS:
            if not phone:
                self.add_error(
                    "phone",
                    "Enter a mobile number if text message is your preferred contact method.",
                )

        if not email and not phone:
            raise forms.ValidationError("Enter an email address or a mobile number.")

        cleaned["email"] = email.lower() if email else ""
        cleaned["phone"] = phone or ""
        cleaned["postcode"] = postcode
        return cleaned

    def clean_email(self) -> str:
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            return ""

        # Check uniqueness in PilotProfile
        if (
            PilotProfile.objects.filter(email__iexact=email)
            .exclude(pk=self.profile.pk)
            .exists()
        ):
            raise ValidationError("That email address is already in use.")

        return email

    def clean_phone(self) -> str:
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            return ""

        if (
            PilotProfile.objects.filter(phone=phone)
            .exclude(pk=self.profile.pk)
            .exists()
        ):
            raise ValidationError("That mobile number is already in use.")

        return phone

    def save(self) -> None:
        email = self.cleaned_data["email"]
        phone = self.cleaned_data["phone"]
        pref = self.cleaned_data["preferred_contact_method"]

        self.profile.email = email
        self.profile.phone = phone
        self.profile.postcode = self.cleaned_data.get("postcode", "")
        self.profile.preferred_contact_method = pref
        self.profile.save(
            update_fields=["email", "phone", "postcode", "preferred_contact_method"]
        )


class DeleteAccountForm(forms.Form):
    confirm = forms.BooleanField(
        required=True,
        label="Yes, delete my account",
    )


class CheckReturningUserForm(forms.Form):
    returning = forms.ChoiceField(
        label="Are you a returning user?",
        choices=(
            ("yes", "First Time"),
            ("no", "I've used it before"),
        ),
        widget=forms.RadioSelect,
        required=True,
    )
