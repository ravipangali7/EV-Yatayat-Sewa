"""Location views: create and list."""
from decimal import Decimal

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from ..models import Location, Vehicle, Trip


def _location_to_response(loc):
    v = getattr(loc, 'vehicle', None)
    t = getattr(loc, 'trip', None)
    return {
        'id': str(loc.id),
        'vehicle': str(loc.vehicle_id),
        'vehicle_name': v.name if v else None,
        'vehicle_no': v.vehicle_no if v else None,
        'trip': str(loc.trip_id) if loc.trip_id else None,
        'trip_id': t.trip_id if t else None,
        'latitude': str(loc.latitude),
        'longitude': str(loc.longitude),
        'speed': str(loc.speed) if loc.speed is not None else None,
        'course': str(loc.course) if getattr(loc, 'course', None) is not None else None,
        'created_at': loc.created_at.isoformat(),
        'updated_at': loc.updated_at.isoformat(),
    }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def location_list_post_view(request):
    """Create a location record."""
    vehicle_id = request.POST.get('vehicle') or request.data.get('vehicle')
    trip_id = request.POST.get('trip') or request.data.get('trip')
    latitude = request.POST.get('latitude') or request.data.get('latitude')
    longitude = request.POST.get('longitude') or request.data.get('longitude')
    speed = request.POST.get('speed') or request.data.get('speed')
    course = request.POST.get('course') or request.data.get('course')

    if not vehicle_id or not latitude or not longitude:
        return Response({'error': 'vehicle, latitude and longitude are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    trip = None
    if trip_id:
        try:
            trip = Trip.objects.get(pk=trip_id, vehicle=vehicle)
        except Trip.DoesNotExist:
            pass

    loc = Location.objects.create(
        vehicle=vehicle,
        trip=trip,
        latitude=Decimal(str(latitude)),
        longitude=Decimal(str(longitude)),
        speed=Decimal(str(speed)) if speed is not None else None,
        course=Decimal(str(course)) if course is not None else None,
    )
    return Response(_location_to_response(loc), status=status.HTTP_201_CREATED)


@api_view(['GET'])
def location_list_get_view(request):
    """List locations, optionally filter by vehicle and/or trip. Includes vehicle_name, vehicle_no, trip_id."""
    vehicle_id = request.query_params.get('vehicle')
    trip_id = request.query_params.get('trip')
    queryset = Location.objects.select_related('vehicle', 'trip').all().order_by('-created_at')
    if vehicle_id:
        queryset = queryset.filter(vehicle_id=vehicle_id)
    if trip_id:
        queryset = queryset.filter(trip_id=trip_id)

    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 50))
    start = (page - 1) * per_page
    end = start + per_page
    total = queryset.count()
    locations = queryset.order_by('-created_at')[start:end]

    return Response({
        'results': [_location_to_response(l) for l in locations],
        'count': total,
        'page': page,
        'per_page': per_page,
    })
