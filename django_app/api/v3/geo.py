"""
Geospatial utilities for the V3 service catalogue API.

This module provides shared postcode and distance helpers used across
serializers and views, including:

    - Postcode normalisation and validation via UK_POSTCODE_REGEX.
    - resolve_centre_and_radius():
        Converts postcode + distance (miles) into (lat, lon, radius_km),
        applying defaults, clamping, and geocoding.
    - haversine_km():
        Calculates great-circle distance between two (lat, lon) points.

These helpers centralise all distance-related logic for the V3 API and are
used by both V3 serializers and V3 views.
"""

import math
import re
from api.v3.nominatim import nominatim_geocode
from .constants import (
    DEFAULT_DISTANCE_MILES,
    MIN_DISTANCE_MILES,
    MAX_DISTANCE_MILES,
)

UK_POSTCODE_REGEX = re.compile(
    r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$",
    re.IGNORECASE,
)

def geocode_postcode(postcode: str):
    return nominatim_geocode(postcode)
    
def resolve_centre_and_radius(raw_postcode, raw_distance):
    """
    Shared helper to resolve centre (lat, lon) and radius (km) from a postcode
    and distance (in miles).

    - `raw_postcode` is any string-like postcode value (or None/"").
    - `raw_distance` can be None, "", a number, or a numeric string.

    Returns (lat, lon, radius_km), or (None, None, None) if inputs are invalid.
    """
    if not raw_postcode:
        return None, None, None

    # Normalise and validate postcode
    postcode = re.sub(r"\s+", " ", str(raw_postcode).strip().upper())
    if not UK_POSTCODE_REGEX.match(postcode):
        return None, None, None

    # Work out distance in miles, applying defaults and clamping
    if raw_distance in (None, ""):
        distance_miles = DEFAULT_DISTANCE_MILES
    else:
        try:
            distance_miles = float(raw_distance)
        except (TypeError, ValueError):
            return None, None, None

    if distance_miles < MIN_DISTANCE_MILES:
        distance_miles = MIN_DISTANCE_MILES
    elif distance_miles > MAX_DISTANCE_MILES:
        distance_miles = MAX_DISTANCE_MILES

    # Convert miles → km
    radius_km = distance_miles * 1.60934

    lat, lon = geocode_postcode(postcode)
    if lat is None or lon is None:
        return None, None, None

    return lat, lon, radius_km
    
def haversine_km(lat1, lon1, lat2, lon2):
    """
    Great-circle distance between two (lat, lon) points in kilometres.
    """
    rlat1 = math.radians(lat1)
    rlon1 = math.radians(lon1)
    rlat2 = math.radians(lat2)
    rlon2 = math.radians(lon2)

    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    earth_radius_km = 6371.0
    return earth_radius_km * c
