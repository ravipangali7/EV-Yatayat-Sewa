"""Notify Node server when seat bookings are created (for real-time driver UI)."""
import logging
from django.conf import settings
import requests

logger = logging.getLogger(__name__)


def notify_node_seat_booked(trip_id, vehicle_id, seats):
    """
    POST to Node /internal/seat-booked so driver receives seat_booked over socket.
    seats: list of dicts with vehicle_seat_id, side, number; optionally user_name, from_address, to_name.
    Fire-and-forget; do not raise or delay the request on failure.
    """
    base_url = getattr(settings, 'NODE_BASE_URL', '') or ''
    if not base_url:
        return
    if not base_url.startswith(('http://', 'https://')):
        base_url = 'https://' + base_url
    url = f'{base_url}/internal/seat-booked'
    headers = {'Content-Type': 'application/json'}
    seat_list = []
    for s in seats:
        item = {
            'vehicle_seat_id': str(s.get('vehicle_seat_id')),
            'side': s.get('side', ''),
            'number': s.get('number', 0),
        }
        if s.get('user_name') is not None:
            item['user_name'] = str(s['user_name'])
        if s.get('from_address') is not None:
            item['from_address'] = str(s['from_address'])
        if s.get('to_name') is not None:
            item['to_name'] = str(s['to_name'])
        seat_list.append(item)
    payload = {
        'trip_id': str(trip_id),
        'vehicle_id': str(vehicle_id),
        'seats': seat_list,
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=3)
        if resp.status_code >= 400:
            logger.warning('Node seat-booked webhook failed: %s %s', resp.status_code, resp.text[:200])
    except requests.exceptions.RequestException as e:
        logger.warning('Node seat-booked webhook error: %s', e)
