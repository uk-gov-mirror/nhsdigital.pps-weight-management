from django.shortcuts import render, redirect
from django.http import Http404
from django.urls import reverse
import re
import requests
import logging

POSTCODE_REGEX = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$", re.I)

logger = logging.getLogger(__name__)

FILTER_FIELDS = [
    "goals",
    "cost",
    "timetable",
    "location",
    "taught",
    "who_with",
    "channel",
]

def start(request):
    request.session.flush()
    return render(request, 'web/index.jinja', {"data": request.session})

def consent_to_pilot(request):
    if request.method == "POST":
        value = request.POST.get('consent-to-pilot')
        if value in (None, '', '_unchecked'):
            return render(request, 'web/consent-to-pilot.jinja', {
                "error": True,
                "data": request.session,
            })
        request.session['consent-to-pilot'] = value
        if value == 'yes':
            return redirect('consent_to_ur')
        # Prototype sends 'oh dear' on 'no'; raise 404 here
        raise Http404("Pilot consent declined")
    return render(request, 'web/consent-to-pilot.jinja', {"data": request.session})

def consent_to_ur(request):
    if request.method == "POST":
        value = request.POST.get('consent-to-ur')
        if value in (None, '', '_unchecked'):
            return render(request, 'web/consent-to-ur.jinja', {
                "error": True,
                "data": request.session,
            })
        request.session['consent-to-ur'] = value
        if value == 'yes':
            return redirect('details_name')
        raise Http404("User research consent declined")
    return render(request, 'web/consent-to-ur.jinja', {"data": request.session})

def details_name(request):
    if request.method == "POST":
        value = (request.POST.get('details-name') or "").strip()
        if not value:
            return render(request, 'web/details-name.jinja', {
                "error": True,
                "data": request.session,
            })
        request.session['details-name'] = value
        return redirect('details_postcode')
    return render(request, 'web/details-name.jinja', {"data": request.session})

def details_postcode(request):
    if request.method == "POST":
        postcode = (request.POST.get('details-postcode') or "").strip()
        validation = _validate_postcode(postcode)

        if not validation["isValid"]:
            return render(request, 'web/details-postcode.jinja', {
                "error": True,
                "data": request.session,
            })

        request.session['details-postcode'] = postcode
        return redirect('details_contact_details')
    return render(request, 'web/details-postcode.jinja', {"data": request.session})

def details_contact_details(request):
    if request.method == "POST":
        contact = request.POST.getlist('contact')

        contact = [c for c in contact if c and c != '_unchecked']

        errors = {"list": []}
        values = {
            "contact": contact,
            "emailInput": request.POST.get('emailInput', ''),
            "mobileInput": request.POST.get('mobileInput', ''),
        }

        if not contact:
            errors["contact"] = True
            errors["list"].append({
                "text": "Please choose an option",
                "href": "#contact",
            })

        if 'email' in contact:
            email_value = (request.POST.get('emailInput') or "").strip()
            if email_value == "":
                errors["email"] = True
                errors["list"].append({
                    "text": "Please enter a valid email address",
                    "href": "#emailInput",
                })

        if 'text' in contact:
            mobile_value = (request.POST.get('mobileInput') or "").strip()
            if mobile_value == "":
                errors["mobile"] = True
                errors["list"].append({
                    "text": "Please enter a valid mobile phone number",
                    "href": "#mobileInput",
                })

        if errors["list"]:
            return render(request, 'web/details-contact-details.jinja', {
                "errors": errors,
                "values": values,
                "data": request.session,
            })

        request.session['contact'] = contact
        request.session['emailInput'] = values["emailInput"]
        request.session['mobileInput'] = values["mobileInput"]

        return redirect('goals')

    return render(request, 'web/details-contact-details.jinja', { "data": request.session })

def goals(request):
    if request.method == "POST":
        values = _clean_checkbox_list('goals', request)
        if not values:
            return render(request, 'web/goals.jinja', {
                "error": True,
                "data": request.session,
            })
        request.session['goals'] = values
        return redirect('barriers')
    return render(request, 'web/goals.jinja', {"data": request.session})

def barriers(request):
    if request.method == "POST":
        values = _clean_checkbox_list('barriers', request)
        if not values:
            return render(request, 'web/barriers.jinja', {
                "error": True,
                "data": request.session,
            })
        request.session['barriers'] = values
        return redirect('preference_who_with')
    return render(request, 'web/barriers.jinja', {"data": request.session})

def preference_who_with(request):
    if request.method == "POST":
        value = request.POST.get('who_with')
        if value in (None, '', '_unchecked'):
            return render(request, 'web/preference-who-with.jinja', {
                "error": True,
                "data": request.session,
            })
        request.session['who_with'] = value
        return redirect('preference_timetable')
    return render(request, 'web/preference-who-with.jinja', {"data": request.session})

def preference_timetable(request):
    if request.method == "POST":
        value = request.POST.get('timetable')
        if value in (None, '', '_unchecked'):
            return render(request, 'web/preference-timetable.jinja', {
                "error": True,
                "data": request.session,
            })
        request.session['timetable'] = value
        return redirect('preference_channel')
    return render(request, 'web/preference-timetable.jinja', {"data": request.session})

def preference_channel(request):
    if request.method == "POST":
        value = request.POST.get('channel')
        if value in (None, '', '_unchecked'):
            return render(request, 'web/preference-channel.jinja', {
                "error": True,
                "data": request.session,
            })
        request.session['channel'] = value
        return redirect('listing')
    return render(request, 'web/preference-channel.jinja', {"data": request.session})

def listing(request):
    session_data = request.session
    filters = {}

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
    
    logger.exception(payload);
    api_url = request.build_absolute_uri(reverse("v2:service-search"))

    results = []
    api_error = None
    try:
        resp = requests.post(
            api_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        
    except requests.HTTPError as e:
        api_error = f"HTTP {resp.status_code}"
        logger.error(
            "Service search API HTTPError: %s, status=%s, body=%s",
            e, getattr(resp, "status_code", None), getattr(resp, "text", None),
        )
        
    except requests.RequestException as e:
        api_error = str(e)
        logger.exception("Service search API RequestException")

    return render(request, "web/listing.jinja", {
        "results": results,
        "data": session_data,
        "api_error": api_error,
    })

def detail(request, service_id: int):
    api_url = request.build_absolute_uri(
        reverse('v2:service-detail', kwargs={"id": service_id})
    )

    try:
        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()
        service = resp.json()
    except requests.RequestException:
        raise Http404("Service not found")

    return render(request, 'web/detail.jinja', {
        "service": service,
        "data": request.session,
    })

def _validate_postcode(postcode: str) -> dict:
    if not postcode or not postcode.strip():
        return {"isValid": False, "error": "empty"}

    trimmed = postcode.strip()
    if not POSTCODE_REGEX.match(trimmed):
        return {"isValid": False, "error": "format"}

    try:
        resp = requests.get(
            f"https://api.postcodes.io/postcodes/{trimmed}/validate",
            timeout=5
        )
        if not resp.ok:
            return {"isValid": False, "error": "api"}
        data = resp.json()
        if data.get("result") is True:
            return {"isValid": True}
        return {"isValid": False, "error": "invalid"}
    except Exception:
        return {"isValid": False, "error": "api"}

def _clean_checkbox_list(field_name: str, request):
    values = request.POST.getlist(field_name)
    values = [
        v for v in values
        if v and v not in ['_unchecked', '']
    ]
    return values

def _transform_to_filter_format(filters: dict) -> dict:
    filter_list = []

    for key, value in filters.items():
        if isinstance(value, list):
            cleaned = [v for v in value if v and v != "dont_mind"]
            if cleaned:
                filter_list.append({"or": cleaned})

        elif isinstance(value, str):
            v = value.strip()
            if v and v != "dont_mind":
                filter_list.append({"or": [v]})

    return {"filter": filter_list}
    