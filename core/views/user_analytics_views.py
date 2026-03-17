"""User analytics API: deep relational report (driver + passenger) with date range presets."""
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict

from django.utils import timezone
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from ..models import User
from booking.models import (
    Trip,
    SeatBooking,
    VehicleTicketBooking,
)


def _parse_date(val, default=None):
    if val is None or val == '':
        return default
    try:
        return datetime.strptime(str(val)[:10], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return default


def resolve_analytics_date_range(preset, date_from_param, date_to_param):
    """Resolve (date_from, date_to) from preset or custom params."""
    today = timezone.now().date()
    date_from = _parse_date(date_from_param)
    date_to = _parse_date(date_to_param)

    if preset == 'all':
        return today - timedelta(days=365 * 5), today
    if preset == 'last_day':
        return today - timedelta(days=1), today
    if preset == 'last_week':
        return today - timedelta(days=7), today
    if preset == 'last_month':
        return today - timedelta(days=30), today
    if not date_from:
        date_from = today - timedelta(days=30)
    if not date_to:
        date_to = today
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    return date_from, date_to


@api_view(['GET'])
def user_analytics_view(request, user_id):
    """
    GET /api/users/<user_id>/analytics/
    Query params: date_from, date_to, preset=all|last_day|last_week|last_month|custom
    Returns deep relational analytics: as driver (trips, seat revenue, by vehicle, most booked seat type)
    and as passenger (seat bookings, total spend).
    """
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    preset = (request.query_params.get('preset') or 'custom').lower()
    date_from, date_to = resolve_analytics_date_range(
        preset,
        request.query_params.get('date_from'),
        request.query_params.get('date_to'),
    )

    # --- As driver ---
    trips_as_driver = Trip.objects.filter(
        driver_id=user_id,
        start_time__isnull=False,
        start_time__date__gte=date_from,
        start_time__date__lte=date_to,
    )
    trip_count_as_driver = trips_as_driver.count()
    trip_ids = list(trips_as_driver.values_list('id', flat=True))

    seat_bookings_on_my_trips = SeatBooking.objects.filter(trip_id__in=trip_ids) if trip_ids else SeatBooking.objects.none()
    seat_revenue_as_driver_agg = seat_bookings_on_my_trips.aggregate(s=Sum('trip_amount'))
    total_seat_revenue_as_driver = seat_revenue_as_driver_agg['s'] or Decimal('0')

    # Ticket revenue: from VehicleTicketBooking where vehicle_schedule has a trip in trip_ids
    schedule_ids_from_trips = Trip.objects.filter(id__in=trip_ids).exclude(vehicle_schedule_id__isnull=True).values_list('vehicle_schedule_id', flat=True)
    ticket_bookings_as_driver = VehicleTicketBooking.objects.filter(
        vehicle_schedule_id__in=schedule_ids_from_trips,
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ) if schedule_ids_from_trips else VehicleTicketBooking.objects.none()
    ticket_revenue_as_driver_agg = ticket_bookings_as_driver.aggregate(s=Sum('price'))
    total_ticket_revenue_as_driver = ticket_revenue_as_driver_agg['s'] or Decimal('0')

    # By vehicle (as driver)
    vehicle_agg = (
        trips_as_driver.values('vehicle_id', 'vehicle__name', 'vehicle__vehicle_no')
        .annotate(trip_count=Count('id'))
        .order_by('-trip_count')
    )
    by_vehicle = []
    for row in vehicle_agg:
        vid = row['vehicle_id']
        v_trip_ids = list(trips_as_driver.filter(vehicle_id=vid).values_list('id', flat=True))
        v_seat_revenue = SeatBooking.objects.filter(trip_id__in=v_trip_ids).aggregate(s=Sum('trip_amount'))
        by_vehicle.append({
            'vehicle_id': str(vid),
            'vehicle_name': row['vehicle__name'] or row['vehicle__vehicle_no'] or 'Unknown',
            'trip_count': row['trip_count'],
            'seat_revenue': str(v_seat_revenue['s'] or 0),
        })

    # Most booked seat type when user was driver (by side and by seat)
    most_booked_by_side_driver = []
    if seat_bookings_on_my_trips.exists():
        side_agg = (
            seat_bookings_on_my_trips.values('vehicle_seat__side')
            .annotate(booking_count=Count('id'), revenue=Sum('trip_amount'))
            .order_by('-booking_count')
        )
        most_booked_by_side_driver = [
            {'side': row['vehicle_seat__side'], 'booking_count': row['booking_count'], 'revenue': str(row['revenue'] or 0)}
            for row in side_agg
        ]
    seat_agg_driver = (
        seat_bookings_on_my_trips.values('vehicle_seat_id', 'vehicle_seat__side', 'vehicle_seat__number')
        .annotate(booking_count=Count('id'), total_revenue=Sum('trip_amount'))
        .order_by('-booking_count')[:10]
    )
    top_seats_as_driver = [
        {
            'seat_label': f"{row['vehicle_seat__side']}{row['vehicle_seat__number']}",
            'booking_count': row['booking_count'],
            'total_revenue': str(row['total_revenue'] or 0),
        }
        for row in seat_agg_driver
    ]

    # Daily series as driver
    daily_trips_driver = [
        {'date': item['day'].isoformat(), 'count': item['count']}
        for item in trips_as_driver.annotate(day=TruncDate('start_time')).values('day').annotate(count=Count('id')).order_by('day')
    ]
    daily_seat_revenue_driver = defaultdict(lambda: Decimal('0'))
    for item in seat_bookings_on_my_trips.annotate(day=TruncDate('check_in_datetime')).values('day').annotate(amount=Sum('trip_amount')).order_by('day'):
        daily_seat_revenue_driver[item['day'].isoformat()] += item['amount'] or Decimal('0')
    daily_revenue_as_driver_list = [{'date': d, 'amount': str(a)} for d, a in sorted(daily_seat_revenue_driver.items())]

    # --- As passenger ---
    seat_bookings_as_passenger = SeatBooking.objects.filter(
        user_id=user_id,
        check_in_datetime__date__gte=date_from,
        check_in_datetime__date__lte=date_to,
    )
    seat_booking_count_as_passenger = seat_bookings_as_passenger.count()
    spend_as_passenger_agg = seat_bookings_as_passenger.aggregate(s=Sum('trip_amount'))
    total_spend_as_passenger = spend_as_passenger_agg['s'] or Decimal('0')

    # Passenger: by vehicle (aggregated)
    passenger_by_vehicle = (
        seat_bookings_as_passenger.values('vehicle_id', 'vehicle__name', 'vehicle__vehicle_no')
        .annotate(booking_count=Count('id'), total_spend=Sum('trip_amount'))
        .order_by('-booking_count')
    )
    as_passenger_by_vehicle = [
        {
            'vehicle_id': str(row['vehicle_id']),
            'vehicle_name': row['vehicle__name'] or row['vehicle__vehicle_no'] or 'Unknown',
            'booking_count': row['booking_count'],
            'total_spend': str(row['total_spend'] or 0),
        }
        for row in passenger_by_vehicle
    ]

    return Response({
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
        'preset': preset,
        'user_id': str(user_id),
        'is_driver': user.is_driver,
        'summary': {
            'trip_count_as_driver': trip_count_as_driver,
            'total_seat_revenue_as_driver': str(total_seat_revenue_as_driver),
            'total_ticket_revenue_as_driver': str(total_ticket_revenue_as_driver),
            'seat_booking_count_as_passenger': seat_booking_count_as_passenger,
            'total_spend_as_passenger': str(total_spend_as_passenger),
        },
        'as_driver': {
            'by_vehicle': by_vehicle,
            'most_booked_by_side': most_booked_by_side_driver,
            'top_seats': top_seats_as_driver,
            'daily_trips': daily_trips_driver,
            'daily_revenue': daily_revenue_as_driver_list,
        },
        'as_passenger': {
            'by_vehicle': as_passenger_by_vehicle,
        },
    })
