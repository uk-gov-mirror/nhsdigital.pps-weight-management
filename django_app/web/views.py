"""
Public web views for the weight management journey.

The journey is a multi-step form stored in the session. Rough order:

1. start                - flush session and show the start page
2. consent_to_pilot     - pilot consent
3. consent_to_ur        - user research consent
4. details_name         - collect participant name
5. details_postcode     - validate postcode via api.postcodes.io
6. details_contact_details
7. goals, barriers      - goals and barriers
8. preference_*         - preferences (who with / timetable / channel)
9. listing              - show matching services from the API
10. detail              - show a single service from the API

All state is stored in request.session; the API is called at the listing/detail
steps. Templates live under ``templates/jinja2/web/pages`` and are referenced
as ``web/pages/<name>.jinja``.
"""

import logging
import re
from json import JSONDecodeError
from typing import Any, Dict, List

import requests
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POSTCODE_REGEX = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$", re.I)
EMAIL_REGEX    = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MOBILE_REGEX   = re.compile(r"^\+?[0-9][0-9\s\-]{7,}$")

# Pagination
PAGE_SIZE_OPTIONS = [5, 10, 15, 20]
DEFAULT_PAGE_SIZE = 10

# Search distance (miles)
DISTANCE_OPTIONS = [5, 10, 15]
DEFAULT_DISTANCE = 5

CHECKBOX_UNCHECKED_VALUE     = "_unchecked"
DONT_MIND_VALUE              = "dont_mind"

SESSION_KEY_DETAILS_POSTCODE = "details-postcode"
SESSION_KEY_CONTACT          = "contact"
SESSION_KEY_EMAIL            = "emailInput"
SESSION_KEY_MOBILE           = "mobileInput"

POSTCODE_API_TEMPLATE        = "https://api.postcodes.io/postcodes/{postcode}/validate"
POSTCODE_API_TIMEOUT         = 5

SERVICE_SEARCH_TIMEOUT       = 10
SERVICE_DETAIL_TIMEOUT       = 10

FILTER_FIELDS: List[str] = [
    "goals",
    "cost",
    "timetable",
    "location",
    "taught",
    "who_with",
    "channel",
]


PERSISTED_SESSION_KEYS: List[str] = [
    # Wizard pages
    "goals",
    "barriers",
    "who_with",
    "timetable",
    "channel",
    SESSION_KEY_DETAILS_POSTCODE,
    # Listing filters (set/edited on listing page)
    "cost",
    "location",
    "taught",
]


def _get_or_create_user_filter(user):
    """Return the user's persisted filter record (creating if needed)."""
    from pilot_access.models import UserFilter

    uf, _ = UserFilter.objects.get_or_create(user=user)
    return uf


def _persist_to_user_filter(user, key: str, value: Any) -> None:
    """Persist a session key/value to the user's filter record."""
    if not getattr(user, "is_authenticated", False):
        return
    uf = _get_or_create_user_filter(user)
    uf.set_value(key, value)
    uf.save(update_fields=["data", "updated_at"])


def _hydrate_session_from_user_filter(request: HttpRequest) -> None:
    """Load persisted answers into the session if present."""
    user = request.user
    if not getattr(user, "is_authenticated", False):
        return

    from pilot_access.models import UserFilter

    try:
        uf = UserFilter.objects.get(user=user)
    except UserFilter.DoesNotExist:
        return

    data = uf.data or {}
    changed = False
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
    from pilot_access.models import UserFilter
    
    # request.session.flush()
    start_href = "details-contact-details"
    
    # If user has already been through the wizard (has UserFilter data), go straight to listings
    if request.user.is_authenticated:
        try:
            uf = UserFilter.objects.get(user=request.user)
            if uf.data:
                start_href = "listing"
        except UserFilter.DoesNotExist:
            pass
    
    # Legacy check for magic link flow
    if request.session.get("entry_flow") == "magiclink":
        start_href = "listing"

    return render(request, "web/pages/index.jinja", {"data": request.session, "start_href": start_href})

# ---------------------------------------------------------------------------
# Journey: personal details
# ---------------------------------------------------------------------------

def details_contact_details(request: HttpRequest) -> HttpResponse:
    """Collect contact details and a preferred contact method.

    This page mirrors the account page: email + phone text inputs, and a single
    preferred contact method (email or text message).
    """
    from django.contrib.auth import get_user_model
    from pilot_access.models import PilotProfile

    user = request.user
    profile = getattr(user, "pilot_profile", None)

    # Initial values come from the profile (and Django user for email)
    initial = {
        "email": getattr(user, "email", "") or "",
        "phone": getattr(profile, "phone", "") if profile else "",
        "preferred_contact_method": getattr(profile, "preferred_contact_method", "") if profile else "",
    }

    if not initial["preferred_contact_method"]:
        initial["preferred_contact_method"] = PilotProfile.CONTACT_EMAIL

    errors: Dict[str, Any] = {"list": []}
    values = dict(initial)

    if request.method == "POST":
        values["email"] = (request.POST.get("email") or "").strip()
        values["phone"] = (request.POST.get("phone") or "").strip()
        values["preferred_contact_method"] = (request.POST.get("preferred_contact_method") or "").strip()

        pref = values["preferred_contact_method"]

        if pref not in (PilotProfile.CONTACT_EMAIL, PilotProfile.CONTACT_SMS):
            errors["preferred_contact_method"] = True
            errors["list"].append({"text": "Please choose a preferred contact method", "href": "#preferredContact"})

        # Validate per preference
        if pref == PilotProfile.CONTACT_EMAIL:
            if not _is_valid_email(values["email"]):
                errors["email"] = True
                errors["list"].append({"text": "Please enter a valid email address", "href": "#emailInput"})
        elif pref == PilotProfile.CONTACT_SMS:
            if not _is_valid_mobile(values["phone"]):
                errors["phone"] = True
                errors["list"].append({"text": "Please enter a valid mobile phone number", "href": "#phoneInput"})

        # If user changed their email, enforce uniqueness
        if not errors.get("email") and values["email"]:
            User = get_user_model()
            if User.objects.filter(email__iexact=values["email"]).exclude(pk=user.pk).exists():
                errors["email"] = True
                errors["list"].append({"text": "That email address is already in use", "href": "#emailInput"})

        # If user entered/changed their phone, enforce uniqueness against PilotProfile
        if not errors.get("phone") and values["phone"]:
            qs = PilotProfile.objects.filter(phone=values["phone"])
            if profile is not None and profile.pk is not None:
                qs = qs.exclude(pk=profile.pk)
            if qs.exists():
                errors["phone"] = True
                errors["list"].append({"text": "That mobile number is already in use", "href": "#phoneInput"})

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

            return redirect("details_postcode")

    return render(
        request,
        "web/pages/details-contact-details.jinja",
        {"data": values, "errors": errors},
    )


def details_postcode(request: HttpRequest) -> HttpResponse:
    """Collect and validate the participant's postcode.

    Validates locally (UK postcode format) and then via api.postcodes.io.
    On success, stores the postcode in the session and (if available) saves it
    to the authenticated user's PilotProfile.
    """
    user = request.user
    profile = getattr(user, "pilot_profile", None)

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

        return redirect("goals")

    return render(
        request,
        "web/pages/details-postcode.jinja",
        {"data": request.session},
    )

# ---------------------------------------------------------------------------
# Journey: goals and barriers
# ---------------------------------------------------------------------------

def goals(request: HttpRequest) -> HttpResponse:
    """Collect goals as a checkbox list."""
    if request.method == "POST":
        values = _clean_checkbox_list("goals", request)
        if not values:
            return render(
                request,
                "web/pages/goals.jinja",
                {"error": True, "data": request.session},
            )
        request.session["goals"] = values
        _persist_to_user_filter(request.user, "goals", values)
        return redirect("barriers")

    return render(
        request,
        "web/pages/goals.jinja",
        {"data": request.session},
    )


def barriers(request: HttpRequest) -> HttpResponse:
    """Collect barriers as a checkbox list."""
    if request.method == "POST":
        values = _clean_checkbox_list("barriers", request)
        if not values:
            return render(
                request,
                "web/pages/barriers.jinja",
                {"error": True, "data": request.session},
            )
        request.session["barriers"] = values
        _persist_to_user_filter(request.user, "barriers", values)
        return redirect("preference_who_with")

    return render(
        request,
        "web/pages/barriers.jinja",
        {"data": request.session},
    )


# ---------------------------------------------------------------------------
# Journey: preferences (who with / timetable / channel)
# ---------------------------------------------------------------------------

def preference_who_with(request: HttpRequest) -> HttpResponse:
    """Collect preference for who the participant wants to attend with."""
    if request.method == "POST":
        value = request.POST.get("who_with")
        if value in (None, "", CHECKBOX_UNCHECKED_VALUE):
            return render(
                request,
                "web/pages/preference-who-with.jinja",
                {"error": True, "data": request.session},
            )
        request.session["who_with"] = value
        _persist_to_user_filter(request.user, "who_with", value)
        return redirect("preference_timetable")

    return render(
        request,
        "web/pages/preference-who-with.jinja",
        {"data": request.session},
    )


def preference_timetable(request: HttpRequest) -> HttpResponse:
    """Collect timetable preferences as a checkbox list."""
    if request.method == "POST":
        value = request.POST.get("timetable")
        if value in (None, "", CHECKBOX_UNCHECKED_VALUE):
            return render(
                request,
                "web/pages/preference-timetable.jinja",
                {"error": True, "data": request.session},
            )
        request.session["timetable"] = value
        _persist_to_user_filter(request.user, "timetable", value)
        return redirect("preference_channel")

    return render(
        request,
        "web/pages/preference-timetable.jinja",
        {"data": request.session},
    )


def preference_channel(request: HttpRequest) -> HttpResponse:
    """Collect preferred contact channel."""
    if request.method == "POST":
        value = request.POST.get("channel")
        if value in (None, "", CHECKBOX_UNCHECKED_VALUE):
            return render(
                request,
                "web/pages/preference-channel.jinja",
                {"error": True, "data": request.session},
            )
        request.session["channel"] = value
        _persist_to_user_filter(request.user, "channel", value)
        return redirect("listing")

    return render(
        request,
        "web/pages/preference-channel.jinja",
        {"data": request.session},
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
    profile = getattr(user, "pilot_profile", None) if getattr(user, "is_authenticated", False) else None
    profile_postcode = (getattr(profile, "postcode", "") or "").strip() if profile else ""
    session_postcode = (session_data.get(SESSION_KEY_DETAILS_POSTCODE, "") or "").strip()

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
            page_size = int(request.POST.get("page_size") or session_data.get("listing_page_size") or DEFAULT_PAGE_SIZE)
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
            distance = int(request.POST.get("distance") or session_data.get("listing_distance") or DEFAULT_DISTANCE)
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
    
    api_url = request.build_absolute_uri(reverse("v3:service-search"))

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
    total_pages = (total_results + page_size - 1) // page_size if total_results > 0 else 1
    
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
    api_url = request.build_absolute_uri(
        reverse("v3:service-detail", kwargs={"id": service_id})
    )

    try:
        resp = requests.get(api_url, timeout=SERVICE_DETAIL_TIMEOUT)
        resp.raise_for_status()
        service = resp.json()
    except (requests.RequestException, ValueError, JSONDecodeError):
        logger.exception("Service detail API error")
        raise Http404("Service not found")

    return render(
        request,
        "web/pages/detail.jinja",
        {"service": service, "data": request.session},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    return [
        v
        for v in values
        if v and v not in [CHECKBOX_UNCHECKED_VALUE, ""]
    ]


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
    