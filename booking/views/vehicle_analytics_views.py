"""Vehicle analytics API: deep relational report with date range presets."""
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict

from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from ..models import (
    Vehicle,
    VehicleSeat,
    SeatBooking,
    Trip,
    VehicleSchedule,
    VehicleTicketBooking,
)
from ..utils import date_range_to_datetime_range


def _parse_date(val, default=None):
    if val is None or val == '':
        return default
    try:
        return datetime.strptime(str(val)[:10], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return default


def resolve_analytics_date_range(preset, date_from_param, date_to_param):
    """
    Resolve (date_from, date_to) from preset or custom params.
    preset: 'all' | 'last_day' | 'last_week' | 'last_month' | 'custom'
    Returns (date_from, date_to) as date objects.
    """
    today = timezone.now().date()
    date_from = _parse_date(date_from_param)
    date_to = _parse_date(date_to_param)

    if preset == 'all':
        # All time: use a fixed start (e.g. 2020-01-01) to today
        return today - timedelta(days=365 * 5), today  # 5 years back as "all"
    if preset == 'last_day':
        # Yesterday 00:00 to today end (i.e. yesterday and today)
        return today - timedelta(days=1), today
    if preset == 'last_week':
        return today - timedelta(days=7), today
    if preset == 'last_month':
        return today - timedelta(days=30), today
    # custom or missing preset: use params, default last 30 days
    if not date_from:
        date_from = today - timedelta(days=30)
    if not date_to:
        date_to = today
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    return date_from, date_to


@api_view(['GET'])
def vehicle_analytics_view(request, vehicle_id):
    """
    GET /api/vehicles/<vehicle_id>/analytics/
    Query params: date_from, date_to (YYYY-MM-DD), preset=all|last_day|last_week|last_month|custom
    Returns deep relational analytics for the vehicle.
    """
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    preset = (request.query_params.get('preset') or 'custom').lower()
    date_from, date_to = resolve_analytics_date_range(
        preset,
        request.query_params.get('date_from'),
        request.query_params.get('date_to'),
    )
    start_dt, end_dt = date_range_to_datetime_range(date_from, date_to)

    # Seat bookings for this vehicle in range (by check_in_datetime)
    seat_bookings_qs = SeatBooking.objects.filter(vehicle_id=vehicle_id)
    if start_dt is not None:
        seat_bookings_qs = seat_bookings_qs.filter(check_in_datetime__gte=start_dt)
    if end_dt is not None:
        seat_bookings_qs = seat_bookings_qs.filter(check_in_datetime__lte=end_dt)

    # Trips for this vehicle in range (by start_time)
    trips_qs = Trip.objects.filter(vehicle_id=vehicle_id, start_time__isnull=False)
    if start_dt is not None:
        trips_qs = trips_qs.filter(start_time__gte=start_dt)
    if end_dt is not None:
        trips_qs = trips_qs.filter(start_time__lte=end_dt)

    # Vehicle ticket bookings: schedules belonging to this vehicle, created_at in range
    schedule_ids = VehicleSchedule.objects.filter(vehicle_id=vehicle_id).values_list('id', flat=True)
    ticket_bookings_qs = VehicleTicketBooking.objects.filter(vehicle_schedule_id__in=schedule_ids)
    if start_dt is not None:
        ticket_bookings_qs = ticket_bookings_qs.filter(created_at__gte=start_dt)
    if end_dt is not None:
        ticket_bookings_qs = ticket_bookings_qs.filter(created_at__lte=end_dt)

    # Summary
    seat_revenue_agg = seat_bookings_qs.aggregate(s=Sum('trip_amount'))
    total_seat_revenue = seat_revenue_agg['s'] or Decimal('0')
    ticket_revenue_agg = ticket_bookings_qs.aggregate(s=Sum('price'))
    total_ticket_revenue = ticket_revenue_agg['s'] or Decimal('0')
    total_revenue = total_seat_revenue + total_ticket_revenue

    trip_count = trips_qs.count()
    seat_booking_count = seat_bookings_qs.count()
    ticket_booking_count = ticket_bookings_qs.count()

    # By seat: each vehicle seat with booking_count and total_revenue in range
    seat_agg = (
        seat_bookings_qs.values('vehicle_seat_id', 'vehicle_seat__side', 'vehicle_seat__number')
        .annotate(booking_count=Count('id'), total_revenue=Sum('trip_amount'))
        .order_by('vehicle_seat__side', 'vehicle_seat__number')
    )
    by_seat = []
    for row in seat_agg:
        by_seat.append({
            'seat_id': str(row['vehicle_seat_id']),
            'seat_label': f"{row['vehicle_seat__side']}{row['vehicle_seat__number']}",
            'side': row['vehicle_seat__side'],
            'number': row['vehicle_seat__number'],
            'booking_count': row['booking_count'],
            'total_revenue': str(row['total_revenue'] or 0),
        })
    # Include all vehicle seats with 0 if no bookings
    all_seats = VehicleSeat.objects.filter(vehicle_id=vehicle_id).order_by('side', 'number')
    seat_ids_with_data = {s['seat_id'] for s in by_seat}
    for seat in all_seats:
        if str(seat.id) not in seat_ids_with_data:
            by_seat.append({
                'seat_id': str(seat.id),
                'seat_label': f"{seat.side}{seat.number}",
                'side': seat.side,
                'number': seat.number,
                'booking_count': 0,
                'total_revenue': '0',
            })
    by_seat.sort(key=lambda x: (x['side'], x['number']))

    # Most booked by side (A/B/C)
    side_agg = (
        seat_bookings_qs.values('vehicle_seat__side')
        .annotate(booking_count=Count('id'), revenue=Sum('trip_amount'))
        .order_by('-booking_count')
    )
    most_booked_by_side = [
        {'side': row['vehicle_seat__side'], 'booking_count': row['booking_count'], 'revenue': str(row['revenue'] or 0)}
        for row in side_agg
    ]

    # Top seats by booking count (e.g. top 10)
    top_seats_by_count = sorted(by_seat, key=lambda x: x['booking_count'], reverse=True)[:10]
    top_seats_by_revenue = sorted(by_seat, key=lambda x: float(x['total_revenue']), reverse=True)[:10]

    # Daily series
    daily_seat = (
        seat_bookings_qs.annotate(day=TruncDate('check_in_datetime'))
        .values('day')
        .annotate(amount=Sum('trip_amount'))
        .order_by('day')
    )
    daily_ticket = (
        ticket_bookings_qs.annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(amount=Sum('price'))
        .order_by('day')
    )
    revenue_by_day = defaultdict(lambda: Decimal('0'))
    for item in daily_seat:
        revenue_by_day[item['day'].isoformat()] += item['amount'] or Decimal('0')
    for item in daily_ticket:
        revenue_by_day[item['day'].isoformat()] += item['amount'] or Decimal('0')
    daily_revenue_list = [{'date': d, 'amount': str(a)} for d, a in sorted(revenue_by_day.items())]

    daily_trips_list = [
        {'date': item['day'].isoformat(), 'count': item['count']}
        for item in trips_qs.annotate(day=TruncDate('start_time')).values('day').annotate(count=Count('id')).order_by('day')
    ]

    daily_seat_bookings_list = [
        {'date': item['day'].isoformat(), 'count': item['count']}
        for item in seat_bookings_qs.annotate(day=TruncDate('check_in_datetime')).values('day').annotate(count=Count('id')).order_by('day')
    ]

    # By driver: for each driver who drove this vehicle in range
    driver_agg = (
        trips_qs.values('driver_id', 'driver__name', 'driver__username')
        .annotate(trip_count=Count('id'))
        .order_by('-trip_count')
    )
    by_driver = []
    for row in driver_agg:
        driver_trip_ids = list(trips_qs.filter(driver_id=row['driver_id']).values_list('id', flat=True))
        driver_seat_revenue = SeatBooking.objects.filter(
            trip_id__in=driver_trip_ids,
        ).aggregate(s=Sum('trip_amount'))
        by_driver.append({
            'driver_id': str(row['driver_id']),
            'driver_name': row['driver__name'] or row['driver__username'] or 'Unknown',
            'trip_count': row['trip_count'],
            'seat_revenue': str(driver_seat_revenue['s'] or 0),
        })

    return Response({
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
        'preset': preset,
        'summary': {
            'total_seat_revenue': str(total_seat_revenue),
            'total_ticket_revenue': str(total_ticket_revenue),
            'total_revenue': str(total_revenue),
            'trip_count': trip_count,
            'seat_booking_count': seat_booking_count,
            'ticket_booking_count': ticket_booking_count,
        },
        'by_seat': by_seat,
        'most_booked_by_side': most_booked_by_side,
        'top_seats_by_count': top_seats_by_count,
        'top_seats_by_revenue': top_seats_by_revenue,
        'daily_revenue': daily_revenue_list,
        'daily_trips': daily_trips_list,
        'daily_seat_bookings': daily_seat_bookings_list,
        'by_driver': by_driver,
    })
