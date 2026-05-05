"""
Public web views for the healthy habits journey.

The journey is a multi-step form stored in the session. Rough order:

1. start                - flush session and show the start page
2. consent_to_htsh     - HTSH consent
3. consent_to_ur        - user research consent
4. details_name         - collect participant name
5. details_postcode     - validate postcode via api.postcodes.io
6. details_contact_details
7. goals, barriers      - goals and barriers
8. preference_*         - preferences (who with / timetable / channel)
9. allow-check-in       - user permission to check in
10. listing             - show matching services from the API
11. detail              - show a single service from the API

All state is stored in request.session; the API is called at the listing/detail
steps. Templates live under ``templates/jinja2/web/pages`` and are referenced
as ``web/pages/<name>.jinja``.
"""

import logging
import re
from json import JSONDecodeError
from typing import Any, Dict, List

import requests
from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POSTCODE_REGEX = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$", re.I)
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MOBILE_REGEX = re.compile(r"^\+?[0-9][0-9\s\-]{7,}$")

# Pagination
PAGE_SIZE_OPTIONS = [5, 10, 15, 20]
DEFAULT_PAGE_SIZE = 10

# Search distance (miles)
DISTANCE_OPTIONS = [5, 10, 15]
DEFAULT_DISTANCE = 5

CHECKBOX_UNCHECKED_VALUE = "_unchecked"
DONT_MIND_VALUE = "dont_mind"

SESSION_KEY_DETAILS_POSTCODE = "details-postcode"
SESSION_KEY_CONTACT = "contact"
SESSION_KEY_EMAIL = "emailInput"
SESSION_KEY_MOBILE = "mobileInput"
SESSION_KEY_ANONYMOUS_FAVOURITES = "anonymous_favourite_service_ids"

POSTCODE_API_TEMPLATE = "https://api.postcodes.io/postcodes/{postcode}/validate"
POSTCODE_API_TIMEOUT = 5

SERVICE_SEARCH_TIMEOUT = 10
SERVICE_DETAIL_TIMEOUT = 10

FILTER_FIELDS: List[str] = [
    "cost",
    "location",
    "taught",
]


QUESTIONNAIRE_SESSION_KEYS: List[str] = [
    "motivation",
    "priority_behaviour",
    "past_barriers",
    "current_barriers",
    "confidence_readiness",
    "enablers",
]


QUESTION_OPTION_LABELS: Dict[str, str] = {
    # Q1 motivation
    "motivation.want_to_feel_better": "I want to feel better in myself",
    "motivation.noticed_changes": "I've noticed changes in my weight or fitness",
    "motivation.health_professional": "A health professional suggested it",
    "motivation.social_encouragement": "A friend or family member encouraged me",
    "motivation.health_scare": "I've had a health scare or diagnosis",
    "motivation.setting_example": "I want to set a good example for others",
    "motivation.tried_before": "I've tried before and want to try again",
    "motivation.life_transition": "I'm at a point in my life where I want to make a change",
    "motivation.just_exploring": "I'm not sure - I'm just exploring",
    # Q2 priority behaviour
    "priority_behaviour.more_physically_active": "Becoming more physically active",
    "priority_behaviour.eating_drinking": "Improving what I eat or drink",
    "priority_behaviour.managing_weight": "Managing my weight",
    "priority_behaviour.mental_wellbeing": "Improving my mental wellbeing (e.g. stress, mood, sleep)",
    "priority_behaviour.energy_stamina": "Building my energy and stamina",
    "priority_behaviour.managing_condition": "Managing a health condition better",
    "priority_behaviour.body_confidence": "Feeling more confident in my body",
    # Q3 past barriers
    "past_barriers.no_time": "I didn't have enough time",
    "past_barriers.too_expensive": "It was too expensive",
    "past_barriers.not_physically_able": "I didn't feel physically able or well enough",
    "past_barriers.didnt_know_where_to_start": "I didn't know what to do or where to start",
    "past_barriers.lost_motivation": "I lost motivation or interest over time",
    "past_barriers.no_one_to_do_it_with": "I didn't have anyone to do it with",
    "past_barriers.nothing_nearby": "There were no suitable options near me",
    "past_barriers.life_pressures": "Life got in the way (stress, work, family)",
    "past_barriers.lack_of_confidence": "I didn't feel confident enough",
    # Q4 current barriers
    "current_barriers.short_on_time": "I'm short on time",
    "current_barriers.cant_afford_it": "I can't afford it",
    "current_barriers.health_condition": "My health or a physical condition limits what I can do",
    "current_barriers.not_sure_what_works": "I'm not sure what would actually work for me",
    "current_barriers.low_motivation": "I don't feel motivated right now",
    "current_barriers.self_conscious": "I feel self-conscious or anxious about trying something new",
    "current_barriers.practical_barriers": "I don't have practical support (e.g. childcare, transport)",
    "current_barriers.routine": "I find it hard to make things a routine",
    "current_barriers.low_perceived_need": "I feel fine and don't see an urgent need to change",
    # Q5 confidence and readiness
    "confidence_readiness.ready_and_confident": "I feel ready and confident - I just need the right option",
    "confidence_readiness.keen_but_worried": "I'm keen but not sure I can stick to it",
    "confidence_readiness.want_to_but_barriers": "I want to but I'm worried about what might get in the way",
    "confidence_readiness.not_quite_ready": "I'm thinking about it but not quite ready to commit",
    "confidence_readiness.change_out_of_reach": "I'm not sure change is possible for me right now",
    # Q6 enablers
    "enablers.wont_take_too_much_time": "Knowing it won't take up too much time",
    "enablers.affordable": "Finding something affordable",
    "enablers.support_from_others": "Having support from other people",
    "enablers.start_slowly": "Doing something I can start slowly and build up",
    "enablers.suitable_for_me": "Knowing it's suitable for someone like me",
    "enablers.home_online": "Being able to do it from home or online",
    "enablers.clear_guidance": "Having clear guidance on what to do",
    "enablers.will_make_a_difference": "Knowing it will actually make a difference",
}


def _format_answer_label(value: Any) -> str:
    """Return human-readable text for a stored questionnaire answer value."""
    if not value:
        return "Not set"
    if not isinstance(value, str):
        return str(value)

    mapped = QUESTION_OPTION_LABELS.get(value)
    if mapped:
        return mapped

    # Fallback for unknown values: drop question prefix and prettify token.
    code = value.split(".", 1)[-1]
    return code.replace("_", " ").capitalize()


def _format_answer_list(values: Any) -> List[str]:
    """Return human-readable text for multi-select questionnaire answers."""
    if not values:
        return ["Not set"]
    if isinstance(values, list):
        return [_format_answer_label(v) for v in values]
    return [_format_answer_label(values)]


def _get_anonymous_favourite_ids(session) -> set[int]:
    """Return normalized anonymous favourite service IDs from session."""
    raw_values = session.get(SESSION_KEY_ANONYMOUS_FAVOURITES, [])
    if not isinstance(raw_values, list):
        raw_values = []

    normalized: set[int] = set()
    for value in raw_values:
        try:
            normalized.add(int(value))
        except (TypeError, ValueError):
            # Ignore stale/invalid values without blocking UX.
            continue

    canonical = sorted(normalized)
    if raw_values != canonical:
        session[SESSION_KEY_ANONYMOUS_FAVOURITES] = canonical
        session.modified = True

    return normalized


def _set_anonymous_favourite_ids(session, service_ids: set[int]) -> None:
    """Persist canonical anonymous favourite IDs in session."""
    session[SESSION_KEY_ANONYMOUS_FAVOURITES] = sorted(service_ids)
    session.modified = True


PERSISTED_SESSION_KEYS: List[str] = [
    SESSION_KEY_DETAILS_POSTCODE,
    # Listing filters (set/edited on listing page)
    "cost",
    "location",
    "taught",
]


def _get_or_create_user_filter(user):
    """Return the user's persisted filter record (creating if needed)."""
    from htsh.models import UserFilter

    uf, _ = UserFilter.objects.get_or_create(user=user)
    return uf


def _persist_to_user_filter(user, key: str, value: Any) -> None:
    """Persist a session key/value to the user's filter record."""
    if not getattr(user, "is_authenticated", False):
        return
    uf = _get_or_create_user_filter(user)
    uf.set_value(key, value)
    uf.save(update_fields=["data", "updated_at"])


def _persist_questionnaire_answer(user, key: str, value: Any) -> None:
    """Persist a questionnaire answer to QuestionnaireResponse, deriving tags."""
    if not getattr(user, "is_authenticated", False):
        return
    from htsh.models import QuestionnaireResponse

    qr, _ = QuestionnaireResponse.objects.get_or_create(user=user)
    qr.set_answer(key, value)
    qr.derive_behavioural_tags()
    qr.derive_activity_attributes()
    qr.save()


def _hydrate_session_from_user_filter(request: HttpRequest) -> None:
    """Load persisted answers into the session if present."""
    user = request.user
    if not getattr(user, "is_authenticated", False):
        return

    changed = False

    # Hydrate questionnaire answers from QuestionnaireResponse
    from htsh.models import QuestionnaireResponse

    try:
        qr = QuestionnaireResponse.objects.get(user=user)
        for key in QUESTIONNAIRE_SESSION_KEYS:
            val = qr.get_answer(key)
            if val is not None and val != "" and val != []:
                request.session[key] = val
                changed = True
    except QuestionnaireResponse.DoesNotExist:
        pass

    # Hydrate filter keys from UserFilter (postcode, cost, location, taught)
    from htsh.models import UserFilter

    try:
        uf = UserFilter.objects.get(user=user)
    except UserFilter.DoesNotExist:
        if changed:
            request.session.modified = True
        return

    data = uf.data or {}
    for key in PERSISTED_SESSION_KEYS:
        if key in data and data[key] is not None:
            request.session[key] = data[key]
            changed = True
    if changed:
        request.session.modified = True


# ---------------------------------------------------------------------------
# Journey: start and consent
# ---------------------------------------------------------------------------


def start(request: HttpRequest) -> HttpResponse:
    """Don't call session.flush() !! It clears the logged in users sessionid"""
    from htsh.models import UserFilter, QuestionnaireResponse

    # request.session.flush()
    onboarding_complete = request.session.get("onboarding_complete", False)
    opted_in = False
    user_fields = {}

    if request.user.is_authenticated:
        start_href = "details-contact-details"
        # Check QuestionnaireResponse for existing questionnaire answers
        try:
            qr = QuestionnaireResponse.objects.get(user=request.user)
            if qr.motivation or qr.past_barriers:  # has answered at least one question
                start_href = "listing"
                for key in QUESTIONNAIRE_SESSION_KEYS:
                    val = qr.get_answer(key)
                    if val is not None and val != "" and val != []:
                        user_fields[key] = val
        except QuestionnaireResponse.DoesNotExist:
            pass
        # Check UserFilter for filter keys + allow_check_in
        try:
            uf = UserFilter.objects.get(user=request.user)
            if uf.data:
                if not user_fields:  # No questionnaire yet but has UserFilter
                    start_href = "listing"
                opted_in = uf.data.get("allow_check_in") == "yes"
                for key in PERSISTED_SESSION_KEYS:
                    if key in uf.data and uf.data[key] is not None:
                        user_fields[key] = uf.data[key]
        except UserFilter.DoesNotExist:
            pass
    else:
        # Anonymous campaign user — skip contact details, start at postcode
        start_href = "questionnaire-intro"
        # Populate user_fields from session so the summary renders correctly
        if onboarding_complete:
            for key in QUESTIONNAIRE_SESSION_KEYS + PERSISTED_SESSION_KEYS:
                if key in request.session:
                    user_fields[key] = request.session[key]

    # Legacy check for magic link flow
    if request.session.get("entry_flow") == "magiclink":
        start_href = "listing"

    user_fields_display = {
        "motivation": _format_answer_label(user_fields.get("motivation")),
        "priority_behaviour": _format_answer_label(user_fields.get("priority_behaviour")),
        "past_barriers": _format_answer_list(user_fields.get("past_barriers")),
        "current_barriers": _format_answer_list(user_fields.get("current_barriers")),
        "confidence_readiness": _format_answer_label(user_fields.get("confidence_readiness")),
        "enablers": _format_answer_list(user_fields.get("enablers")),
    }

    return render(
        request,
        "web/pages/index.jinja",
        {
            "data": request.session,
            "start_href": start_href,
            "onboarding_complete": onboarding_complete,
            "opted_in": opted_in,
            "user_fields": user_fields,
            "user_fields_display": user_fields_display,
        },
    )


# ---------------------------------------------------------------------------
# Journey: personal details
# ---------------------------------------------------------------------------


def details_contact_details(request: HttpRequest) -> HttpResponse:
    """Collect contact details and a preferred contact method.

    This page mirrors the account page: email + phone text inputs, and a single
    preferred contact method (email or text message).
    """
    from django.contrib.auth import get_user_model
    from htsh.models import UserProfile

    user = request.user
    profile = getattr(user, "profile", None)

    # Initial values come from the profile (and Django user for email)
    initial = {
        "email": getattr(user, "email", "") or "",
        "phone": getattr(profile, "phone", "") if profile else "",
        "preferred_contact_method": (
            getattr(profile, "preferred_contact_method", "") if profile else ""
        ),
    }

    if not initial["preferred_contact_method"]:
        initial["preferred_contact_method"] = UserProfile.CONTACT_EMAIL

    errors: Dict[str, Any] = {"list": []}
    values = dict(initial)

    if request.method == "POST":
        values["email"] = (request.POST.get("email") or "").strip()
        values["phone"] = (request.POST.get("phone") or "").strip()
        values["preferred_contact_method"] = (
            request.POST.get("preferred_contact_method") or ""
        ).strip()

        pref = values["preferred_contact_method"]

        if pref not in (UserProfile.CONTACT_EMAIL, UserProfile.CONTACT_SMS):
            errors["preferred_contact_method"] = True
            errors["list"].append(
                {
                    "text": "Please choose a preferred contact method",
                    "href": "#preferredContact",
                }
            )

        # Validate per preference
        if pref == UserProfile.CONTACT_EMAIL:
            if not _is_valid_email(values["email"]):
                errors["email"] = True
                errors["list"].append(
                    {
                        "text": "Please enter a valid email address",
                        "href": "#emailInput",
                    }
                )
        elif pref == UserProfile.CONTACT_SMS:
            if not _is_valid_mobile(values["phone"]):
                errors["phone"] = True
                errors["list"].append(
                    {
                        "text": "Please enter a valid mobile phone number",
                        "href": "#phoneInput",
                    }
                )

        # If user changed their email, enforce uniqueness
        if not errors.get("email") and values["email"]:
            User = get_user_model()
            if (
                User.objects.filter(email__iexact=values["email"])
                .exclude(pk=user.pk)
                .exists()
            ):
                errors["email"] = True
                errors["list"].append(
                    {
                        "text": "That email address is already in use",
                        "href": "#emailInput",
                    }
                )

        # If user entered/changed their phone, enforce uniqueness against UserProfile
        if not errors.get("phone") and values["phone"]:
            qs = UserProfile.objects.filter(phone=values["phone"])
            if profile is not None and profile.pk is not None:
                qs = qs.exclude(pk=profile.pk)
            if qs.exists():
                errors["phone"] = True
                errors["list"].append(
                    {
                        "text": "That mobile number is already in use",
                        "href": "#phoneInput",
                    }
                )

        if not errors["list"]:
            # Persist to session (for existing journey behaviour)
            request.session[SESSION_KEY_EMAIL] = values["email"]
            request.session[SESSION_KEY_MOBILE] = values["phone"]
            request.session[SESSION_KEY_CONTACT] = [pref]

            # Persist to profile (+ user email)
            if values["email"] and values["email"] != (user.email or ""):
                user.email = values["email"]
                user.username = values["email"]
                user.save(update_fields=["email", "username"])

            if profile is not None:
                profile.phone = values["phone"]
                profile.preferred_contact_method = pref
                profile.save(update_fields=["phone", "preferred_contact_method"])

            return redirect("questionnaire_intro")

    return render(
        request,
        "web/pages/details-contact-details.jinja",
        {"data": values, "errors": errors},
    )


def details_postcode(request: HttpRequest) -> HttpResponse:
    """Collect and validate the participant's postcode.

    Validates locally (UK postcode format) and then via api.postcodes.io.
    On success, stores the postcode in the session and (if available) saves it
    to the authenticated user's UserProfile.
    """
    user = request.user
    profile = getattr(user, "profile", None)

    if request.method == "POST":
        postcode = (request.POST.get(SESSION_KEY_DETAILS_POSTCODE) or "").strip()
        validation = _validate_postcode(postcode)

        if not validation["isValid"]:
            data = dict(request.session)
            data[SESSION_KEY_DETAILS_POSTCODE] = postcode
            return render(
                request,
                "web/pages/details-postcode.jinja",
                {"error": True, "data": data, "postcode_error": validation["error"]},
            )

        request.session[SESSION_KEY_DETAILS_POSTCODE] = postcode

        # Persist the user's postcode answer (session key) so it can be restored
        # for returning users.
        _persist_to_user_filter(user, SESSION_KEY_DETAILS_POSTCODE, postcode)

        # Persist to profile if present
        if profile is not None:
            profile.postcode = postcode
            profile.save(update_fields=["postcode"])

        return redirect("motivation")

    return render(
        request,
        "web/pages/details-postcode.jinja",
        {"data": request.session},
    )


# ---------------------------------------------------------------------------
# Journey: behavioural questionnaire (Q1–Q6)
# ---------------------------------------------------------------------------


def motivation(request: HttpRequest) -> HttpResponse:
    """Q1: What prompted you to look for support with your health today?"""
    mode = request.GET.get("mode")
    back_href = "/" if mode == "edit" else "/details-postcode"
    if request.method == "POST":
        value = request.POST.get("motivation")
        if value in (None, "", CHECKBOX_UNCHECKED_VALUE):
            return render(
                request,
                "web/pages/motivation.jinja",
                {"error": True, "data": request.session, "back_href": back_href},
            )
        request.session["motivation"] = value
        _persist_questionnaire_answer(request.user, "motivation", value)
        if mode == "edit":
            messages.success(request, "Your data has been updated.")
            return redirect("/")
        return redirect("priority_behaviour")

    return render(
        request,
        "web/pages/motivation.jinja",
        {"data": request.session, "back_href": back_href},
    )


def priority_behaviour(request: HttpRequest) -> HttpResponse:
    """Q2: Which would make the biggest difference to your health right now?"""
    mode = request.GET.get("mode")
    back_href = "/" if mode == "edit" else "/motivation"
    if request.method == "POST":
        value = request.POST.get("priority_behaviour")
        if value in (None, "", CHECKBOX_UNCHECKED_VALUE):
            return render(
                request,
                "web/pages/priority-behaviour.jinja",
                {"error": True, "data": request.session, "back_href": back_href},
            )
        request.session["priority_behaviour"] = value
        _persist_questionnaire_answer(request.user, "priority_behaviour", value)
        if mode == "edit":
            messages.success(request, "Your data has been updated.")
            return redirect("/")
        return redirect("past_barriers")

    return render(
        request,
        "web/pages/priority-behaviour.jinja",
        {"data": request.session, "back_href": back_href},
    )


def past_barriers(request: HttpRequest) -> HttpResponse:
    """Q3: What has made it difficult for you to keep up healthy habits?"""
    mode = request.GET.get("mode")
    back_href = "/" if mode == "edit" else "/priority-behaviour"
    if request.method == "POST":
        values = _clean_checkbox_list("past_barriers", request)
        if not values:
            return render(
                request,
                "web/pages/past-barriers.jinja",
                {"error": True, "data": request.session, "back_href": back_href},
            )
        request.session["past_barriers"] = values
        _persist_questionnaire_answer(request.user, "past_barriers", values)
        if mode == "edit":
            messages.success(request, "Your data has been updated.")
            return redirect("/")
        return redirect("current_barriers")

    return render(
        request,
        "web/pages/past-barriers.jinja",
        {"data": request.session, "back_href": back_href},
    )


def current_barriers(request: HttpRequest) -> HttpResponse:
    """Q4: What is making it hardest for you to build healthy habits right now?"""
    mode = request.GET.get("mode")
    back_href = "/" if mode == "edit" else "/past-barriers"
    if request.method == "POST":
        values = _clean_checkbox_list("current_barriers", request)
        if not values:
            return render(
                request,
                "web/pages/current-barriers.jinja",
                {"error": True, "data": request.session, "back_href": back_href},
            )
        request.session["current_barriers"] = values
        _persist_questionnaire_answer(request.user, "current_barriers", values)
        if mode == "edit":
            messages.success(request, "Your data has been updated.")
            return redirect("/")
        return redirect("confidence_readiness")

    return render(
        request,
        "web/pages/current-barriers.jinja",
        {"data": request.session, "back_href": back_href},
    )


def confidence_readiness(request: HttpRequest) -> HttpResponse:
    """Q5: How do you feel about making a change to your health habits?"""
    mode = request.GET.get("mode")
    back_href = "/" if mode == "edit" else "/current-barriers"
    if request.method == "POST":
        value = request.POST.get("confidence_readiness")
        if value in (None, "", CHECKBOX_UNCHECKED_VALUE):
            return render(
                request,
                "web/pages/confidence-readiness.jinja",
                {"error": True, "data": request.session, "back_href": back_href},
            )
        request.session["confidence_readiness"] = value
        _persist_questionnaire_answer(request.user, "confidence_readiness", value)
        if mode == "edit":
            messages.success(request, "Your data has been updated.")
            return redirect("/")
        return redirect("enablers")

    return render(
        request,
        "web/pages/confidence-readiness.jinja",
        {"data": request.session, "back_href": back_href},
    )


def enablers(request: HttpRequest) -> HttpResponse:
    """Q6: What would make it easier for you to take that first step?"""
    mode = request.GET.get("mode")
    back_href = "/" if mode == "edit" else "/confidence-readiness"
    if request.method == "POST":
        values = _clean_checkbox_list("enablers", request)
        if not values:
            return render(
                request,
                "web/pages/enablers.jinja",
                {"error": True, "data": request.session, "back_href": back_href},
            )
        request.session["enablers"] = values
        _persist_questionnaire_answer(request.user, "enablers", values)
        if mode == "edit":
            messages.success(request, "Your data has been updated.")
            return redirect("/")
        request.session["onboarding_complete"] = True
        return redirect("home")

    return render(
        request,
        "web/pages/enablers.jinja",
        {"data": request.session, "back_href": back_href},
    )


def questionnaire_intro(request: HttpRequest) -> HttpResponse:
    """Provide context before users begin the questionnaire."""
    if request.method == "POST":
        return redirect("details_postcode")

    return render(
        request,
        "web/pages/questionnaire-intro.jinja",
    )

# ---------------------------------------------------------------------------
# Journey: option to allow check-in
# ---------------------------------------------------------------------------

def allow_check_in(request: HttpRequest) -> HttpResponse:
    """Collect user permission to check in."""
    mode = request.GET.get("mode")
    back_href = "/" if mode == "edit" else "/enablers"
    if request.method == "POST":

        value = request.POST.get("allow_check_in")
        request.session["allow_check_in"] = value
        _persist_to_user_filter(request.user, "allow_check_in", value)

        service_id = request.session.pop("account_prompt_service_id", None)
        if service_id and value in ("yes", "no"):
            request.session["onboarding_complete"] = True
            return redirect("detail", service_id=service_id)

        if mode == "edit" and value in ("yes", "no"):
            messages.success(request, "Your data has been updated.")
            return redirect("/")
        elif value == "no":
            request.session["onboarding_complete"] = True
            return redirect("no_check_in")
        elif value == "yes":
            request.session["onboarding_complete"] = True
            return redirect("listing")
        else:
            return render(
                request,
                "web/pages/allow-check-in.jinja",
                {"error": True, "data": request.session, "back_href": back_href},
            )

    return render(
        request,
        "web/pages/allow-check-in.jinja",
        {"data": request.session, "back_href": back_href},
    )


def no_check_in(request: HttpRequest) -> HttpResponse:
    """Show a page when user declines check-in."""
    return render(
        request,
        "web/pages/no-check-in.jinja",
    )

# ---------------------------------------------------------------------------
# Journey: listing and detail (API-backed)
# ---------------------------------------------------------------------------


def listing(request: HttpRequest) -> HttpResponse:
    """Show the list of matching services from the API.

    Filters are derived from the session and any POSTed checkbox values. The
    payload is transformed to the API format where each non-empty field becomes
    an ``{"or": [...]}`` filter clause.

    Supports pagination via page_size and page form fields.
    Supports distance-based search via postcode from session.
    """
    session_data = request.session
    filters: Dict[str, Any] = {}

    _hydrate_session_from_user_filter(request)

    user = request.user
    profile = (
        getattr(user, "profile", None)
        if getattr(user, "is_authenticated", False)
        else None
    )
    profile_postcode = (
        (getattr(profile, "postcode", "") or "").strip() if profile else ""
    )
    session_postcode = (
        session_data.get(SESSION_KEY_DETAILS_POSTCODE, "") or ""
    ).strip()

    # If the user has a profile postcode and it differs, update session + persisted filter
    if profile_postcode and profile_postcode != session_postcode:
        session_data[SESSION_KEY_DETAILS_POSTCODE] = profile_postcode
        _persist_to_user_filter(user, SESSION_KEY_DETAILS_POSTCODE, profile_postcode)
        session_data.modified = True

    # Get postcode from session
    postcode = session_data.get(SESSION_KEY_DETAILS_POSTCODE, "")

    # Handle pagination and distance parameters
    if request.method == "POST":
        # Get page_size from POST, store in session
        try:
            page_size = int(
                request.POST.get("page_size")
                or session_data.get("listing_page_size")
                or DEFAULT_PAGE_SIZE
            )
            if page_size not in PAGE_SIZE_OPTIONS:
                page_size = DEFAULT_PAGE_SIZE
        except (ValueError, TypeError):
            page_size = DEFAULT_PAGE_SIZE
        session_data["listing_page_size"] = page_size

        # Get page from POST
        try:
            current_page = int(request.POST.get("page") or 1)
            if current_page < 1:
                current_page = 1
        except (ValueError, TypeError):
            current_page = 1

        # Get distance from POST, store in session
        try:
            distance = int(
                request.POST.get("distance")
                or session_data.get("listing_distance")
                or DEFAULT_DISTANCE
            )
            if distance not in DISTANCE_OPTIONS:
                distance = DEFAULT_DISTANCE
        except (ValueError, TypeError):
            distance = DEFAULT_DISTANCE
        session_data["listing_distance"] = distance
    else:
        # GET request - use session values or defaults
        page_size = session_data.get("listing_page_size", DEFAULT_PAGE_SIZE)
        current_page = 1
        distance = session_data.get("listing_distance", DEFAULT_DISTANCE)

    offset = (current_page - 1) * page_size

    if request.method == "POST":
        for field in FILTER_FIELDS:
            values = _clean_checkbox_list(field, request)

            if values:
                filters[field] = values
                session_data[field] = values
                _persist_to_user_filter(request.user, field, values)
            else:
                filters.pop(field, None)
                session_data.pop(field, None)
                _persist_to_user_filter(request.user, field, None)
    else:
        for field in FILTER_FIELDS:
            value = session_data.get(field)
            if not value:
                continue

            if isinstance(value, list):
                filters[field] = value
            else:
                filters[field] = [value]
                session_data[field] = filters[field]

    payload = _transform_to_filter_format(filters)
    # Add pagination parameters to payload
    payload["limit"] = page_size
    payload["offset"] = offset

    # Add postcode and distance to payload if postcode is available
    if postcode:
        payload["postcode"] = postcode
        payload["distance"] = distance

    # Include activity attributes for relevance ranking (from QuestionnaireResponse)
    user_activity_attributes = []
    if request.user.is_authenticated:
        from htsh.models import QuestionnaireResponse
        try:
            qr = QuestionnaireResponse.objects.get(user=request.user)
            user_activity_attributes = qr.activity_attributes or []
        except QuestionnaireResponse.DoesNotExist:
            pass
    if user_activity_attributes:
        payload["activity_attributes"] = user_activity_attributes

    api_url = _build_internal_api_url(reverse("v3:service-search"))

    results: Dict[str, Any] = {"total": 0, "results": []}
    api_error: str | None = None

    try:
        resp = requests.post(api_url, json=payload, timeout=SERVICE_SEARCH_TIMEOUT)
        resp.raise_for_status()
    except requests.HTTPError as exc:
        api_error = f"HTTP {getattr(resp, 'status_code', '?')}"
        logger.error(
            "Service search API HTTPError: %s, status=%s, body=%s",
            exc,
            getattr(resp, "status_code", None),
            getattr(resp, "text", None),
        )
    except requests.RequestException as exc:
        api_error = str(exc)
        logger.exception("Service search API RequestException")
    else:
        try:
            results = resp.json()
        except (ValueError, JSONDecodeError):
            api_error = "Invalid response from service search API"
            logger.exception("Service search API JSON decode error")

    # Calculate pagination info
    total_results = results.get("total", 0)
    total_pages = (
        (total_results + page_size - 1) // page_size if total_results > 0 else 1
    )

    # Ensure current_page doesn't exceed total_pages
    if current_page > total_pages:
        current_page = total_pages

    # Build pagination context
    pagination = {
        "current_page": current_page,
        "page_size": page_size,
        "page_size_options": PAGE_SIZE_OPTIONS,
        "total_pages": total_pages,
        "total_results": total_results,
        "has_previous": current_page > 1,
        "has_next": current_page < total_pages,
        "previous_page": current_page - 1 if current_page > 1 else None,
        "next_page": current_page + 1 if current_page < total_pages else None,
        "page_range": _get_page_range(current_page, total_pages),
        "showing_from": offset + 1 if total_results > 0 else 0,
        "showing_to": min(offset + page_size, total_results),
    }

    # Favourite state for star icons
    favourite_ids = set()
    if request.user.is_authenticated:
        from htsh.models import FavouriteService
        favourite_ids = set(
            FavouriteService.objects.filter(user=request.user)
            .values_list("service_id", flat=True)
        )
    else:
        favourite_ids = _get_anonymous_favourite_ids(request.session)

    return render(
        request,
        "web/pages/listing.jinja",
        {
            "results": results,
            "data": session_data,
            "api_error": api_error,
            "pagination": pagination,
            "postcode": postcode,
            "distance": distance,
            "distance_options": DISTANCE_OPTIONS,
            "favourite_ids": favourite_ids,
        },
    )


def _get_page_range(current_page: int, total_pages: int, window: int = 2) -> List[int]:
    """Return a list of page numbers to display in pagination.

    Shows pages around current page within the window, always including
    first and last pages. Returns a list where -1 represents an ellipsis.
    """
    if total_pages <= 1:
        return [1] if total_pages == 1 else []

    pages = []

    # Always include page 1
    pages.append(1)

    # Calculate the range around current page
    start = max(2, current_page - window)
    end = min(total_pages - 1, current_page + window)

    # Add ellipsis after page 1 if needed
    if start > 2:
        pages.append(-1)  # -1 represents ellipsis

    # Add pages in the window
    for p in range(start, end + 1):
        pages.append(p)

    # Add ellipsis before last page if needed
    if end < total_pages - 1:
        pages.append(-1)

    # Always include last page (if not already included)
    if total_pages > 1:
        pages.append(total_pages)

    return pages


def detail(request: HttpRequest, service_id: int) -> HttpResponse:
    """Show a single service's details, fetched from the API."""
    if (
        request.method == "POST"
        and not request.user.is_authenticated
        and request.session.get("campaign_code")
        and request.POST.get("action") == "create_account"
    ):
        request.session["account_prompt_service_id"] = service_id
        request.session.modified = True
        return redirect("htsh:disclaimer")

    api_url = _build_internal_api_url(
        reverse("v3:service-detail", kwargs={"id": service_id})
    )

    try:
        resp = requests.get(api_url, timeout=SERVICE_DETAIL_TIMEOUT)
        resp.raise_for_status()
        service = resp.json()
    except (requests.RequestException, ValueError, JSONDecodeError):
        logger.exception("Service detail API error")
        raise Http404("Service not found")

    # Favourite state for star icon
    is_favourited = False
    if request.user.is_authenticated:
        from htsh.models import FavouriteService
        is_favourited = FavouriteService.objects.filter(
            user=request.user, service_id=service_id
        ).exists()
    else:
        is_favourited = service_id in _get_anonymous_favourite_ids(request.session)

    return render(
        request,
        "web/pages/detail.jinja",
        {"service": service, "data": request.session, "is_favourited": is_favourited},
    )


@require_POST
def toggle_favourite(request: HttpRequest, service_id: int) -> HttpResponse:
    """Toggle a service in the user's favourites. POST only, redirects back."""
    if not request.user.is_authenticated:
        if not request.session.get("campaign_code"):
            return redirect("landing")

        anonymous_favourites = _get_anonymous_favourite_ids(request.session)
        if service_id in anonymous_favourites:
            anonymous_favourites.remove(service_id)
        else:
            anonymous_favourites.add(service_id)
        _set_anonymous_favourite_ids(request.session, anonymous_favourites)

        referer = request.META.get("HTTP_REFERER", "")
        if referer and request.get_host() in referer:
            return redirect(referer)
        return redirect(reverse("listing"))

    from htsh.models import FavouriteService

    obj, created = FavouriteService.objects.get_or_create(
        user=request.user, service_id=service_id
    )
    if not created:
        obj.delete()

    # Redirect to referer if same host, otherwise listing
    referer = request.META.get("HTTP_REFERER", "")
    if referer and request.get_host() in referer:
        return redirect(referer)
    return redirect(reverse("listing"))


def favourites_list(request: HttpRequest) -> HttpResponse:
    """Show the user's saved (favourited) services as cards."""
    from api.models_v3 import V3_Service
    from api.v3.serializers import V3_ServiceSummarySerializer

    if request.user.is_authenticated:
        from htsh.models import FavouriteService

        service_ids = list(
            FavouriteService.objects.filter(user=request.user)
            .values_list("service_id", flat=True)
        )
    else:
        service_ids = sorted(_get_anonymous_favourite_ids(request.session))

    services = V3_Service.objects.filter(id__in=service_ids).select_related("service_type")
    serialized = V3_ServiceSummarySerializer(services, many=True).data

    return render(
        request,
        "web/pages/favourites.jinja",
        {"services": serialized, "data": request.session},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_internal_api_url(path: str) -> str:
    base_url = settings.SERVICE_API_BASE_URL
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base_url.rstrip('/')}{path}"

def _validate_postcode(postcode: str) -> Dict[str, Any]:
    """Validate a postcode locally and against api.postcodes.io.

    Returns a dict with:

    * ``isValid`` (bool)
    * ``error`` (one of: "empty", "format", "api", "invalid")
    """
    if not postcode or not postcode.strip():
        return {"isValid": False, "error": "empty"}

    trimmed = postcode.strip()
    if not POSTCODE_REGEX.match(trimmed):
        return {"isValid": False, "error": "format"}

    try:
        resp = requests.get(
            POSTCODE_API_TEMPLATE.format(postcode=trimmed),
            timeout=POSTCODE_API_TIMEOUT,
        )
        if not resp.ok:
            return {"isValid": False, "error": "api"}

        try:
            data = resp.json()
        except (ValueError, JSONDecodeError):
            logger.exception("Postcode API JSON decode error")
            return {"isValid": False, "error": "api"}

        if data.get("result") is True:
            return {"isValid": True, "error": None}

        return {"isValid": False, "error": "invalid"}
    except requests.RequestException:
        logger.exception("Postcode validation API error")
        return {"isValid": False, "error": "api"}


def _clean_checkbox_list(field_name: str, request: HttpRequest) -> List[str]:
    """Return a cleaned list of checkbox values for ``field_name``.

    Removes empty values and the special ``_unchecked`` value used by the
    frontend.
    """
    values = request.POST.getlist(field_name)
    return [v for v in values if v and v not in [CHECKBOX_UNCHECKED_VALUE, ""]]


def _transform_to_filter_format(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Transform flat filters dict into the API's OR-based filter format."""
    filter_list: List[Dict[str, Any]] = []

    for _, value in filters.items():
        if isinstance(value, list):
            cleaned = [v for v in value if v and v != DONT_MIND_VALUE]
            if cleaned:
                filter_list.append({"or": cleaned})

        elif isinstance(value, str):
            v = value.strip()
            if v and v != DONT_MIND_VALUE:
                filter_list.append({"or": [v]})

    return {"filter": filter_list}


def _is_valid_email(email: str) -> bool:
    """Return True if the email looks syntactically valid."""
    if not email:
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


def _is_valid_mobile(mobile: str) -> bool:
    """Return True if the mobile number looks plausibly valid."""
    if not mobile:
        return False
    return bool(MOBILE_REGEX.match(mobile.strip()))


def success(request: HttpRequest) -> HttpResponse:
    """Show a simple success page."""
    return render(
        request,
        "web/pages/success.jinja",
    )
