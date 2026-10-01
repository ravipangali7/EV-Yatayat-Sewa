"""Segment fares for scheduled vehicle tickets.

Full route (first place to last place in the schedule direction) uses the
schedule price. Any shorter segment uses distance along the route stops
times price per km (schedule rate, else super-setting default, else per km charge).
"""
import math
from decimal import Decimal, ROUND_HALF_UP

from .route_order import get_route_ordered_points, get_route_place_order


def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371.0
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    d_phi = math.radians(float(lat2) - float(lat1))
    d_lambda = math.radians(float(lon2) - float(lon1))
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def get_default_price_per_km():
    from core.models import SuperSetting

    setting = SuperSetting.objects.order_by('-id').first()
    if not setting:
        return Decimal('0')
    if setting.default_price_per_km is not None:
        return setting.default_price_per_km
    return setting.per_km_charge or Decimal('0')


def segment_distance_km(route, reverse, from_place_id, to_place_id):
    """Kilometres along ordered route places from pickup to destination."""
    points = get_route_ordered_points(route, reverse=reverse)
    places = [place for _, place, _ in points]
    ids = [place.id for place in places]
    if from_place_id not in ids or to_place_id not in ids:
        return Decimal('0.00')
    start = ids.index(from_place_id)
    end = ids.index(to_place_id)
    if start >= end:
        return Decimal('0.00')
    total = 0.0
    for index in range(start, end):
        a = places[index]
        b = places[index + 1]
        total += haversine_km(a.latitude, a.longitude, b.latitude, b.longitude)
    return Decimal(str(round(total, 2)))


def quote_segment(schedule, from_place_id=None, to_place_id=None, default_rate=None):
    """Return unit fare for one seat on this pickup → destination."""
    reverse = getattr(schedule, 'reverse_direction', False)
    order_map = get_route_place_order(schedule.route, reverse)
    from_id = int(from_place_id) if from_place_id not in (None, '') else None
    to_id = int(to_place_id) if to_place_id not in (None, '') else None

    is_full = True
    if order_map and from_id in order_map and to_id in order_map:
        is_full = order_map[from_id] == min(order_map.values()) and order_map[to_id] == max(order_map.values())
    elif from_id is not None or to_id is not None:
        is_full = False

    if schedule.price_per_km is not None:
        rate = schedule.price_per_km
    elif default_rate is not None:
        rate = default_rate
    else:
        rate = get_default_price_per_km()

    km = Decimal('0.00')
    if from_id is not None and to_id is not None:
        km = segment_distance_km(schedule.route, reverse, from_id, to_id)

    if is_full:
        unit = Decimal(str(schedule.price))
    else:
        unit = (km * Decimal(str(rate))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return {
        'unit_price': unit,
        'distance_km': km,
        'price_per_km': Decimal(str(rate)),
        'is_full_route': is_full,
    }
