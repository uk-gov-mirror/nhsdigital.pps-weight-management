"""
This module provides a wrapper around the Nominatim API to turn
postcodes into latitude/longitude coordinates.
"""

import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

def nominatim_geocode(postcode: str):
    """
    Calls Nominatim to convert a postcode into (lat, lon).

    Returns:
        (lat, lon) as floats, or (None, None) if no results.
    """

    if not postcode:
        return None, None

    params = {
        "q": postcode,
        "format": "json",
    }

    headers = {
        "User-Agent": "BetterHealthApp/1.0 (jamie.be11@nhs.net)",
        "Accept": "application/json"
    }

    try:
        response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=5)
        response.raise_for_status()

        results = response.json()
        if not results:
            return None, None

        # Nominatim returns lat/lon as strings
        lat = float(results[0].get("lat"))
        lon = float(results[0].get("lon"))
        return lat, lon

    except Exception:
        # Gracefully degrade instead of throwing
        return None, None
