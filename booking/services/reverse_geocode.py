"""Reverse geocoding for seat booking addresses (lat/lng → human-readable text).

Uses Nominatim (OpenStreetMap). Policy: https://operations.osmfoundation.org/policies/nominatim/
Always send a valid User-Agent (see NOMINATIM_USER_AGENT in settings).
"""
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

# Normalized (lowercase, no trailing dot) client placeholders → replace via reverse geocode.
_PLACEHOLDER_ADDRESSES = frozenset(
    {
        'current location',
        'my location',
        'my current location',
    }
)


def needs_reverse_geocode(address):
    """True when stored text is empty or a generic placeholder (case-insensitive)."""
    if address is None:
        return True
    s = str(address).strip().lower().rstrip('.')
    if not s:
        return True
    return s in _PLACEHOLDER_ADDRESSES


def reverse_geocode(lat, lng, timeout=10):
    """
    Return display name from Nominatim, or None on failure / empty result.
    """
    try:
        lat_f = float(lat)
        lng_f = float(lng)
    except (TypeError, ValueError):
        return None

    user_agent = getattr(
        settings,
        'NOMINATIM_USER_AGENT',
        'EV-Yatayat-Sewa/1.0 (+https://github.com/)',
    )
    params = urllib.parse.urlencode(
        {
            'lat': lat_f,
            'lon': lng_f,
            'format': 'json',
            'addressdetails': '1',
        }
    )
    url = f'https://nominatim.openstreetmap.org/reverse?{params}'
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': user_agent,
            'Accept': 'application/json',
            'Accept-Language': 'en',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
    except (urllib.error.URLError, OSError, TimeoutError, ValueError) as e:
        logger.warning('reverse_geocode request failed: %s', e)
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    display = data.get('display_name')
    if display and isinstance(display, str):
        out = display.strip()
        if out:
            return out
    return None


def resolve_address_from_coords(address, lat, lng):
    """
    If address is empty/placeholder, try reverse geocode; otherwise return address unchanged.
    On geocode failure, returns original address (may still be placeholder).
    """
    if not needs_reverse_geocode(address):
        return (address or '').strip()
    resolved = reverse_geocode(lat, lng)
    if resolved:
        return resolved
    return (address or '').strip()
