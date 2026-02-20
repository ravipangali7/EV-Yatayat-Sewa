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
            vs = VehicleSchedule.objects.select_related('vehicle', 'route', 'route__start_point').prefetch_related(
                'ticket_bookings', 'ticket_bookings__user'
            ).get(pk=vehicle_schedule_id, vehicle=vehicle, date=today)
        except VehicleSchedule.DoesNotExist:
            return Response({'error': 'Vehicle schedule not found or not for today'}, status=status.HTTP_404_NOT_FOUND)
        route = vs.route
        start_place = route.start_point
        start_addr = getattr(start_place, 'address', None) or f"{start_place.name}"

        with transaction.atomic():
            trip_id = f"T-{today.strftime('%Y%m%d')}-{vehicle.id}-{uuid.uuid4().hex[:8]}"
            trip = Trip.objects.create(
                vehicle=vehicle,
                driver=user,
                route=route,
                trip_id=trip_id,
                start_time=now,
                end_time=None,
                is_scheduled=True,
                vehicle_schedule=vs,
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
                    )
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
        for vs in VehicleSchedule.objects.filter(vehicle=vehicle, date=today).select_related('route', 'route__start_point').prefetch_related('ticket_bookings'):
            vs_minutes = vs.time.hour * 60 + vs.time.minute if vs.time else 0
            if abs(now_minutes - vs_minutes) > minute_coverage:
                continue
            start_place = vs.route.start_point
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
                    },
                    'tickets': tickets,
                }, status=status.HTTP_200_OK)

    # Normal trip
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
        confirm_out_of_range = confirm_out_of_range.lower() == 'true'
    else:
        confirm_out_of_range = bool(confirm_out_of_range)

    if not latitude or not longitude:
        return Response({'error': 'latitude and longitude are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        trip = Trip.objects.select_related('vehicle', 'route', 'route__end_point').get(pk=pk)
    except Trip.DoesNotExist:
        return Response({'error': 'Trip not found'}, status=status.HTTP_404_NOT_FOUND)

    if trip.end_time:
        return Response({'error': 'Trip is already ended'}, status=status.HTTP_400_BAD_REQUEST)

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
        return Response({
            'error': 'Check out all passengers first.',
            'pending_seat_bookings': pending_labels,
        }, status=status.HTTP_400_BAD_REQUEST)

    end_place = trip.route.end_point
    distance_km = haversine_km(
        float(latitude), float(longitude),
        float(end_place.latitude), float(end_place.longitude)
    )
    try:
        ss = SuperSetting.objects.latest('created_at')
        stop_radius_km = float(ss.point_cover_radius or 1.5)
    except (SuperSetting.DoesNotExist, (TypeError, ValueError)):
        stop_radius_km = 1.5

    if distance_km > stop_radius_km:
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
    trip.save()

    # Record location at end
    Location.objects.create(
        vehicle=trip.vehicle,
        trip=trip,
        latitude=Decimal(str(latitude)),
        longitude=Decimal(str(longitude)),
        speed=None,
    )

    # Clear vehicle active driver and active route when trip ends
    vehicle = trip.vehicle
    vehicle.active_driver = None
    vehicle.active_route = None
    vehicle.save()

    return Response({
        'trip': _trip_to_response(trip),
        'within_destination': distance_km <= stop_radius_km,
    }, status=status.HTTP_200_OK)


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
    """List trips with filters: vehicle, driver, route, active_only, search (trip_id), date_from, date_to."""
    from django.db.models import Q
    vehicle_id = request.query_params.get('vehicle')
    driver_id = request.query_params.get('driver')
    route_id = request.query_params.get('route')
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
    if active_only and active_only.lower() == 'true':
        queryset = queryset.filter(end_time__isnull=True)
    if search:
        queryset = queryset.filter(trip_id__icontains=search)
    if date_from:
        queryset = queryset.filter(start_time__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(start_time__date__lte=date_to)

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

    # Route with stop_points (place_id, order, announcement_text, lat/lng) for Flutter announcements
    route = trip.route
    if route:
        stop_points = []
        for rsp in route.stop_points.all().order_by('order'):
            place = rsp.place
            stop_points.append({
                'place_id': str(rsp.place_id),
                'order': rsp.order,
                'announcement_text': getattr(rsp, 'announcement_text', '') or '',
                'place_name': place.name if place else None,
                'place_code': place.code if place else None,
                'latitude': str(place.latitude) if place and place.latitude is not None else None,
                'longitude': str(place.longitude) if place and place.longitude is not None else None,
            })
        data['route'] = {
            'id': str(route.id),
            'name': route.name,
            'stop_points': stop_points,
        }
    else:
        data['route'] = None

    # Locations for this trip (ordered by created_at for polyline/playback)
    locations = list(trip.locations.all().order_by('created_at'))
    data['locations'] = [_location_to_response(loc) for loc in locations]

    # Seat bookings with full nested data
    seat_bookings = trip.seat_bookings.all().select_related(
        'user', 'vehicle', 'vehicle_seat', 'destination_place'
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
        trip = Trip.objects.select_related('route', 'route__start_point', 'route__end_point').prefetch_related(
            'route__stop_points__place', 'vehicle_schedule__ticket_bookings__pickup_point',
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

    # Ordered points: (kind, place, route_stop_point or None for start/end)
    points = []
    points.append(('start', route.start_point, None))
    for rsp in route.stop_points.all().order_by('order'):
        points.append(('stop', rsp.place, rsp))
    points.append(('end', route.end_point, None))

    lat_f, lng_f = float(lat), float(lng)
    for _kind, place, rsp in points:
        dist = haversine_km(lat_f, lng_f, float(place.latitude), float(place.longitude))
        if dist <= radius_km:
            if rsp is not None:
                custom = (getattr(rsp, 'announcement_text', None) or '').strip()
                if custom:
                    announcement_text = custom
                elif header:
                    name = (place.name or '').strip()
                    announcement_text = (header.replace('$x', name).replace('$X', name).strip() or name)[:500]
                else:
                    announcement_text = (place.name or '')[:500]
            else:
                announcement_text = ''
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
            dropoffs = []
            if not trip.is_scheduled:
                for sb in SeatBooking.objects.filter(
                    trip=trip,
                    destination_place_id=place.id,
                    check_out_datetime__isnull=True,
                ).select_related('vehicle_seat'):
                    seat_label = f"{sb.vehicle_seat.side}{sb.vehicle_seat.number}"
                    dropoffs.append({
                        'booking_id': str(sb.id),
                        'vehicle_seat_id': str(sb.vehicle_seat_id),
                        'seat_label': seat_label,
                        'name': sb.user.name if sb.user else 'Guest',
                        'pnr': '',
                        'trip_amount': str(sb.trip_amount) if sb.trip_amount is not None else '0',
                    })
            return Response({
                'at_stop': {
                    'place_id': str(place.id),
                    'name': place.name,
                    'announcement_text': announcement_text[:500] if announcement_text else '',
                    'pickups': pickups,
                    'dropoffs': dropoffs,
                },
            }, status=status.HTTP_200_OK)

    return Response({'at_stop': None}, status=status.HTTP_200_OK)
