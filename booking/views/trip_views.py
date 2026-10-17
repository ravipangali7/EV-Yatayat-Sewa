"""Trip views: start trip, end trip, CRUD"""
import math
import uuid
from datetime import date, datetime
from decimal import Decimal

from django.utils import timezone
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ..models import Trip, Vehicle, Route, Location, VehicleSchedule, VehicleTicketBooking, SeatBooking, VehicleSeat
from ..route_order import get_route_place_order, get_route_ordered_points
from ..services.notify_node import notify_node_seat_booked
from ..utils import date_range_to_datetime_range
from core.models import User, SuperSetting


def haversine_km(lat1, lon1, lat2, lon2):
    """Distance in km between two points (Haversine)."""
    lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return round(c * 6371, 4)


def _trip_to_response(trip):
    """Build trip dict for API response with display names for vehicle, driver, route."""
    v = trip.vehicle if hasattr(trip, 'vehicle') and trip.vehicle else None
    d = trip.driver if hasattr(trip, 'driver') and trip.driver else None
    r = trip.route if hasattr(trip, 'route') and trip.route else None
    return {
        'id': str(trip.id),
        'trip_id': trip.trip_id,
        'vehicle': str(trip.vehicle_id),
        'vehicle_name': v.name if v else None,
        'vehicle_no': v.vehicle_no if v else None,
        'driver': str(trip.driver_id),
        'driver_name': d.name if d else None,
        'driver_phone': d.phone if d else None,
        'route': str(trip.route_id),
        'route_name': r.name if r else None,
        'start_time': trip.start_time.isoformat() if trip.start_time else None,
        'end_time': trip.end_time.isoformat() if trip.end_time else None,
        'remarks': trip.remarks or '',
        'is_scheduled': trip.is_scheduled,
        'vehicle_schedule': str(trip.vehicle_schedule_id) if trip.vehicle_schedule_id else None,
        'reverse_direction': getattr(trip, 'reverse_direction', False),
        'created_at': trip.created_at.isoformat(),
        'updated_at': trip.updated_at.isoformat(),
    }


def _seat_to_list(seat):
    if isinstance(seat, list):
        return [x for x in seat if isinstance(x, dict) and x.get('side') is not None and x.get('number') is not None]
    if isinstance(seat, dict) and seat.get('side') is not None and seat.get('number') is not None:
        return [seat]
    return []


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trip_start_view(request):
    """
    Start a trip. Body: vehicle_id (required), vehicle_schedule_id (optional, when confirming scheduled),
    latitude, longitude (optional, for scheduled check).
    - If vehicle_schedule_id provided: create scheduled trip and SeatBookings for that schedule's tickets.
    - Else: check if vehicle has a schedule today within time window and location near start; if yes return
      need_confirm_scheduled with schedule and tickets; else create normal trip.
    """
    vehicle_id = request.POST.get('vehicle_id') or request.data.get('vehicle_id')
    vehicle_schedule_id = request.POST.get('vehicle_schedule_id') or request.data.get('vehicle_schedule_id')
    latitude = request.POST.get('latitude') or request.data.get('latitude')
    longitude = request.POST.get('longitude') or request.data.get('longitude')

    if not vehicle_id:
        return Response({'error': 'vehicle_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        vehicle = Vehicle.objects.select_related('active_driver', 'active_route').get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    if vehicle.active_driver_id != user.id:
        return Response({'error': 'You are not the active driver of this vehicle'}, status=status.HTTP_400_BAD_REQUEST)
    if not vehicle.active_route_id:
        return Response({'error': 'Vehicle has no active route. Select a route first.'}, status=status.HTTP_400_BAD_REQUEST)

    if Trip.objects.filter(vehicle=vehicle, end_time__isnull=True).exists():
        return Response({'error': 'Vehicle already has an active trip'}, status=status.HTTP_400_BAD_REQUEST)

    now = timezone.now()
    today = now.date()

    # Confirm scheduled: create Trip + SeatBookings
    if vehicle_schedule_id:
        try:
            vs = VehicleSchedule.objects.select_related(
                'vehicle', 'route', 'route__start_point', 'route__end_point',
            ).prefetch_related(
                'ticket_bookings', 'ticket_bookings__user',
                'ticket_bookings__pickup_point', 'ticket_bookings__destination_point',
            ).get(pk=vehicle_schedule_id, vehicle=vehicle, date=today)
        except VehicleSchedule.DoesNotExist:
            return Response({'error': 'Vehicle schedule not found or not for today'}, status=status.HTTP_404_NOT_FOUND)
        route = vs.route
        reverse = getattr(vs, 'reverse_direction', False)
        start_place = route.end_point if reverse else route.start_point
        end_place = route.start_point if reverse else route.end_point
        start_addr = getattr(start_place, 'address', None) or f"{start_place.name}"

        scheduled_created_seats = []
        with transaction.atomic():
            trip_id_str = f"T-{today.strftime('%Y%m%d')}-{vehicle.id}-{uuid.uuid4().hex[:8]}"
            trip = Trip.objects.create(
                vehicle=vehicle,
                driver=user,
                route=route,
                trip_id=trip_id_str,
                start_time=now,
                end_time=None,
                is_scheduled=True,
                vehicle_schedule=vs,
                reverse_direction=reverse,
            )
            for tb in vs.ticket_bookings.all():
                seat_list = _seat_to_list(tb.seat)
                if not seat_list:
                    continue
                amount_per_seat = (tb.price / len(seat_list)) if seat_list else tb.price
                for s in seat_list:
                    side = str(s.get('side', ''))
                    try:
                        num = int(s.get('number', 0))
                    except (TypeError, ValueError):
                        continue
                    try:
                        vseat = VehicleSeat.objects.get(vehicle=vehicle, side=side, number=num)
                    except VehicleSeat.DoesNotExist:
                        continue
                    origin_place = tb.pickup_point or start_place
                    dest_place = tb.destination_point or end_place
                    SeatBooking.objects.create(
                        user=tb.user,
                        is_guest=tb.is_guest,
                        vehicle=vehicle,
                        vehicle_seat=vseat,
                        trip=trip,
                        check_in_lat=start_place.latitude,
                        check_in_lng=start_place.longitude,
                        check_in_datetime=now,
                        check_in_address=start_addr,
                        check_out_lat=None,
                        check_out_lng=None,
                        check_out_datetime=None,
                        check_out_address=None,
                        trip_distance=None,
                        trip_duration=None,
                        trip_amount=amount_per_seat,
                        is_paid=True,
                        origin_place=origin_place,
                        destination_place=dest_place,
                    )
                    if vseat.status != 'booked':
                        vseat.status = 'booked'
                        vseat.save(update_fields=['status', 'updated_at'])
                    user_name = (tb.name or '').strip() or (tb.user.name if tb.user else None) or (tb.user.username if tb.user else None) or 'Guest'
                    scheduled_created_seats.append({
                        'vehicle_seat_id': vseat.id,
                        'side': vseat.side,
                        'number': vseat.number,
                        'user_name': user_name,
                        'from_address': start_addr,
                        'to_name': dest_place.name if dest_place else '',
                    })
        if scheduled_created_seats:
            notify_node_seat_booked(trip.trip_id, vehicle.id, scheduled_created_seats)
        return Response(_trip_to_response(trip), status=status.HTTP_201_CREATED)

    # Check for scheduled trip prompt
    try:
        ss = SuperSetting.objects.latest('created_at')
        minute_coverage = int(ss.minute_coverage_schedule or 60)
        point_radius_km = float(ss.point_cover_radius or 0.5)
    except (SuperSetting.DoesNotExist, (TypeError, ValueError)):
        minute_coverage = 60
        point_radius_km = 0.5

    if latitude is not None and longitude is not None:
        lat_f = float(latitude)
        lng_f = float(longitude)
        # Schedules for this vehicle, today, time within ± minute_coverage of now
        now_minutes = now.hour * 60 + now.minute
        for vs in VehicleSchedule.objects.filter(vehicle=vehicle, date=today).select_related('route', 'route__start_point', 'route__end_point').prefetch_related('ticket_bookings'):
            vs_minutes = vs.time.hour * 60 + vs.time.minute if vs.time else 0
            if abs(now_minutes - vs_minutes) > minute_coverage:
                continue
            reverse = getattr(vs, 'reverse_direction', False)
            start_place = vs.route.end_point if reverse else vs.route.start_point
            dist = haversine_km(lat_f, lng_f, float(start_place.latitude), float(start_place.longitude))
            if dist <= point_radius_km:
                tickets = []
                for tb in vs.ticket_bookings.all():
                    tickets.append({
                        'id': str(tb.id),
                        'pnr': tb.pnr,
                        'name': tb.name,
                        'phone': tb.phone,
                        'seat': _seat_to_list(tb.seat),
                        'price': str(tb.price),
                    })
                return Response({
                    'need_confirm_scheduled': True,
                    'schedule': {
                        'id': str(vs.id),
                        'date': vs.date.isoformat(),
                        'time': vs.time.strftime('%H:%M') if vs.time else None,
                        'route_name': vs.route.name,
                        'start_point_name': vs.route.start_point.name,
                        'end_point_name': vs.route.end_point.name,
                        'reverse_direction': reverse,
                    },
                    'tickets': tickets,
                }, status=status.HTTP_200_OK)

    # Normal trip: optional reverse_direction (only when route is bidirectional)
    reverse_direction = request.POST.get('reverse_direction') or request.data.get('reverse_direction')
    if reverse_direction is not None:
        reverse_direction = reverse_direction is True or (isinstance(reverse_direction, str) and reverse_direction.lower() == 'true')
    else:
        reverse_direction = False
    if reverse_direction and not getattr(vehicle.active_route, 'is_bidirectional', False):
        reverse_direction = False
    trip_id = f"T-{today.strftime('%Y%m%d')}-{vehicle.id}-{uuid.uuid4().hex[:8]}"
    trip = Trip.objects.create(
        vehicle=vehicle,
        driver=user,
        route=vehicle.active_route,
        trip_id=trip_id,
        start_time=now,
        end_time=None,
        is_scheduled=False,
        vehicle_schedule=None,
        reverse_direction=reverse_direction,
    )
    return Response(_trip_to_response(trip), status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trip_end_view(request, pk):
    """
    End trip. Body: latitude, longitude, confirm_out_of_range (optional).
    If current location > 1.5km from route end_point, require confirm_out_of_range=true and set remarks.
    """
    latitude = request.POST.get('latitude') or request.data.get('latitude')
    longitude = request.POST.get('longitude') or request.data.get('longitude')
    confirm_out_of_range = request.POST.get('confirm_out_of_range') or request.data.get('confirm_out_of_range')
    if isinstance(confirm_out_of_range, str):
        confirm_out_of_range = confirm_out_of_range.lower() in ('true', '1', 'yes')
    else:
        confirm_out_of_range = bool(confirm_out_of_range)

    lat = _finite_float(latitude)
    lng = _finite_float(longitude)
    if lat is None or lng is None:
        return Response({'error': 'latitude and longitude are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        trip = Trip.objects.select_related('vehicle', 'route', 'route__start_point', 'route__end_point').get(pk=pk)
    except Trip.DoesNotExist:
        return Response({'error': 'Trip not found'}, status=status.HTTP_404_NOT_FOUND)

    # Idempotent: a previous attempt may have saved end_time and then failed
    # while writing the location row. The driver app must be able to clear.
    if trip.end_time:
        return Response({
            'trip': _trip_to_response(trip),
            'within_destination': True,
            'message': 'Trip is already ended',
        }, status=status.HTTP_200_OK)

    user = request.user
    if trip.driver_id != user.id:
        return Response({'error': 'You are not the driver of this trip'}, status=status.HTTP_403_FORBIDDEN)

    pending = list(
        SeatBooking.objects.filter(trip=trip, check_out_datetime__isnull=True)
        .select_related('vehicle_seat')
        .values_list('vehicle_seat__side', 'vehicle_seat__number')
    )
    if pending:
        pending_labels = [f"{s}{n}" for s, n in pending if s and n is not None]
        detail = f' Still on board: {", ".join(pending_labels)}.' if pending_labels else ''
        return Response({
            'error': f'Check out all passengers first.{detail}',
            'pending_seat_bookings': pending_labels,
        }, status=status.HTTP_400_BAD_REQUEST)

    reverse = getattr(trip, 'reverse_direction', False)
    distance_km = None
    try:
        route = trip.route
        end_place = None
        if route is not None:
            end_place = route.start_point if reverse else route.end_point
        if end_place is not None and end_place.latitude is not None and end_place.longitude is not None:
            distance_km = haversine_km(
                lat, lng,
                float(end_place.latitude), float(end_place.longitude)
            )
    except (TypeError, ValueError, AttributeError):
        distance_km = None
    try:
        ss = SuperSetting.objects.latest('created_at')
        stop_radius_km = float(ss.point_cover_radius or 1.5)
    except (SuperSetting.DoesNotExist, (TypeError, ValueError)):
        stop_radius_km = 1.5

    outside = distance_km is None or distance_km > stop_radius_km
    if outside:
        if not confirm_out_of_range:
            return Response({
                'within_destination': False,
                'message': 'You are not at the proper destination. Are you sure you want to end the trip?',
                'distance_km': distance_km,
            }, status=status.HTTP_200_OK)
        remark = "Driver didn't took in proper destination."
        if trip.remarks:
            trip.remarks = trip.remarks + "\n" + remark
        else:
            trip.remarks = remark

    now = timezone.now()
    trip.end_time = now
    with transaction.atomic():
        trip.save(update_fields=['end_time', 'remarks', 'updated_at'])
        vehicle = trip.vehicle
        vehicle.active_driver = None
        vehicle.active_route = None
        vehicle.save(update_fields=['active_driver', 'active_route', 'updated_at'])

    try:
        Location.objects.create(
            vehicle=trip.vehicle,
            trip=trip,
            latitude=_coord_decimal(lat),
            longitude=_coord_decimal(lng),
            speed=None,
        )
    except Exception:
        # The trip is already ended. A location-row failure must not make the
        # client retry into "already ended" and leave the trip on screen.
        pass

    return Response({
        'trip': _trip_to_response(trip),
        'within_destination': distance_km is not None and distance_km <= stop_radius_km,
    }, status=status.HTTP_200_OK)


def _finite_float(value):
    if value is None or value == '':
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _coord_decimal(number):
    return Decimal(str(number)).quantize(Decimal('0.000001'))


def _parse_date(val):
    if val is None or val == '':
        return None
    try:
        from datetime import datetime as dt
        return dt.strptime(str(val)[:10], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


@api_view(['GET'])
def trip_list_get_view(request):
    """List trips with filters: vehicle, driver, route, vehicle_schedule, active_only, search (trip_id), date_from, date_to."""
    from django.db.models import Q
    vehicle_id = request.query_params.get('vehicle')
    driver_id = request.query_params.get('driver')
    route_id = request.query_params.get('route')
    vehicle_schedule_id = request.query_params.get('vehicle_schedule')
    active_only = request.query_params.get('active_only')
    search = request.query_params.get('search', '').strip()
    date_from = _parse_date(request.query_params.get('date_from'))
    date_to = _parse_date(request.query_params.get('date_to'))

    queryset = Trip.objects.select_related('vehicle', 'driver', 'route').all()
    if vehicle_id:
        queryset = queryset.filter(vehicle_id=vehicle_id)
    if driver_id:
        queryset = queryset.filter(driver_id=driver_id)
    if route_id:
        queryset = queryset.filter(route_id=route_id)
    if vehicle_schedule_id:
        queryset = queryset.filter(vehicle_schedule_id=vehicle_schedule_id)
    if active_only and active_only.lower() == 'true':
        queryset = queryset.filter(end_time__isnull=True)
    if search:
        queryset = queryset.filter(trip_id__icontains=search)
    start_dt, end_dt = date_range_to_datetime_range(date_from, date_to)
    if start_dt is not None or end_dt is not None:
        queryset = queryset.filter(start_time__isnull=False)
        if start_dt is not None:
            queryset = queryset.filter(start_time__gte=start_dt)
        if end_dt is not None:
            queryset = queryset.filter(start_time__lte=end_dt)

    total = queryset.count()
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 10))
    start = (page - 1) * per_page
    end = start + per_page
    trips = queryset.order_by('-created_at')[start:end]

    return Response({
        'results': [_trip_to_response(t) for t in trips],
        'count': total,
        'page': page,
        'per_page': per_page,
        'stats': {'total_count': total},
    })


def _location_to_response(loc):
    return {
        'id': str(loc.id),
        'latitude': str(loc.latitude),
        'longitude': str(loc.longitude),
        'speed': str(loc.speed) if loc.speed is not None else None,
        'course': str(loc.course) if getattr(loc, 'course', None) is not None else None,
        'created_at': loc.created_at.isoformat(),
    }


def _announcement_text_for_stop(place, rsp, header):
    """Stop speech, including the route terminus. Start and end points have no RouteStopPoint row."""
    custom = (getattr(rsp, 'announcement_text', None) or '').strip() if rsp is not None else ''
    if custom:
        return custom[:500]
    name = (getattr(place, 'name', None) or '').strip()
    if header:
        return (header.replace('$x', name).replace('$X', name).strip() or name)[:500]
    return name[:500]


def _segment_projection_km(lat, lng, lat1, lng1, lat2, lng2):
    """Project a point onto a segment. Returns (t 0..1, cross-track km)."""
    lat_scale = 110.574
    lng_scale = 111.320 * math.cos(math.radians((lat1 + lat2) / 2.0))
    bx = (lng2 - lng1) * lng_scale
    by = (lat2 - lat1) * lat_scale
    px = (lng - lng1) * lng_scale
    py = (lat - lat1) * lat_scale
    ab2 = bx * bx + by * by
    if ab2 <= 1e-12:
        return 0.0, math.hypot(px, py)
    t = max(0.0, min(1.0, (px * bx + py * by) / ab2))
    return t, math.hypot(px - t * bx, py - t * by)


def _route_cumulative_km(points):
    cum = [0.0]
    for i in range(1, len(points)):
        prev = points[i - 1][1]
        cur = points[i][1]
        if prev is None or cur is None or prev.latitude is None or cur.latitude is None or prev.longitude is None or cur.longitude is None:
            cum.append(cum[-1])
            continue
        cum.append(cum[-1] + haversine_km(prev.latitude, prev.longitude, cur.latitude, cur.longitude))
    return cum


def _project_progress_km(points, cum, lat, lng):
    if len(points) <= 1:
        return 0.0
    best_dist = float('inf')
    best_progress = 0.0
    for i in range(len(points) - 1):
        a = points[i][1]
        b = points[i + 1][1]
        if a is None or b is None or a.latitude is None or b.latitude is None:
            continue
        t, dist = _segment_projection_km(
            lat, lng,
            float(a.latitude), float(a.longitude),
            float(b.latitude), float(b.longitude),
        )
        if dist < best_dist:
            best_dist = dist
            best_progress = cum[i] + t * (cum[i + 1] - cum[i])
    return best_progress


def select_reached_stop_index(points, lat, lng, radius_km, approach_km=0.02):
    """
    Route index of the stop the vehicle has reached.

    A later stop that is still inside the cover radius wins once the bus has
    crossed up to it. That is the case when the previous pin is on the other
    side of the road and its circle would otherwise hide the destination.
    Returns (index, crossed) or (None, False).
    """
    if not points:
        return None, False
    cum = _route_cumulative_km(points)
    progress = _project_progress_km(points, cum, float(lat), float(lng))
    reached = []
    nearest = None
    for i, (_kind, place, _rsp) in enumerate(points):
        if place is None or place.latitude is None or place.longitude is None:
            continue
        dist = haversine_km(lat, lng, place.latitude, place.longitude)
        if dist <= radius_km:
            if nearest is None or dist < nearest[0]:
                nearest = (dist, i)
            if progress + approach_km >= cum[i]:
                reached.append(i)
    if reached:
        return reached[-1], True
    if nearest is not None:
        return nearest[1], False
    return None, False


@api_view(['GET'])
def trip_detail_get_view(request, pk):
    """Get single trip with locations, seat_bookings, revenue, vehicle_schedule, ticket_bookings."""
    from django.db.models import Sum
    from ..serializers import SeatBookingSerializer
    try:
        trip = Trip.objects.select_related(
            'vehicle', 'driver', 'route', 'vehicle_schedule',
            'vehicle_schedule__vehicle', 'vehicle_schedule__route',
            'vehicle_schedule__route__start_point', 'vehicle_schedule__route__end_point',
            'route__start_point', 'route__end_point',
        ).prefetch_related(
            'locations',
            'seat_bookings__user',
            'seat_bookings__vehicle_seat',
            'seat_bookings__destination_place',
            'seat_bookings__origin_place',
            'vehicle_schedule__ticket_bookings',
            'vehicle_schedule__ticket_bookings__pickup_point',
            'vehicle_schedule__ticket_bookings__destination_point',
            'route__stop_points__place',
        ).get(pk=pk)
    except Trip.DoesNotExist:
        return Response({'error': 'Trip not found'}, status=status.HTTP_404_NOT_FOUND)

    data = _trip_to_response(trip)

    # point_cover_radius_km for client-side geofence announcements
    try:
        ss = SuperSetting.objects.latest('created_at')
        data['point_cover_radius_km'] = float(ss.point_cover_radius or 0.5)
    except (SuperSetting.DoesNotExist, (TypeError, ValueError)):
        data['point_cover_radius_km'] = 0.5

    # Route with stop_points in effective traversal order (forward or reverse)
    route = trip.route
    if route:
        reverse = getattr(trip, 'reverse_direction', False)
        start_place = route.end_point if reverse else route.start_point
        end_place = route.start_point if reverse else route.end_point
        points = get_route_ordered_points(route, reverse)
        try:
            header = (getattr(SuperSetting.objects.latest('created_at'), 'stop_point_announcement_header', None) or '').strip()
        except SuperSetting.DoesNotExist:
            header = ''
        open_dest_ids = set(
            SeatBooking.objects.filter(trip=trip, check_out_datetime__isnull=True)
            .exclude(destination_place_id=None)
            .values_list('destination_place_id', flat=True)
        )
        if trip.vehicle_schedule_id:
            ticket_qs = trip.vehicle_schedule.ticket_bookings.all()
            open_dest_ids.update(
                ticket_qs.exclude(destination_point_id=None).values_list('destination_point_id', flat=True)
            )
            if ticket_qs.filter(destination_point_id__isnull=True).exists():
                terminus = route.start_point if reverse else route.end_point
                if terminus is not None:
                    open_dest_ids.add(terminus.id)
        stop_points = []
        ordered_points = []
        for order_idx, (kind, place, rsp) in enumerate(points):
            if place is None:
                continue
            announcement_text = _announcement_text_for_stop(place, rsp, header)
            has_destination_booking = place.id in open_dest_ids
            lat_str = str(place.latitude) if place.latitude is not None else None
            lng_str = str(place.longitude) if place.longitude is not None else None
            stop_points.append({
                'kind': kind,
                'place': str(place.id),
                'place_id': str(place.id),
                'order': order_idx,
                'announcement_text': announcement_text,
                'place_name': place.name,
                'place_code': place.code,
                'latitude': lat_str,
                'longitude': lng_str,
                'has_destination_booking': has_destination_booking,
            })
            ordered_points.append({
                'kind': kind,
                'order': order_idx,
                'place_id': str(place.id),
                'name': place.name,
                'latitude': lat_str,
                'longitude': lng_str,
            })
        data['route'] = {
            'id': str(route.id),
            'name': route.name,
            'is_bidirectional': getattr(route, 'is_bidirectional', False),
            'start_point': str(start_place.id) if start_place else None,
            'start_point_name': start_place.name if start_place else None,
            'start_point_lat': str(start_place.latitude) if start_place and start_place.latitude is not None else None,
            'start_point_lng': str(start_place.longitude) if start_place and start_place.longitude is not None else None,
            'end_point': str(end_place.id) if end_place else None,
            'end_point_name': end_place.name if end_place else None,
            'end_point_lat': str(end_place.latitude) if end_place and end_place.latitude is not None else None,
            'end_point_lng': str(end_place.longitude) if end_place and end_place.longitude is not None else None,
            'stop_points': stop_points,
            'ordered_points': ordered_points,
        }
    else:
        data['route'] = None

    # Locations for this trip (ordered by created_at for polyline/playback)
    locations = list(trip.locations.all().order_by('created_at'))
    data['locations'] = [_location_to_response(loc) for loc in locations]

    # Seat bookings with full nested data
    seat_bookings = trip.seat_bookings.all().select_related(
        'user', 'vehicle', 'vehicle_seat', 'destination_place', 'origin_place'
    ).order_by('check_in_datetime')
    data['seat_bookings'] = SeatBookingSerializer(seat_bookings, many=True).data

    # Revenue: seat booking total + ticket total (if scheduled)
    seat_revenue_agg = trip.seat_bookings.aggregate(s=Sum('trip_amount'))
    total_seat_booking_revenue = seat_revenue_agg['s'] or Decimal('0')
    data['total_seat_booking_revenue'] = str(total_seat_booking_revenue)
    ticket_revenue = Decimal('0')
    data['vehicle_schedule'] = None
    data['ticket_bookings'] = []
    if trip.vehicle_schedule_id:
        vs = trip.vehicle_schedule
        data['vehicle_schedule'] = {
            'id': str(vs.id),
            'date': vs.date.isoformat(),
            'time': vs.time.strftime('%H:%M') if vs.time else None,
            'price': str(vs.price),
            'route_name': vs.route.name if vs.route else None,
            'vehicle_name': vs.vehicle.name if vs.vehicle else None,
            'vehicle_no': vs.vehicle.vehicle_no if vs.vehicle else None,
        }
        for tb in vs.ticket_bookings.all().select_related('pickup_point', 'destination_point'):
            ticket_revenue += tb.price
            data['ticket_bookings'].append({
                'id': str(tb.id),
                'pnr': tb.pnr,
                'name': tb.name,
                'phone': tb.phone,
                'seat': tb.seat,
                'price': str(tb.price),
                'is_paid': tb.is_paid,
                'pickup_point_name': tb.pickup_point.name if tb.pickup_point else None,
                'destination_point_name': tb.destination_point.name if tb.destination_point else None,
            })
    data['ticket_revenue'] = str(ticket_revenue)
    data['total_revenue'] = str(total_seat_booking_revenue + ticket_revenue)

    return Response(data)


@api_view(['POST'])
def trip_detail_post_view(request, pk):
    """Update trip (remarks, etc.)."""
    try:
        trip = Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        return Response({'error': 'Trip not found'}, status=status.HTTP_404_NOT_FOUND)
    if 'remarks' in request.data:
        trip.remarks = request.data.get('remarks') or trip.remarks
    trip.save()
    return Response(_trip_to_response(trip))


@api_view(['GET'])
def trip_delete_get_view(request, pk):
    """Delete trip."""
    try:
        trip = Trip.objects.get(pk=pk)
        trip.delete()
        return Response({'message': 'Trip deleted'}, status=status.HTTP_200_OK)
    except Trip.DoesNotExist:
        return Response({'error': 'Trip not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trip_current_stop_view(request):
    """
    Given trip_id, latitude, longitude: return which stop (if any) is within point_cover_radius.
    For scheduled trips, also return ticket bookings whose pickup_point is that place.
    Query params: trip, latitude, longitude.
    """
    trip_id = request.query_params.get('trip')
    lat = request.query_params.get('latitude')
    lng = request.query_params.get('longitude')
    if not trip_id or lat is None or lng is None:
        return Response(
            {'error': 'trip, latitude and longitude are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        trip = Trip.objects.select_related('route', 'route__start_point', 'route__end_point', 'vehicle').prefetch_related(
            'route__stop_points__place', 'vehicle_schedule__ticket_bookings__pickup_point',
            'vehicle_schedule__ticket_bookings__destination_point', 'vehicle__seats',
        ).get(pk=trip_id)
    except Trip.DoesNotExist:
        return Response({'error': 'Trip not found'}, status=status.HTTP_404_NOT_FOUND)
    if trip.driver_id != request.user.id:
        return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
    if trip.end_time:
        return Response({'at_stop': None}, status=status.HTTP_200_OK)

    try:
        ss = SuperSetting.objects.latest('created_at')
        radius_km = float(ss.point_cover_radius or 0.5)
        header = (getattr(ss, 'stop_point_announcement_header', None) or '').strip()
    except (SuperSetting.DoesNotExist, (TypeError, ValueError)):
        radius_km = 0.5
        header = ''

    route = trip.route
    reverse = getattr(trip, 'reverse_direction', False)
    points = get_route_ordered_points(route, reverse)

    lat_f, lng_f = float(lat), float(lng)
    chosen_index, crossed = select_reached_stop_index(points, lat_f, lng_f, radius_km)
    if chosen_index is None:
        return Response({'at_stop': None}, status=status.HTTP_200_OK)

    for idx, (_kind, place, rsp) in enumerate(points):
        if idx != chosen_index:
            continue
        announcement_text = _announcement_text_for_stop(place, rsp, header)
        pickups = []
        if trip.is_scheduled and trip.vehicle_schedule_id:
            for vtb in trip.vehicle_schedule.ticket_bookings.filter(pickup_point_id=place.id).select_related('pickup_point'):
                seat_str = str(vtb.seat) if isinstance(vtb.seat, (dict, list)) else vtb.seat
                if isinstance(vtb.seat, list):
                    seat_str = ', '.join(f"{s.get('side', '')}{s.get('number', '')}" for s in vtb.seat if isinstance(s, dict))
                pickups.append({
                    'pnr': vtb.pnr,
                    'name': vtb.name,
                    'phone': vtb.phone,
                    'seat': seat_str,
                })
        for sb in SeatBooking.objects.filter(
            trip=trip,
            origin_place_id=place.id,
            check_out_datetime__isnull=True,
        ).select_related('user', 'vehicle_seat'):
            pickups.append({
                'pnr': '',
                'name': sb.user.name if sb.user else 'Guest',
                'phone': getattr(sb.user, 'phone', None) or '',
                'seat': f"{sb.vehicle_seat.side}{sb.vehicle_seat.number}",
            })
        booking_select = (
            'vehicle_seat', 'user', 'trip', 'trip__driver', 'vehicle', 'destination_place', 'origin_place',
        )
        open_bookings = list(
            SeatBooking.objects.filter(
                trip=trip,
                destination_place_id=place.id,
                check_out_datetime__isnull=True,
            ).select_related(*booking_select)
        )
        # Scheduled tickets whose SeatBooking was created without a destination still belong to this stop.
        route_end = None
        if route is not None:
            route_end = route.start_point if reverse else route.end_point
        if trip.is_scheduled and trip.vehicle_schedule_id and trip.vehicle_id:
            vehicle_seat_by_key = {(vs.side, vs.number): vs for vs in trip.vehicle.seats.all()}
            unassigned = {
                sb.vehicle_seat_id: sb
                for sb in SeatBooking.objects.filter(
                    trip=trip,
                    destination_place_id__isnull=True,
                    check_out_datetime__isnull=True,
                ).select_related(*booking_select)
            }
            for vtb in trip.vehicle_schedule.ticket_bookings.all():
                dest_id = vtb.destination_point_id or (route_end.id if route_end is not None else None)
                if dest_id != place.id:
                    continue
                for seat_item in _seat_to_list(vtb.seat):
                    side = str(seat_item.get('side', '')).strip()
                    try:
                        num = int(seat_item.get('number'))
                    except (TypeError, ValueError):
                        continue
                    vs = vehicle_seat_by_key.get((side, num))
                    if vs is None:
                        continue
                    sb = unassigned.pop(vs.id, None)
                    if sb is None:
                        continue
                    sb.destination_place = place
                    if not sb.origin_place_id and vtb.pickup_point_id:
                        sb.origin_place = vtb.pickup_point
                    sb.save(update_fields=['destination_place', 'origin_place', 'updated_at'])
                    open_bookings.append(sb)

        dropoffs = []
        for sb in open_bookings:
            seat_label = f"{sb.vehicle_seat.side}{sb.vehicle_seat.number}"
            dropoffs.append({
                'booking_id': str(sb.id),
                'vehicle_seat_id': str(sb.vehicle_seat_id),
                'seat_label': seat_label,
                'name': (sb.user.name if sb.user else None) or 'Guest',
                'pnr': '',
                'trip_amount': str(sb.trip_amount) if sb.trip_amount is not None else '0',
            })
        checked_out_seat_ids = {
            str(sid) for sid in SeatBooking.objects.filter(
                trip=trip, check_out_datetime__isnull=False,
            ).values_list('vehicle_seat_id', flat=True)
        }
        existing_seat_ids = {d['vehicle_seat_id'] for d in dropoffs}
        if trip.is_scheduled and trip.vehicle_schedule_id and trip.vehicle_id:
            vehicle_seat_by_key = {(vs.side, vs.number): vs for vs in trip.vehicle.seats.all()}
            for vtb in trip.vehicle_schedule.ticket_bookings.all():
                dest_id = vtb.destination_point_id or (route_end.id if route_end is not None else None)
                if dest_id != place.id:
                    continue
                for seat_item in _seat_to_list(vtb.seat):
                    side = str(seat_item.get('side', '')).strip()
                    try:
                        num = int(seat_item.get('number'))
                    except (TypeError, ValueError):
                        continue
                    vs = vehicle_seat_by_key.get((side, num))
                    if vs is None or str(vs.id) in existing_seat_ids or str(vs.id) in checked_out_seat_ids:
                        continue
                    existing_seat_ids.add(str(vs.id))
                    dropoffs.append({
                        'booking_id': f"ticket_{vtb.id}",
                        'vehicle_seat_id': str(vs.id),
                        'seat_label': f"{side}{num}",
                        'name': vtb.name or 'Guest',
                        'pnr': vtb.pnr or '',
                        'trip_amount': str(vtb.price) if vtb.price is not None else '0',
                    })

        auto_released = False
        # Free the seats only after the bus has crossed the stop, including
        # when the pin is on the other side of the road.
        if crossed and dropoffs:
            from .seat_booking_views import release_booking_at_destination
            for sb in open_bookings:
                release_booking_at_destination(sb, place)
            released_ids = {str(sb.vehicle_seat_id) for sb in open_bookings}
            for item in dropoffs:
                if item['vehicle_seat_id'] in released_ids:
                    continue
                VehicleSeat.objects.filter(pk=item['vehicle_seat_id'], status='booked').update(status='available')
            auto_released = True

        has_destination_booking = bool(dropoffs)
        return Response({
            'at_stop': {
                'place_id': str(place.id),
                'name': place.name,
                'announcement_text': announcement_text[:500] if announcement_text else '',
                'pickups': pickups,
                'dropoffs': dropoffs,
                'has_destination_booking': has_destination_booking,
                'crossed': crossed,
                'auto_released': auto_released,
            },
        }, status=status.HTTP_200_OK)

    return Response({'at_stop': None}, status=status.HTTP_200_OK)
