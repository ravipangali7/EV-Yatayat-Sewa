"""Monitoring snapshot API: single endpoint for control room dashboard."""
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Exists, OuterRef, Subquery, Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ..models import (
    Location,
    SeatBooking,
    Trip,
    Vehicle,
    VehicleSchedule,
    VehicleTicketBooking,
)
from core.models import Wallet


def _get_month_bounds(dt):
    """Return (first_day, last_day) of the month for dt.date()."""
    d = dt.date() if hasattr(dt, 'date') else dt
    first = date(d.year, d.month, 1)
    if d.month == 12:
        last = date(d.year, 12, 31)
    else:
        last = date(d.year, d.month + 1, 1) - timedelta(days=1)
    return first, last


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monitoring_snapshot_view(request):
    """
    GET /api/monitoring/
    Returns a single calculated snapshot: vehicles (with last location, today stats),
    summary KPIs, and heavy dues (drivers with to_pay > 0).
    """
    now = timezone.now()
    today = now.date()
    month_start, month_end = _get_month_bounds(now)

    # --- Vehicles: active only, with related data ---
    vehicles_qs = (
        Vehicle.objects.filter(is_active=True)
        .select_related(
            'active_driver',
            'active_route',
            'active_route__start_point',
            'active_route__end_point',
        )
        .prefetch_related('seats')
    )

    # Annotate with last location (one subquery per field to avoid N+1)
    latest_loc = (
        Location.objects.filter(vehicle_id=OuterRef('pk'))
        .order_by('-created_at')
    )
    vehicles_qs = vehicles_qs.annotate(
        last_lat=Subquery(latest_loc.values('latitude')[:1]),
        last_lng=Subquery(latest_loc.values('longitude')[:1]),
        last_location_at=Subquery(latest_loc.values('created_at')[:1]),
        last_speed=Subquery(latest_loc.values('speed')[:1]),
    )
    has_active_trip = Trip.objects.filter(
        vehicle_id=OuterRef('pk'),
        end_time__isnull=True,
    )
    vehicles_qs = vehicles_qs.annotate(has_active_trip=Exists(has_active_trip))

    vehicles_list = list(vehicles_qs)
    vehicle_ids = [v.id for v in vehicles_list]

    if not vehicle_ids:
        return Response({
            'fetched_at': now.isoformat(),
            'summary': {
                'total_vehicles': 0,
                'on_trip_count': 0,
                'total_seats_booked': 0,
                'total_revenue_today': '0',
            },
            'vehicles': [],
            'heavy_dues': _build_heavy_dues(month_start, month_end),
        }, status=status.HTTP_200_OK)

    # Active trips: vehicle_id -> trip
    active_trips = {
        t.vehicle_id: t
        for t in Trip.objects.filter(
            vehicle_id__in=vehicle_ids,
            end_time__isnull=True,
        ).select_related('vehicle')
    }
    active_trip_ids = list(active_trips.keys())

    # Seats booked per active trip: trip_id -> count
    seats_booked_by_trip = {}
    if active_trip_ids:
        for row in SeatBooking.objects.filter(trip_id__in=active_trip_ids).values('trip_id').annotate(c=Count('id')):
            seats_booked_by_trip[row['trip_id']] = row['c']

    # Today trip count per vehicle
    today_trips_by_vehicle = dict(
        Trip.objects.filter(
            vehicle_id__in=vehicle_ids,
            start_time__date=today,
            start_time__isnull=False,
        )
        .values('vehicle_id')
        .annotate(c=Count('id'))
        .values_list('vehicle_id', 'c')
    )

    # Today seat revenue per vehicle
    today_seat_revenue = dict(
        SeatBooking.objects.filter(
            vehicle_id__in=vehicle_ids,
            check_in_datetime__date=today,
        )
        .values('vehicle_id')
        .annotate(s=Sum('trip_amount'))
        .values_list('vehicle_id', 's')
    )

    # Today ticket revenue per vehicle (via VehicleSchedule)
    today_ticket_revenue = {}
    schedule_ids = list(VehicleSchedule.objects.filter(vehicle_id__in=vehicle_ids).values_list('id', flat=True))
    if schedule_ids:
        for row in (
            VehicleTicketBooking.objects.filter(
                vehicle_schedule_id__in=schedule_ids,
                created_at__date=today,
            )
            .values('vehicle_schedule__vehicle_id')
            .annotate(s=Sum('price'))
            .values_list('vehicle_schedule__vehicle_id', 's')
        ):
            vid, s = row[0], row[1] or Decimal('0')
            today_ticket_revenue[vid] = (today_ticket_revenue.get(vid) or Decimal('0')) + s

    # Build vehicle payloads
    vehicles_payload = []
    total_seats_booked = 0
    total_revenue_today = Decimal('0')
    on_trip_count = 0

    for v in vehicles_list:
        trip = active_trips.get(v.id)
        seats_booked = seats_booked_by_trip.get(trip.id, 0) if trip else 0
        seats_total = v.seats.count() if hasattr(v, 'seats') else 0
        today_trips = today_trips_by_vehicle.get(v.id, 0)
        seat_rev = today_seat_revenue.get(v.id) or Decimal('0')
        ticket_rev = today_ticket_revenue.get(v.id) or Decimal('0')
        rev_today = seat_rev + ticket_rev

        total_seats_booked += seats_booked
        total_revenue_today += rev_today
        if getattr(v, 'has_active_trip', False):
            on_trip_count += 1

        start_point = ''
        end_point = ''
        if v.active_route:
            if v.active_route.start_point:
                start_point = v.active_route.start_point.name or ''
            if v.active_route.end_point:
                end_point = v.active_route.end_point.name or ''

        lat = float(v.last_lat) if v.last_lat is not None else None
        lng = float(v.last_lng) if v.last_lng is not None else None
        speed_kmh = int(float(v.last_speed)) if v.last_speed is not None else 0

        vehicles_payload.append({
            'id': str(v.id),
            'name': v.name,
            'vehicle_no': v.vehicle_no,
            'start_point': start_point,
            'end_point': end_point,
            'active_driver_name': v.active_driver.name if v.active_driver else None,
            'active_driver_phone': v.active_driver.phone if v.active_driver else None,
            'seats_booked': seats_booked,
            'seats_total': seats_total,
            'today_revenue': str(rev_today),
            'today_trips': today_trips,
            'lat': lat,
            'lng': lng,
            'speed_kmh': speed_kmh,
            'last_location_at': v.last_location_at.isoformat() if v.last_location_at else None,
            'status': 'on_trip' if getattr(v, 'has_active_trip', False) else 'idle',
        })

    heavy_dues = _build_heavy_dues(month_start, month_end)

    return Response({
        'fetched_at': now.isoformat(),
        'summary': {
            'total_vehicles': len(vehicles_list),
            'on_trip_count': on_trip_count,
            'total_seats_booked': total_seats_booked,
            'total_revenue_today': str(total_revenue_today),
        },
        'vehicles': vehicles_payload,
        'heavy_dues': heavy_dues,
    }, status=status.HTTP_200_OK)


def _build_heavy_dues(month_start, month_end):
    """Return list of heavy dues (drivers with to_pay > 0) with trips_this_month."""
    wallets = (
        Wallet.objects.filter(user__is_driver=True)
        .exclude(to_pay=0)
        .order_by('-to_pay')
        .select_related('user')[:50]
    )
    if not wallets:
        return []

    user_ids = [w.user_id for w in wallets]
    trips_count = dict(
        Trip.objects.filter(
            driver_id__in=user_ids,
            start_time__date__gte=month_start,
            start_time__date__lte=month_end,
            start_time__isnull=False,
        )
        .values('driver_id')
        .annotate(c=Count('id'))
        .values_list('driver_id', 'c')
    )

    result = []
    for w in wallets:
        name = w.user.name or w.user.username or w.user.phone or ''
        initial = (name.strip()[0:1] or w.user.phone or '?')[0:1].upper()
        result.append({
            'id': str(w.user_id),
            'name': name,
            'phone': w.user.phone or '',
            'avatar_initial': initial,
            'to_pay': str(w.to_pay),
            'trips_this_month': trips_count.get(w.user_id, 0),
        })
    return result
