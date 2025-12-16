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

CHECKBOX_UNCHECKED_VALUE     = "_unchecked"
DONT_MIND_VALUE              = "dont_mind"

SESSION_KEY_CONSENT_PILOT    = "consent-to-pilot"
SESSION_KEY_CONSENT_UR       = "consent-to-ur"
SESSION_KEY_DETAILS_NAME     = "details-name"
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


# ---------------------------------------------------------------------------
# Journey: start and consent
# ---------------------------------------------------------------------------

def start(request: HttpRequest) -> HttpResponse:
    """Start the journey by clearing any existing session data."""
    request.session.flush()
    return render(request, "web/pages/index.jinja", {"data": request.session})


def consent_to_pilot(request: HttpRequest) -> HttpResponse:
    """Collect consent to take part in the pilot.

    If consent is not given, respond with 404 (end of journey).
    """
    if request.method == "POST":
        value = request.POST.get(SESSION_KEY_CONSENT_PILOT)
        if value in (None, "", CHECKBOX_UNCHECKED_VALUE):
            return render(
                request,
                "web/pages/consent-to-pilot.jinja",
                {"error": True, "data": request.session},
            )

        request.session[SESSION_KEY_CONSENT_PILOT] = value
        if value == "yes":
            return redirect("consent_to_ur")

        # On 'no' return 404
        raise Http404("Pilot consent declined")

    return render(
        request,
        "web/pages/consent-to-pilot.jinja",
        {"data": request.session},
    )


def consent_to_ur(request: HttpRequest) -> HttpResponse:
    """Collect consent for user research.

    If consent is not given, respond with 404 (end of journey).
    """
    if request.method == "POST":
        value = request.POST.get(SESSION_KEY_CONSENT_UR)
        if value in (None, "", CHECKBOX_UNCHECKED_VALUE):
            return render(
                request,
                "web/pages/consent-to-ur.jinja",
                {"error": True, "data": request.session},
            )

        request.session[SESSION_KEY_CONSENT_UR] = value
        if value == "yes":
            return redirect("details_name")

        # On 'no' return 404
        raise Http404("User research consent declined")

    return render(
        request,
        "web/pages/consent-to-ur.jinja",
        {"data": request.session},
    )


# ---------------------------------------------------------------------------
# Journey: personal details
# ---------------------------------------------------------------------------

def details_name(request: HttpRequest) -> HttpResponse:
    """Collect the participant's name."""
    if request.method == "POST":
        value = (request.POST.get(SESSION_KEY_DETAILS_NAME) or "").strip()
        if not value:
            return render(
                request,
                "web/pages/details-name.jinja",
                {"error": True, "data": request.session},
            )

        request.session[SESSION_KEY_DETAILS_NAME] = value
        return redirect("details_postcode")

    return render(
        request,
        "web/pages/details-name.jinja",
        {"data": request.session},
    )


def details_postcode(request: HttpRequest) -> HttpResponse:
    """Collect and validate the participant's postcode."""
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
        return redirect("details_contact_details")

    return render(
        request,
        "web/pages/details-postcode.jinja",
        {"data": request.session},
    )


def details_contact_details(request: HttpRequest) -> HttpResponse:
    """Collect preferred contact methods and their details.

    Rules:

    * At least one contact method must be selected.
    * If 'email' is selected, a syntactically valid email is required.
    * If 'text' is selected, a plausibly valid mobile number is required.
    * On errors, re-render the form with an error summary and the current values.
    * On success, save values to the session and continue to 'goals'.
    """
    if request.method == "POST":
        contact = request.POST.getlist(SESSION_KEY_CONTACT)
        # Drop unchecked/empty values
        contact = [
            c for c in contact if c and c != CHECKBOX_UNCHECKED_VALUE
        ]

        errors: Dict[str, Any] = {"list": []}
        values: Dict[str, Any] = {
            SESSION_KEY_CONTACT: contact,
            SESSION_KEY_EMAIL  : (request.POST.get(SESSION_KEY_EMAIL , "") or "").strip(),
            SESSION_KEY_MOBILE : (request.POST.get(SESSION_KEY_MOBILE, "") or "").strip(),
        }

        if not contact:
            errors["contact"] = True
            errors["list"].append(
                {"text": "Please choose an option", "href": "#contact"}
            )

        if "email" in contact:
            email_value = values[SESSION_KEY_EMAIL]
            if not _is_valid_email(email_value):
                errors["email"] = True
                errors["list"].append(
                    {"text": "Please enter a valid email address", "href": "#emailInput"}
                )

        if "text" in contact:
            mobile_value = values[SESSION_KEY_MOBILE]
            if not _is_valid_mobile(mobile_value):
                errors["mobile"] = True
                errors["list"].append(
                    {
                        "text": "Please enter a valid mobile phone number",
                        "href": "#mobileInput",
                    }
                )

        if errors["list"]:
            # Merge session data and current form values so the template
            # can re-populate fields with the user's last input.
            data = dict(request.session)
            data.update(values)

            return render(
                request,
                "web/pages/details-contact-details.jinja",
                {"errors": errors, "data": data},
            )

        # Only save to session if everything is valid
        request.session[SESSION_KEY_CONTACT] = contact
        request.session[SESSION_KEY_EMAIL]   = values[SESSION_KEY_EMAIL]
        request.session[SESSION_KEY_MOBILE]  = values[SESSION_KEY_MOBILE]

        return redirect("goals")

    return render(
        request,
        "web/pages/details-contact-details.jinja",
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
    """
    session_data = request.session
    filters: Dict[str, Any] = {}

    if request.method == "POST":
        for field in FILTER_FIELDS:
            values = _clean_checkbox_list(field, request)

            if values:
                filters[field] = values
                session_data[field] = values
            else:
                filters.pop(field, None)
                session_data.pop(field, None)
    else:
        # Rehydrate filters from the session for GET requests
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
    api_url = request.build_absolute_uri(reverse("v3:service-search"))

    results: List[Dict[str, Any]] = []
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
            results = resp.json()  # type: ignore[assignment]
        except (ValueError, JSONDecodeError):
            api_error = "Invalid response from service search API"
            logger.exception("Service search API JSON decode error")

    return render(
        request,
        "web/pages/listing.jinja",
        {"results": results, "data": session_data, "api_error": api_error},
    )


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
