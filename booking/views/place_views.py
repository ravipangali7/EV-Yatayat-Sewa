from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from decimal import Decimal
from ..models import Place
from ..transliteration import romanize


@api_view(['GET'])
def place_list_get_view(request):
    """List all places. Search matches name/code/address and supports Nepali/English (e.g. Ram matches राम)."""
    # Get query parameters
    search = (request.query_params.get('search') or '').strip()
    
    # Build queryset
    queryset = Place.objects.all()
    
    if search:
        # Direct match
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(code__icontains=search) |
            Q(address__icontains=search)
        )
        # Also match by romanized name (e.g. user types "Ram", place name is "राम")
        search_roman = romanize(search)
        if search_roman:
            all_place_ids = set(queryset.values_list('id', flat=True))
            for place in Place.objects.only('id', 'name').iterator(chunk_size=200):
                name_roman = romanize(place.name or '')
                if search_roman in name_roman or (search.lower() in (place.name or '').lower()):
                    all_place_ids.add(place.id)
            queryset = Place.objects.filter(id__in=all_place_ids)
    
    # Pagination
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 10))
    start = (page - 1) * per_page
    end = start + per_page
    
    total = queryset.count()
    places = queryset[start:end]
    
    # Return data without serializer
    results = []
    for place in places:
        results.append({
            'id': str(place.id),
            'name': place.name,
            'code': place.code,
            'latitude': str(place.latitude),
            'longitude': str(place.longitude),
            'address': place.address or '',
            'created_at': place.created_at.isoformat(),
            'updated_at': place.updated_at.isoformat(),
        })
    
    return Response({
        'results': results,
        'count': total,
        'page': page,
        'per_page': per_page,
        'stats': {'total_count': total},
    })


@api_view(['POST'])
def place_list_post_view(request):
    """Create a new place"""
    # Extract data from request.POST or request.data
    name = request.POST.get('name') or request.data.get('name')
    code = request.POST.get('code') or request.data.get('code')
    latitude = request.POST.get('latitude') or request.data.get('latitude')
    longitude = request.POST.get('longitude') or request.data.get('longitude')
    address = request.POST.get('address') or request.data.get('address') or None
    
    # Validate required fields
    if not name:
        return Response({'error': 'Name is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not code:
        return Response({'error': 'Code is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not latitude:
        return Response({'error': 'Latitude is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not longitude:
        return Response({'error': 'Longitude is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if code already exists
    if Place.objects.filter(code=code).exists():
        return Response({'error': 'Place with this code already exists'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Convert to Decimal
    try:
        latitude = Decimal(str(latitude))
        longitude = Decimal(str(longitude))
    except (ValueError, TypeError):
        return Response({'error': 'Invalid latitude or longitude values'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Create place directly without serializer
    place = Place.objects.create(
        name=name,
        code=code,
        latitude=latitude,
        longitude=longitude,
        address=address,
    )
    
    # Return response
    return Response({
        'id': str(place.id),
        'name': place.name,
        'code': place.code,
        'latitude': str(place.latitude),
        'longitude': str(place.longitude),
        'address': place.address or '',
        'created_at': place.created_at.isoformat(),
        'updated_at': place.updated_at.isoformat(),
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def place_detail_get_view(request, pk):
    """Retrieve a single place"""
    try:
        place = Place.objects.get(pk=pk)
    except Place.DoesNotExist:
        return Response({'error': 'Place not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Return data without serializer
    return Response({
        'id': str(place.id),
        'name': place.name,
        'code': place.code,
        'latitude': str(place.latitude),
        'longitude': str(place.longitude),
        'address': place.address or '',
        'created_at': place.created_at.isoformat(),
        'updated_at': place.updated_at.isoformat(),
    })


@api_view(['POST'])
def place_detail_post_view(request, pk):
    """Update/edit a place"""
    try:
        place = Place.objects.get(pk=pk)
    except Place.DoesNotExist:
        return Response({'error': 'Place not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Extract data from request.POST or request.data
    if 'name' in request.POST or 'name' in request.data:
        name = request.POST.get('name') or request.data.get('name')
        if name:
            place.name = name
    
    if 'code' in request.POST or 'code' in request.data:
        code = request.POST.get('code') or request.data.get('code')
        if code and code != place.code:
            # Check if new code already exists
            if Place.objects.filter(code=code).exclude(pk=pk).exists():
                return Response({'error': 'Place with this code already exists'}, status=status.HTTP_400_BAD_REQUEST)
            place.code = code
    
    if 'latitude' in request.POST or 'latitude' in request.data:
        latitude = request.POST.get('latitude') or request.data.get('latitude')
        try:
            place.latitude = Decimal(str(latitude))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid latitude value'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'longitude' in request.POST or 'longitude' in request.data:
        longitude = request.POST.get('longitude') or request.data.get('longitude')
        try:
            place.longitude = Decimal(str(longitude))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid longitude value'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'address' in request.POST or 'address' in request.data:
        address = request.POST.get('address') or request.data.get('address')
        place.address = address if address else None
    
    place.save()
    
    # Return updated data
    return Response({
        'id': str(place.id),
        'name': place.name,
        'code': place.code,
        'latitude': str(place.latitude),
        'longitude': str(place.longitude),
        'address': place.address or '',
        'created_at': place.created_at.isoformat(),
        'updated_at': place.updated_at.isoformat(),
    })


@api_view(['GET'])
def place_delete_get_view(request, pk):
    """Delete a place"""
    try:
        place = Place.objects.get(pk=pk)
        place.delete()
        return Response({'message': 'Place deleted successfully'})
    except Place.DoesNotExist:
        return Response({'error': 'Place not found'}, status=status.HTTP_404_NOT_FOUND)
