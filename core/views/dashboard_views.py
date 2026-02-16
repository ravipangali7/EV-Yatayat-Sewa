"""Dashboard stats API for admin: aggregates with optional date range and daily series."""
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Q
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from ..models import User, Wallet, Transaction
from booking.models import (
    Vehicle,
    Place,
    Route,
    Trip,
    SeatBooking,
    VehicleTicketBooking,
    VehicleSchedule,
)


def _parse_date(val, default=None):
    if val is None or val == '':
        return default
    try:
        return datetime.strptime(str(val)[:10], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return default


@api_view(['GET'])
def dashboard_stats_view(request):
    """
    GET /api/dashboard/stats/
    Query params: date_from (YYYY-MM-DD), date_to (YYYY-MM-DD).
    Returns: totals (users, vehicles, places, routes, wallets balance, etc.),
    period stats (trips, seat_bookings, transactions, revenue in range),
    daily_series (trips_per_day, revenue_per_day) for charts.
    """
    date_from = _parse_date(request.query_params.get('date_from'))
    date_to = _parse_date(request.query_params.get('date_to'))
    today = timezone.now().date()
    if not date_from:
        date_from = today - timedelta(days=30)
    if not date_to:
        date_to = today
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    # Totals (not filtered by date)
    total_users = User.objects.count()
    total_drivers = User.objects.filter(is_driver=True).count()
    active_vehicles = Vehicle.objects.filter(is_active=True).count()
    total_vehicles = Vehicle.objects.count()
    total_places = Place.objects.count()
    total_routes = Route.objects.count()
    wallet_agg = Wallet.objects.aggregate(
        total_balance=Sum('balance'),
        total_to_pay=Sum('to_pay'),
        total_to_receive=Sum('to_receive'),
    )
    total_balance = wallet_agg['total_balance'] or 0
    total_to_pay = wallet_agg['total_to_pay'] or 0
    total_to_receive = wallet_agg['total_to_receive'] or 0

    # Period: use start_time for trips (exclude null), created_at for others
    from django.db.models.functions import TruncDate
    trip_count = Trip.objects.filter(
        start_time__isnull=False,
        start_time__date__gte=date_from,
        start_time__date__lte=date_to,
    ).count()
    seat_booking_count = SeatBooking.objects.filter(
        check_in_datetime__date__gte=date_from,
        check_in_datetime__date__lte=date_to,
    ).count()
    transaction_count = Transaction.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).count()
    transaction_sum = Transaction.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
        status='success',
    ).aggregate(s=Sum('amount'))
    transaction_sum_amount = transaction_sum['s'] or 0

    # Revenue: seat_bookings.trip_amount (in period by check_in date) + ticket bookings (by created_at in period)
    seat_revenue_agg = SeatBooking.objects.filter(
        check_in_datetime__date__gte=date_from,
        check_in_datetime__date__lte=date_to,
    ).aggregate(s=Sum('trip_amount'))
    seat_revenue = seat_revenue_agg['s'] or 0
    ticket_revenue_agg = VehicleTicketBooking.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).aggregate(s=Sum('price'))
    ticket_revenue = ticket_revenue_agg['s'] or 0
    total_revenue = seat_revenue + ticket_revenue

    # Daily series for charts (trips per day, revenue per day)
    daily_trips = (
        Trip.objects.filter(
            start_time__isnull=False,
            start_time__date__gte=date_from,
            start_time__date__lte=date_to,
        )
        .annotate(day=TruncDate('start_time'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    daily_trips_list = [{'date': item['day'].isoformat(), 'count': item['count']} for item in daily_trips]

    # Revenue per day: seat_bookings by check_in date + ticket by created_at
    from django.db.models import Value, DecimalField
    from decimal import Decimal
    daily_seat = (
        SeatBooking.objects.filter(
            check_in_datetime__date__gte=date_from,
            check_in_datetime__date__lte=date_to,
        )
        .annotate(day=TruncDate('check_in_datetime'))
        .values('day')
        .annotate(amount=Sum('trip_amount'))
        .order_by('day')
    )
    daily_ticket = (
        VehicleTicketBooking.objects.filter(
            created_at__date__gte=date_from,
            created_at__date__lte=date_to,
        )
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(amount=Sum('price'))
        .order_by('day')
    )
    from collections import defaultdict
    revenue_by_day = defaultdict(lambda: Decimal('0'))
    for item in daily_seat:
        revenue_by_day[item['day'].isoformat()] += item['amount'] or Decimal('0')
    for item in daily_ticket:
        revenue_by_day[item['day'].isoformat()] += item['amount'] or Decimal('0')
    daily_revenue_list = [{'date': d, 'amount': str(a)} for d, a in sorted(revenue_by_day.items())]

    return Response({
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
        'totals': {
            'users': total_users,
            'drivers': total_drivers,
            'active_vehicles': active_vehicles,
            'total_vehicles': total_vehicles,
            'places': total_places,
            'routes': total_routes,
            'total_balance': str(total_balance),
            'total_to_pay': str(total_to_pay),
            'total_to_receive': str(total_to_receive),
        },
        'period': {
            'trip_count': trip_count,
            'seat_booking_count': seat_booking_count,
            'transaction_count': transaction_count,
            'transaction_sum': str(transaction_sum_amount),
            'seat_revenue': str(seat_revenue),
            'ticket_revenue': str(ticket_revenue),
            'total_revenue': str(total_revenue),
        },
        'daily_trips': daily_trips_list,
        'daily_revenue': daily_revenue_list,
    })
