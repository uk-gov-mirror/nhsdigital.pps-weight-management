from __future__ import annotations

import time
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .forms import DisclaimerForm, CampaignContactForm, OTPForm
from .forms import LoginRequestForm, PilotAccountForm, DeleteAccountForm
from .models import PilotProfile, MagicLink, UserFilter, Campaign, generate_username

from .services.tokens import generate_otp, hash_token
from .services.sender import get_email_sender, get_sms_sender

User = get_user_model()

# Rate limiting constants
OTP_GENERATION_LIMIT = 3  # Max OTP requests per contact per hour
OTP_GENERATION_WINDOW = 60 * 60  # 1 hour in seconds
OTP_ATTEMPT_LIMIT = 5  # Max verification attempts per user
OTP_ATTEMPT_WINDOW = 60 * 15  # 15 minutes in seconds
OTP_LOCKOUT_DURATION = 60 * 30  # 30 minute lockout after too many failures

# Minimum response time to prevent timing attacks (in seconds)
MIN_RESPONSE_TIME = 0.5


def _rate_limit_key_otp_generation(contact: str) -> str:
    """Cache key for OTP generation rate limiting."""
    return f"pilot_access:otp_gen:{contact.lower()}"


def _rate_limit_key_otp_attempts(user_id: int) -> str:
    """Cache key for OTP verification attempt rate limiting."""
    return f"pilot_access:otp_attempts:{user_id}"


def _rate_limit_key_otp_lockout(user_id: int) -> str:
    """Cache key for OTP lockout."""
    return f"pilot_access:otp_lockout:{user_id}"


def _check_otp_generation_rate_limit(contact: str) -> bool:
    """
    Check if OTP generation is rate limited for this contact.
    Returns True if rate limited (should block), False if OK to proceed.
    """
    key = _rate_limit_key_otp_generation(contact)
    count = cache.get(key, 0)
    return count >= OTP_GENERATION_LIMIT


def _increment_otp_generation_count(contact: str) -> None:
    """Increment the OTP generation count for this contact."""
    key = _rate_limit_key_otp_generation(contact)
    count = cache.get(key, 0)
    cache.set(key, count + 1, timeout=OTP_GENERATION_WINDOW)


def _check_otp_attempt_lockout(user_id: int) -> bool:
    """
    Check if user is locked out from OTP attempts.
    Returns True if locked out, False if OK to proceed.
    """
    lockout_key = _rate_limit_key_otp_lockout(user_id)
    return cache.get(lockout_key) is not None


def _get_otp_attempt_count(user_id: int) -> int:
    """Get current OTP attempt count for user."""
    key = _rate_limit_key_otp_attempts(user_id)
    return cache.get(key, 0)


def _increment_otp_attempt_count(user_id: int) -> int:
    """
    Increment OTP attempt count and return new count.
    If limit exceeded, set lockout.
    """
    key = _rate_limit_key_otp_attempts(user_id)
    count = cache.get(key, 0) + 1
    cache.set(key, count, timeout=OTP_ATTEMPT_WINDOW)
    
    if count >= OTP_ATTEMPT_LIMIT:
        lockout_key = _rate_limit_key_otp_lockout(user_id)
        cache.set(lockout_key, True, timeout=OTP_LOCKOUT_DURATION)
    
    return count


def _clear_otp_attempt_count(user_id: int) -> None:
    """Clear OTP attempt count after successful verification."""
    key = _rate_limit_key_otp_attempts(user_id)
    lockout_key = _rate_limit_key_otp_lockout(user_id)
    cache.delete(key)
    cache.delete(lockout_key)


def _invalidate_existing_otps(user) -> None:
    """Mark all existing unused OTPs for this user as used."""
    MagicLink.objects.filter(
        user=user,
        used_at__isnull=True
    ).update(used_at=timezone.now())


def _normalize_phone(phone: str) -> str:
    """Normalize phone number by removing spaces and common formatting."""
    return re.sub(r'[\s\-\(\)]+', '', phone)


def magic_link_request(request: HttpRequest) -> HttpResponse:
    """Request an OTP to be sent to a registered user via email or phone."""
    start_time = time.time()
    
    if request.method == "POST":
        form = LoginRequestForm(request.POST)
        if form.is_valid():
            contact = form.cleaned_data["contact"].strip()
            
            # Determine if contact is email or phone
            is_email = '@' in contact
            
            if is_email:
                contact = contact.lower()
            else:
                contact = _normalize_phone(contact)
            
            # Store contact info in session for OTP verify page display
            # (do this early so the otp_verify page can show consistent info)
            request.session['otp_contact'] = contact
            request.session['otp_is_email'] = is_email
            request.session['otp_flow'] = 'login'
            
            # Check rate limit for OTP generation
            if _check_otp_generation_rate_limit(contact):
                # Redirect to same page to not reveal rate limiting
                _ensure_min_response_time(start_time)
                return redirect("pilot_access:otp_verify")
            
            # Look up profile
            profile = None
            if is_email:
                profile = PilotProfile.objects.select_related('user').filter(
                    email__iexact=contact
                ).first()
            else:
                profile = PilotProfile.objects.select_related('user').filter(
                    phone=contact
                ).first()
            
            # Always increment rate limit counter, even if user not found
            # This prevents enumeration via rate limit behavior
            _increment_otp_generation_count(contact)
            
            if not profile or not profile.disclaimer_accepted_at:
                # Do not reveal whether the contact exists - redirect to same page
                _ensure_min_response_time(start_time)
                return redirect("pilot_access:otp_verify")
            
            user = profile.user
            
            # Invalidate any existing unused OTPs for this user
            _invalidate_existing_otps(user)

            # Generate and send OTP
            otp = generate_otp()
            MagicLink.objects.create(
                user=user,
                token_hash=hash_token(otp),
                expires_at=timezone.now() + timedelta(minutes=15),
            )

            # Send OTP via the method they used to log in
            if is_email:
                email_sender = get_email_sender()
                email_sender.send_otp(email=contact, otp=otp)
            else:
                sms_sender = get_sms_sender()
                sms_sender.send_otp(phone=contact, otp=otp)

            # Store user ID in session for OTP verification
            request.session['otp_user_id'] = user.id
            request.session['otp_flow'] = 'login'
            request.session['otp_contact'] = contact
            request.session['otp_is_email'] = is_email
            
            # In DEBUG mode, store OTP in session for testers to see
            if settings.DEBUG:
                request.session['debug_otp'] = otp
            
            _ensure_min_response_time(start_time)
            return redirect("pilot_access:otp_verify")
    else:
        form = LoginRequestForm()

    return render(request, "pilot_access/magic_link_request.jinja", {"form": form})


def _ensure_min_response_time(start_time: float) -> None:
    """Ensure minimum response time to prevent timing attacks."""
    elapsed = time.time() - start_time
    if elapsed < MIN_RESPONSE_TIME:
        time.sleep(MIN_RESPONSE_TIME - elapsed)


def otp_verify(request: HttpRequest) -> HttpResponse:
    """Verify OTP code entered by user."""
    user_id = request.session.get('otp_user_id')
    otp_flow = request.session.get('otp_flow', 'login')
    otp_contact = request.session.get('otp_contact', '')
    otp_is_email = request.session.get('otp_is_email', True)
    
    # If no contact info at all, redirect to start
    if not otp_contact and not user_id:
        return redirect("pilot_access:landing")
    
    # Build contact display string
    if otp_is_email:
        contact_display = otp_contact
    else:
        contact_display = f"mobile number ending in {otp_contact[-4:]}" if otp_contact else "your mobile"
    
    # Check if user is locked out (use contact as key if no user_id)
    lockout_key = user_id if user_id else otp_contact
    if _check_otp_attempt_lockout(lockout_key):
        return render(request, "pilot_access/otp_locked.jinja", {
            "lockout_minutes": OTP_LOCKOUT_DURATION // 60,
        })
    
    # Try to get user and profile (may not exist for fake requests)
    user = None
    profile = None
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            profile = PilotProfile.objects.get(user=user)
        except (User.DoesNotExist, PilotProfile.DoesNotExist):
            user = None
            profile = None
    
    # Get remaining attempts for display
    attempts_used = _get_otp_attempt_count(lockout_key)
    attempts_remaining = max(0, OTP_ATTEMPT_LIMIT - attempts_used)
    
    if request.method == "POST":
        form = OTPForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data["otp"]
            otp_hash = hash_token(otp)
            
            # Find valid OTP for this user (will always fail if user is None)
            ml = None
            if user:
                try:
                    ml = MagicLink.objects.get(
                        user=user,
                        token_hash=otp_hash,
                        used_at__isnull=True,
                        expires_at__gt=timezone.now()
                    )
                except MagicLink.DoesNotExist:
                    pass
            
            if not ml:
                # Increment failed attempt counter
                new_count = _increment_otp_attempt_count(lockout_key)
                attempts_remaining = max(0, OTP_ATTEMPT_LIMIT - new_count)
                
                if new_count >= OTP_ATTEMPT_LIMIT:
                    # User is now locked out
                    return render(request, "pilot_access/otp_locked.jinja", {
                        "lockout_minutes": OTP_LOCKOUT_DURATION // 60,
                    })
                
                form.add_error("otp", f"Invalid or expired code. You have {attempts_remaining} attempt(s) remaining.")
                return render(request, "pilot_access/otp_verify.jinja", {
                    "form": form,
                    "contact_display": contact_display,
                    "attempts_remaining": attempts_remaining,
                    "debug_otp": request.session.get('debug_otp') if settings.DEBUG else None,
                })
            
            # Success! Mark OTP as used
            ml.used_at = timezone.now()
            ml.save(update_fields=["used_at"])
            
            # Clear attempt counter on success
            _clear_otp_attempt_count(lockout_key)
            
            # If this is a new signup, mark disclaimer as accepted
            if otp_flow == 'signup' and not profile.disclaimer_accepted_at:
                profile.disclaimer_accepted_at = timezone.now()
                profile.save(update_fields=["disclaimer_accepted_at"])
            
            # Log the user in
            login(request, user)
            
            # Regenerate session to prevent session fixation
            request.session.cycle_key()
            
            request.session["entry_flow"] = "otp"
            
            # Clear OTP session data
            request.session.pop('otp_user_id', None)
            request.session.pop('otp_flow', None)
            request.session.pop('otp_contact', None)
            request.session.pop('otp_is_email', None)
            request.session.pop('campaign_code', None)
            request.session.pop('disclaimer_accepted', None)
            
            # Restore user's previous journey answers
            try:
                uf = UserFilter.objects.get(user=user)
                if uf and uf.data:
                    for key, value in uf.data.items():
                        request.session[key] = value
                    request.session.modified = True
            except UserFilter.DoesNotExist:
                pass
            
            return redirect("/")
    else:
        form = OTPForm()
    
    return render(request, "pilot_access/otp_verify.jinja", {
        "form": form,
        "contact_display": contact_display,
        "attempts_remaining": attempts_remaining,
        "debug_otp": request.session.get('debug_otp') if settings.DEBUG else None,
    })


@require_POST
def logout_post(request: HttpRequest) -> HttpResponse:
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("pilot_access:landing")


def landing(request: HttpRequest) -> HttpResponse:
    cc = request.GET.get('cc', '').strip()
    
    context = {
        'campaign_code': cc,
        'campaign': None,
        'campaign_invalid': False,
        'show_magic_link': False,
        'form': None,
    }
    
    if cc:
        # Campaign code was provided - look it up
        try:
            campaign = Campaign.objects.get(campaign_code=cc)
            if campaign.is_valid_today():
                # Valid campaign - show disclaimer form
                context['campaign'] = campaign
                
                if request.method == "POST":
                    form = DisclaimerForm(request.POST)
                    if form.is_valid():
                        # Store campaign code in session and redirect to contact info page
                        request.session['campaign_code'] = cc
                        request.session['disclaimer_accepted'] = True
                        return redirect("pilot_access:campaign_contact_info")
                    context['form'] = form
                else:
                    context['form'] = DisclaimerForm()
            else:
                # Campaign exists but is out of date range
                context['campaign_invalid'] = True
        except Campaign.DoesNotExist:
            # Campaign code doesn't exist
            context['campaign_invalid'] = True
    else:
        # No campaign code - show magic link request option
        context['show_magic_link'] = True
    
    return render(request, "pilot_access/landing.jinja", context)


def campaign_contact_info(request: HttpRequest) -> HttpResponse:
    """Page to collect user contact info after accepting disclaimer."""
    start_time = time.time()
    
    # Check that user came through proper flow
    if not request.session.get('disclaimer_accepted'):
        return redirect("pilot_access:landing")
    
    campaign_code = request.session.get('campaign_code', '')
    
    # Validate campaign still exists and is valid
    try:
        campaign = Campaign.objects.get(campaign_code=campaign_code)
        if not campaign.is_valid_today():
            return redirect("pilot_access:landing")
    except Campaign.DoesNotExist:
        return redirect("pilot_access:landing")
    
    errors = {}
    data = {}
    
    if request.method == "POST":
        form = CampaignContactForm(request.POST)
        data = {
            'email': request.POST.get('email', ''),
            'phone': request.POST.get('phone', ''),
            'preferred_contact_method': request.POST.get('preferred_contact_method', ''),
        }
        
        if form.is_valid():
            email = form.cleaned_data['email']
            phone = form.cleaned_data['phone']
            pref = form.cleaned_data['preferred_contact_method']
            
            # Normalize phone number
            if phone:
                phone = _normalize_phone(phone)
            
            # Determine contact for rate limiting
            contact_for_limit = email if pref == PilotProfile.CONTACT_EMAIL else phone
            
            # Check rate limit for OTP generation
            if _check_otp_generation_rate_limit(contact_for_limit):
                if settings.DEBUG:
                    key = _rate_limit_key_otp_generation(contact_for_limit)
                    count = cache.get(key, 0)
                    errors['__all__'] = f'Too many requests. Please try again later. (DEBUG: count={count}, limit={OTP_GENERATION_LIMIT})'
                else:
                    errors['__all__'] = 'Too many requests. Please try again later.'
                _ensure_min_response_time(start_time)
                return render(request, "pilot_access/campaign_contact_info.jinja", {
                    'campaign_code': campaign_code,
                    'errors': errors,
                    'data': data,
                })
            
            _increment_otp_generation_count(contact_for_limit)
            
            with transaction.atomic():
                # Create Django user with random username
                username = generate_username()
                user = User.objects.create_user(
                    username=username,
                    email=email if email else None,
                )
                user.set_unusable_password()
                user.save()
                
                # Create PilotProfile
                profile = PilotProfile.objects.create(
                    user=user,
                    campaign=campaign,
                    email=email,
                    phone=phone,
                    preferred_contact_method=pref,
                    # disclaimer_accepted_at will be set after OTP verification
                )
                
                # Generate and send OTP
                otp = generate_otp()
                MagicLink.objects.create(
                    user=user,
                    token_hash=hash_token(otp),
                    expires_at=timezone.now() + timedelta(minutes=15),
                )
                
                # Send OTP via preferred method
                if pref == PilotProfile.CONTACT_SMS:
                    sms_sender = get_sms_sender()
                    sms_sender.send_otp(phone=phone, otp=otp)
                    otp_contact = phone
                    otp_is_email = False
                else:
                    email_sender = get_email_sender()
                    email_sender.send_otp(email=email, otp=otp)
                    otp_contact = email
                    otp_is_email = True
                
                # Store user ID in session for OTP verification
                request.session['otp_user_id'] = user.id
                request.session['otp_flow'] = 'signup'
                request.session['otp_contact'] = otp_contact
                request.session['otp_is_email'] = otp_is_email
                
                # In DEBUG mode, store OTP in session for testers to see
                if settings.DEBUG:
                    request.session['debug_otp'] = otp
                
                _ensure_min_response_time(start_time)
                return redirect("pilot_access:otp_verify")
        else:
            # Extract errors for template
            for field, error_list in form.errors.items():
                errors[field] = error_list[0] if error_list else ''
    
    return render(request, "pilot_access/campaign_contact_info.jinja", {
        'campaign_code': campaign_code,
        'errors': errors,
        'data': data,
    })


@xframe_options_sameorigin
def disclaimer(request: HttpRequest) -> HttpResponse:
    return render(request, "pilot_access/disclaimer.jinja")


def account(request: HttpRequest) -> HttpResponse:
    """Show and edit the currently-logged-in pilot user's account details."""
    user = request.user
    profile = getattr(request, "pilot_access_profile", None)
    if profile is None:
        profile = PilotProfile.objects.get(user=user)

    next_url = request.GET.get("next") or request.POST.get("next") or request.META.get("HTTP_REFERER") or ""
    if next_url and not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = ""

    if request.method == "POST":
        form = PilotAccountForm(user=user, profile=profile, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account updated.")
            return redirect(next_url or reverse("pilot_access:account"))
    else:
        form = PilotAccountForm(user=user, profile=profile)

    return render(
        request,
        "pilot_access/account.jinja",
        {
            "form": form,
            "profile": profile,
            "next": next_url,
        },
    )


def delete_account(request: HttpRequest) -> HttpResponse:
    """Confirm + delete the pilot user's account and related pilot_access records."""
    user = request.user
    profile = getattr(request, "pilot_access_profile", None)
    if profile is None:
        profile = PilotProfile.objects.get(user=user)

    if request.method == "POST":
        form = DeleteAccountForm(data=request.POST)
        if form.is_valid():
            with transaction.atomic():
                user.delete()

            logout(request)
            messages.success(request, "Your account has been deleted.")
            return redirect("pilot_access:landing")
    else:
        form = DeleteAccountForm()

    return render(
        request,
        "pilot_access/delete_account.jinja",
        {
            "form": form,
            "email": profile.email or user.email,
        },
    )
