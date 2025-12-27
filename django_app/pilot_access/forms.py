from django import forms


class InviteRequestForm(forms.Form):
    email = forms.EmailField(
        required=False,
        label="Email address",
    )
    phone = forms.CharField(
        required=False,
        label="Mobile number",
        help_text="Include spaces if you like; we’ll store it as entered for now.",
    )

    def clean(self):
        cleaned = super().clean()
        email = (cleaned.get("email") or "").strip()
        phone = (cleaned.get("phone") or "").strip()

        if not email and not phone:
            raise forms.ValidationError("Enter an email address or a mobile number.")

        cleaned["email"] = email or None
        cleaned["phone"] = phone or None
        return cleaned

class DisclaimerForm(forms.Form):
    accept = forms.BooleanField(
        required=True,
        label="I have read and agree to the beta disclaimer.",
    )

class MagicLinkRequestForm(forms.Form):
    email = forms.EmailField()    