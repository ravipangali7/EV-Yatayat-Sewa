"""VehicleSchedule CRUD views."""
from decimal import Decimal
from datetime import datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from ..models import VehicleSchedule, Vehicle, Route, Place, VehicleTicketBooking, RouteStopPoint


def _route_place_order(route):
    """Return dict place_id -> order (0=start, 1..n=stops, n+1=end)."""
    order_map = {route.start_point_id: 0}
    for i, sp in enumerate(route.stop_points.all().order_by('order')):
        order_map[sp.place_id] = i + 1
    order_map[route.end_point_id] = len(order_map)  # end is last
    return order_map


def _route_contains_place_before(route, from_place_id, to_place_id):
    """True if both places are on route and from comes before to."""
    order_map = _route_place_order(route)
    if from_place_id not in order_map or to_place_id not in order_map:
        return False
    return order_map[from_place_id] < order_map[to_place_id]


def _schedule_to_response(s):
    return {
        'id': str(s.id),
        'vehicle': str(s.vehicle.id),
        'route': str(s.route.id),
        'date': s.date.isoformat(),
        'time': s.time.strftime('%H:%M:%S') if s.time else None,
        'price': str(s.price),
        'created_at': s.created_at.isoformat(),
        'updated_at': s.updated_at.isoformat(),
    }


def _build_media_url(request, path):
    """Build absolute URL for media file."""
    if not path:
        return None
    if path.startswith('http'):
        return path
    base = request.build_absolute_uri('/').rstrip('/')
    return f"{base}{path}" if path.startswith('/') else f"{base}/{path}"


def _schedule_to_response_expanded(s, request):
    """Response with nested route (start/end place) and vehicle (name, vehicle_no, featured_image, images)."""
    route = s.route
    vehicle = s.vehicle
    route_data = {
        'id': str(route.id),
        'name': route.name,
        'start_point': {'id': str(route.start_point.id), 'name': route.start_point.name, 'code': route.start_point.code},
        'end_point': {'id': str(route.end_point.id), 'name': route.end_point.name, 'code': route.end_point.code},
    }
    featured_image = None
    if vehicle.featured_image:
        featured_image = _build_media_url(request, vehicle.featured_image.url)
    images = []
    for img in getattr(vehicle, '_prefetched_images', []) or []:
        if img.image:
            images.append(_build_media_url(request, img.image.url))
    if not images and hasattr(vehicle, 'images'):
        for img in vehicle.images.all()[:20]:
            if img.image:
                images.append(_build_media_url(request, img.image.url))
    vehicle_data = {
        'id': str(vehicle.id),
        'name': vehicle.name,
        'vehicle_no': vehicle.vehicle_no,
        'featured_image': featured_image,
        'images': images,
    }
    return {
        'id': str(s.id),
        'vehicle': str(s.vehicle.id),
        'route': str(s.route.id),
        'date': s.date.isoformat(),
        'time': (s.time.strftime('%H:%M') if s.time else None),
        'price': str(s.price),
        'created_at': s.created_at.isoformat(),
        'updated_at': s.updated_at.isoformat(),
        'route_details': route_data,
        'vehicle_details': vehicle_data,
    }


@api_view(['GET'])
def vehicle_schedule_start_places_view(request):
    """All places that appear on any vehicle_schedule route: start + stop_points + end, distinct, by name."""
    # Routes that have at least one VehicleSchedule
    route_ids = VehicleSchedule.objects.values_list('route_id', flat=True).distinct()
    routes = Route.objects.filter(id__in=route_ids).prefetch_related(
        'start_point', 'end_point', 'stop_points__place'
    )
    place_ids = set()
    for route in routes:
        place_ids.add(route.start_point_id)
        place_ids.add(route.end_point_id)
        for sp in route.stop_points.all():
            place_ids.add(sp.place_id)
    places = Place.objects.filter(id__in=place_ids).order_by('name')
    return Response([
        {'id': str(p.id), 'name': p.name, 'code': p.code}
        for p in places
    ])


@api_view(['GET'])
def vehicle_schedule_end_places_view(request):
    """Places that are 'after' from_place on some route (stops + end), so 'to' can be any downstream place."""
    from_place_id = request.query_params.get('from')
    if not from_place_id:
        return Response({'error': 'from (place id) is required'}, status=status.HTTP_400_BAD_REQUEST)
    route_ids = VehicleSchedule.objects.values_list('route_id', flat=True).distinct()
    routes = Route.objects.filter(id__in=route_ids).prefetch_related(
        'start_point', 'end_point', 'stop_points__place'
    )
    place_ids = set()
    for route in routes:
        order_map = _route_place_order(route)
        if int(from_place_id) not in order_map:
            continue
        from_order = order_map[int(from_place_id)]
        for pid, o in order_map.items():
            if o > from_order:
                place_ids.add(pid)
    places = Place.objects.filter(id__in=place_ids).order_by('name')
    return Response([
        {'id': str(p.id), 'name': p.name, 'code': p.code}
        for p in places
    ])


def _seat_to_list(seat):
    if isinstance(seat, list):
        return [x for x in seat if isinstance(x, dict) and x.get('side') is not None and x.get('number') is not None]
    if isinstance(seat, dict) and seat.get('side') is not None and seat.get('number') is not None:
        return [seat]
    return []


def _segment_overlap(a_start, a_end, b_start, b_end):
    """True if segment [a_start, a_end] overlaps [b_start, b_end] (order indices)."""
    return a_start < b_end and b_start < a_end


def _booked_seats_for_segment(schedule, from_order, to_order, order_map):
    """Set of (side, number) that are booked for a segment overlapping [from_order, to_order]."""
    booked = set()
    for b in VehicleTicketBooking.objects.filter(vehicle_schedule=schedule).select_related('pickup_point', 'destination_point'):
        seat_list = _seat_to_list(b.seat)
        if not seat_list:
            continue
        if b.pickup_point_id and b.destination_point_id and b.pickup_point_id in order_map and b.destination_point_id in order_map:
            b_start = order_map[b.pickup_point_id]
            b_end = order_map[b.destination_point_id]
        else:
            b_start = 0
            b_end = max(order_map.values()) + 1
        if not _segment_overlap(from_order, to_order, b_start, b_end):
            continue
        for s in seat_list:
            side = str(s.get('side', ''))
            try:
                num = int(s.get('number', 0))
            except (TypeError, ValueError):
                continue
            booked.add((side, num))
    return booked


@api_view(['GET'])
def vehicle_schedule_list_get_view(request):
    vehicle_id = request.query_params.get('vehicle')
    route_id = request.query_params.get('route')
    date_str = request.query_params.get('date')
    from_place = request.query_params.get('from_place')
    to_place = request.query_params.get('to_place')
    expand = request.query_params.get('expand', '').lower() in ('1', 'true', 'yes')

    queryset = VehicleSchedule.objects.select_related('vehicle', 'route', 'route__start_point', 'route__end_point').prefetch_related('route__stop_points__place')
    if vehicle_id:
        queryset = queryset.filter(vehicle_id=vehicle_id)
    if route_id:
        queryset = queryset.filter(route_id=route_id)
    if date_str:
        try:
            search_date = datetime.strptime(str(date_str).strip()[:10], '%Y-%m-%d').date()
            queryset = queryset.filter(date=search_date)
        except ValueError:
            pass
    # Segment search: both from_place and to_place => filter by route containing both in order
    if from_place and to_place:
        from_place_id = int(from_place)
        to_place_id = int(to_place)
        # Filter schedules whose route has from_place before to_place
        valid_schedule_ids = []
        for s in queryset:
            if _route_contains_place_before(s.route, from_place_id, to_place_id):
                valid_schedule_ids.append(s.id)
        queryset = queryset.filter(id__in=valid_schedule_ids)
    elif from_place:
        queryset = queryset.filter(route__start_point_id=from_place)
    elif to_place:
        queryset = queryset.filter(route__end_point_id=to_place)

    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 10))
    start = (page - 1) * per_page
    end = start + per_page
    total = queryset.count()
    items = list(queryset.order_by('date', 'time')[start:end])

    if expand and items:
        vehicle_ids = [s.vehicle_id for s in items]
        from django.db.models import Prefetch
        from ..models import VehicleImage
        vehicles_with_images = Vehicle.objects.filter(id__in=vehicle_ids).prefetch_related(
            Prefetch('images', queryset=VehicleImage.objects.all())
        )
        vehicle_map = {v.id: v for v in vehicles_with_images}

        def _count_seats_in_booking(seat_field):
            if isinstance(seat_field, list):
                return sum(1 for x in seat_field if isinstance(x, dict) and x.get('side') is not None and x.get('number') is not None)
            if isinstance(seat_field, dict) and seat_field.get('side') is not None and seat_field.get('number') is not None:
                return 1
            return 0

        results = []
        for s in items:
            v = vehicle_map.get(s.vehicle_id) or s.vehicle
            if hasattr(v, 'images'):
                s.vehicle._prefetched_images = list(v.images.all())[:20]
            row = _schedule_to_response_expanded(s, request)
            total_seats = s.vehicle.seats.count() if hasattr(s.vehicle, 'seats') else 0
            if total_seats == 0:
                layout = getattr(s.vehicle, 'seat_layout', None) or []
                total_seats = sum(1 for c in layout if c == 'x')
            if from_place and to_place:
                order_map = _route_place_order(s.route)
                from_order = order_map.get(int(from_place), -1)
                to_order = order_map.get(int(to_place), -1)
                booked_for_segment = _booked_seats_for_segment(s, from_order, to_order, order_map)
                seats_used = len(booked_for_segment)
            else:
                seats_used = 0
                for b in VehicleTicketBooking.objects.filter(vehicle_schedule=s).only('seat'):
                    seats_used += _count_seats_in_booking(b.seat)
            row['available_seats'] = max(0, total_seats - seats_used)
            row['total_seats'] = total_seats
            results.append(row)
    else:
        results = [_schedule_to_response(s) for s in items]

    return Response({
        'results': results,
        'count': total,
        'page': page,
        'per_page': per_page,
    })


@api_view(['POST'])
def vehicle_schedule_list_post_view(request):
    vehicle_id = request.POST.get('vehicle') or request.data.get('vehicle')
    route_id = request.POST.get('route') or request.data.get('route')
    date_str = request.POST.get('date') or request.data.get('date')
    time_str = request.POST.get('time') or request.data.get('time')
    price = request.POST.get('price') or request.data.get('price')
    if not vehicle_id or not route_id or not date_str or not time_str or not price:
        return Response({'error': 'vehicle, route, date, time, price are required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
        route = Route.objects.get(pk=route_id)
    except (Vehicle.DoesNotExist, Route.DoesNotExist):
        return Response({'error': 'Vehicle or Route not found'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        d = datetime.strptime(str(date_str).strip()[:10], '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Invalid date format (use YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        ts = str(time_str).strip()
        if len(ts) <= 5:  # HH:MM
            t = datetime.strptime(ts, '%H:%M').time()
        else:
            t = datetime.strptime(ts[:8], '%H:%M:%S').time()
    except ValueError:
        return Response({'error': 'Invalid time format (use HH:MM or HH:MM:SS)'}, status=status.HTTP_400_BAD_REQUEST)
    s = VehicleSchedule.objects.create(vehicle=vehicle, route=route, date=d, time=t, price=Decimal(str(price)))
    return Response(_schedule_to_response(s), status=status.HTTP_201_CREATED)


@api_view(['GET'])
def vehicle_schedule_detail_get_view(request, pk):
    try:
        s = VehicleSchedule.objects.select_related('vehicle', 'route').get(pk=pk)
    except VehicleSchedule.DoesNotExist:
        return Response({'error': 'Vehicle schedule not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(_schedule_to_response(s))


@api_view(['POST'])
def vehicle_schedule_detail_post_view(request, pk):
    try:
        s = VehicleSchedule.objects.get(pk=pk)
    except VehicleSchedule.DoesNotExist:
        return Response({'error': 'Vehicle schedule not found'}, status=status.HTTP_404_NOT_FOUND)
    data = request.data or request.POST
    if 'date' in data:
        try:
            s.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            pass
    if 'time' in data:
        try:
            ts = data['time']
            s.time = datetime.strptime(ts, '%H:%M').time() if len(ts) <= 8 else datetime.strptime(ts, '%H:%M:%S').time()
        except ValueError:
            pass
    if 'price' in data:
        s.price = Decimal(str(data['price']))
    if 'vehicle' in data:
        try:
            s.vehicle = Vehicle.objects.get(pk=data['vehicle'])
        except Vehicle.DoesNotExist:
            pass
    if 'route' in data:
        try:
            s.route = Route.objects.get(pk=data['route'])
        except Route.DoesNotExist:
            pass
    s.save()
    return Response(_schedule_to_response(s))


@api_view(['GET'])
def vehicle_schedule_delete_get_view(request, pk):
    try:
        s = VehicleSchedule.objects.get(pk=pk)
        s.delete()
        return Response({'message': 'Deleted'}, status=status.HTTP_200_OK)
    except VehicleSchedule.DoesNotExist:
        return Response({'error': 'Vehicle schedule not found'}, status=status.HTTP_404_NOT_FOUND)
