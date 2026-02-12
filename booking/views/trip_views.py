"""Trip views: start trip, end trip, CRUD"""
import math
import uuid
from datetime import date
from decimal import Decimal

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ..models import Trip, Vehicle, Route, Location
from core.models import User


def haversine_km(lat1, lon1, lat2, lon2):
    """Distance in km between two points (Haversine)."""
    lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return round(c * 6371, 4)


def _trip_to_response(trip):
    """Build trip dict for API response."""
    return {
        'id': str(trip.id),
        'trip_id': trip.trip_id,
        'vehicle': str(trip.vehicle.id),
        'driver': str(trip.driver.id),
        'route': str(trip.route.id),
        'start_time': trip.start_time.isoformat() if trip.start_time else None,
        'end_time': trip.end_time.isoformat() if trip.end_time else None,
        'remarks': trip.remarks or '',
        'is_scheduled': trip.is_scheduled,
        'vehicle_schedule': str(trip.vehicle_schedule.id) if trip.vehicle_schedule else None,
        'created_at': trip.created_at.isoformat(),
        'updated_at': trip.updated_at.isoformat(),
    }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trip_start_view(request):
    """Start a trip: vehicle must have active_driver (request.user) and active_route."""
    vehicle_id = request.POST.get('vehicle_id') or request.data.get('vehicle_id')
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

    # Check no active trip already
    if Trip.objects.filter(vehicle=vehicle, end_time__isnull=True).exists():
        return Response({'error': 'Vehicle already has an active trip'}, status=status.HTTP_400_BAD_REQUEST)

    trip_id = f"T-{date.today().strftime('%Y%m%d')}-{vehicle.id}-{uuid.uuid4().hex[:8]}"
    now = timezone.now()
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

    end_place = trip.route.end_point
    distance_km = haversine_km(
        float(latitude), float(longitude),
        float(end_place.latitude), float(end_place.longitude)
    )
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

    return Response({
        'trip': _trip_to_response(trip),
        'within_destination': distance_km <= stop_radius_km,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def trip_list_get_view(request):
    """List trips with filters."""
    from django.db.models import Q
    vehicle_id = request.query_params.get('vehicle')
    driver_id = request.query_params.get('driver')
    route_id = request.query_params.get('route')
    active_only = request.query_params.get('active_only')

    queryset = Trip.objects.select_related('vehicle', 'driver', 'route').all()
    if vehicle_id:
        queryset = queryset.filter(vehicle_id=vehicle_id)
    if driver_id:
        queryset = queryset.filter(driver_id=driver_id)
    if route_id:
        queryset = queryset.filter(route_id=route_id)
    if active_only and active_only.lower() == 'true':
        queryset = queryset.filter(end_time__isnull=True)

    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 10))
    start = (page - 1) * per_page
    end = start + per_page
    total = queryset.count()
    trips = queryset.order_by('-created_at')[start:end]

    return Response({
        'results': [_trip_to_response(t) for t in trips],
        'count': total,
        'page': page,
        'per_page': per_page,
    })


@api_view(['GET'])
def trip_detail_get_view(request, pk):
    """Get single trip."""
    try:
        trip = Trip.objects.select_related('vehicle', 'driver', 'route').get(pk=pk)
    except Trip.DoesNotExist:
        return Response({'error': 'Trip not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(_trip_to_response(trip))


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
