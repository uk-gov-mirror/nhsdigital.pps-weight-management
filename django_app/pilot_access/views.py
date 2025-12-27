from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import MagicLinkRequestForm
from .forms import InviteRequestForm, DisclaimerForm
from .models import InviteRequest, Invitation, PilotProfile, MagicLink

from .services.tokens import generate_token, hash_token
from .services.sender import get_email_sender

import hashlib

_RATE_LIMIT_WINDOW_SECONDS = 60 * 10  # 10 minutes
_RATE_LIMIT_MAX_SUBMITS = 5

User = get_user_model()

def _rate_limit_key(request: HttpRequest, email: str) -> str:
    ip = request.META.get("REMOTE_ADDR", "") or "unknown"
    return f"pilot_access:invite_request:{ip}:{email.strip().lower()}"


def request_invite(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = InviteRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()

            key = _rate_limit_key(request, email)
            current = cache.get(key, 0)

            if current >= _RATE_LIMIT_MAX_SUBMITS:
                # Show the same page with a friendly rate limit message
                return render(
                    request,
                    "pilot_access/request_invite.jinja",
                    {
                        "form": form,
                        "rate_limited": True,
                        "rate_limit_window_minutes": int(_RATE_LIMIT_WINDOW_SECONDS / 60),
                    },
                    status=429,
                )

            cache.set(key, current + 1, timeout=_RATE_LIMIT_WINDOW_SECONDS)

            # Create or refresh an existing request.
            obj, created = InviteRequest.objects.get_or_create(email=email)
            if not created:
                obj.created_at = timezone.now()
                obj.status = InviteRequest.STATUS_PENDING
                obj.save(update_fields=["created_at", "status"])

            return redirect("pilot_access:request_invite_done")
    else:
        form = InviteRequestForm()

    return render(request, "pilot_access/request_invite.jinja", {"form": form})


def request_invite_done(request: HttpRequest) -> HttpResponse:
    return render(request, "pilot_access/request_invite_done.jinja")


def accept_invitation(request: HttpRequest) -> HttpResponse:
    raw_token = (request.GET.get("token") or "").strip()
    if not raw_token:
        return HttpResponse("Missing token.", status=400)

    token_hash = hash_token(raw_token)

    try:
        invitation = Invitation.objects.get(token_hash=token_hash)
    except Invitation.DoesNotExist:
        return HttpResponse("Invalid invitation.", status=404)

    if not invitation.is_valid():
        return HttpResponse("Invitation expired or already used.", status=410)

    if request.method == "POST":
        form = DisclaimerForm(request.POST)
        if form.is_valid():
            now = timezone.now()

            User = get_user_model()
            user, created = User.objects.get_or_create(
                email=invitation.email,
                defaults={"username": invitation.email},
            )
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])

            PilotProfile.objects.update_or_create(
                user=user,
                defaults={
                    "invited_at": now,
                    "disclaimer_accepted_at": now,
                },
            )

            invitation.used_at = now
            invitation.save(update_fields=["used_at"])

            login(request, user)
            messages.success(request, "Thanks — access enabled.")
            return redirect("/")

    else:
        form = DisclaimerForm()

    return render(
        request,
        "pilot_access/accept_invitation.jinja",
        {"form": form, "email": invitation.email},
    )

def magic_link_request(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = MagicLinkRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()

            # Only send links for users who are already invited + accepted disclaimer
            try:
                user = User.objects.get(email__iexact=email)
                profile = PilotProfile.objects.get(user=user)
            except (User.DoesNotExist, PilotProfile.DoesNotExist):
                # Do not reveal whether an email exists
                return render(request, "pilot_access/magic_link_sent.jinja")

            # (optional) also require disclaimer accepted flag on profile
            if not profile.disclaimer_accepted_at:
                return render(request, "pilot_access/magic_link_sent.jinja")

            raw = generate_token()
            MagicLink.objects.create(
                user=user,
                token_hash=hash_token(raw),
                expires_at=timezone.now() + timedelta(minutes=15),
            )

            link = request.build_absolute_uri(
                reverse("pilot_access:magic_link_consume") + f"?t={raw}"
            )
            email_sender = get_email_sender()
            email_sender.send_magic_link(email=email, link=link)

            return render(request, "pilot_access/magic_link_sent.jinja")
    else:
        form = MagicLinkRequestForm()

    return render(request, "pilot_access/magic_link_request.jinja", {"form": form})


def magic_link_consume(request: HttpRequest) -> HttpResponse:
    raw = request.GET.get("t", "")
    if not raw:
        return redirect("pilot_access:magic_link_request")

    token_h = hash_token(raw)
    try:
        ml = MagicLink.objects.select_related("user").get(token_hash=token_h)
    except MagicLink.DoesNotExist:
        return redirect("pilot_access:magic_link_request")

    if not ml.is_valid():
        return redirect("pilot_access:magic_link_request")

    ml.used_at = timezone.now()
    ml.save(update_fields=["used_at"])

    login(request, ml.user)
    return redirect("/") 

@require_POST
def logout_post(request: HttpRequest) -> HttpResponse:
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("pilot_access:landing")

def landing(request: HttpRequest) -> HttpResponse:
    return render(request, "pilot_access/landing.jinja")
