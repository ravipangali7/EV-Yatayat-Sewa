from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
import json
from ..models import Route, RouteStopPoint, Place


@api_view(['GET'])
def route_list_get_view(request):
    """List all routes"""
    # Get query parameters
    search = request.query_params.get('search', '')
    start_point = request.query_params.get('start_point', None)
    end_point = request.query_params.get('end_point', None)
    is_bidirectional = request.query_params.get('is_bidirectional', None)
    
    # Build queryset
    queryset = Route.objects.select_related('start_point', 'end_point').prefetch_related('stop_points__place').all()
    
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(start_point__name__icontains=search) |
            Q(end_point__name__icontains=search)
        )
    
    if start_point:
        queryset = queryset.filter(start_point_id=start_point)
    
    if end_point:
        queryset = queryset.filter(end_point_id=end_point)
    
    if is_bidirectional is not None:
        queryset = queryset.filter(is_bidirectional=is_bidirectional.lower() == 'true')
    
    # Pagination
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 10))
    start = (page - 1) * per_page
    end = start + per_page
    
    total = queryset.count()
    routes = queryset[start:end]
    
    # Return data without serializer
    results = []
    for route in routes:
        # Build stop_points array
        stop_points = []
        for sp in route.stop_points.all():
            stop_points.append({
                'id': str(sp.id),
                'route': str(sp.route.id),
                'place': str(sp.place.id),
                'place_details': {
                    'id': str(sp.place.id),
                    'name': sp.place.name,
                    'code': sp.place.code,
                    'latitude': str(sp.place.latitude),
                    'longitude': str(sp.place.longitude),
                },
                'order': sp.order,
                'created_at': sp.created_at.isoformat(),
                'updated_at': sp.updated_at.isoformat(),
            })
        
        results.append({
            'id': str(route.id),
            'name': route.name,
            'is_bidirectional': route.is_bidirectional,
            'start_point': str(route.start_point.id),
            'start_point_details': {
                'id': str(route.start_point.id),
                'name': route.start_point.name,
                'code': route.start_point.code,
                'latitude': str(route.start_point.latitude),
                'longitude': str(route.start_point.longitude),
            },
            'end_point': str(route.end_point.id),
            'end_point_details': {
                'id': str(route.end_point.id),
                'name': route.end_point.name,
                'code': route.end_point.code,
                'latitude': str(route.end_point.latitude),
                'longitude': str(route.end_point.longitude),
            },
            'stop_points': stop_points,
            'created_at': route.created_at.isoformat(),
            'updated_at': route.updated_at.isoformat(),
        })
    
    return Response({
        'results': results,
        'count': total,
        'page': page,
        'per_page': per_page
    })


@api_view(['POST'])
def route_list_post_view(request):
    """Create a new route"""
    # Extract data from request.POST or request.data
    name = request.POST.get('name') or request.data.get('name')
    start_point_id = request.POST.get('start_point') or request.data.get('start_point')
    end_point_id = request.POST.get('end_point') or request.data.get('end_point')
    is_bidirectional = request.POST.get('is_bidirectional') or request.data.get('is_bidirectional', 'false')
    stop_points_data = request.POST.get('stop_points') or request.data.get('stop_points', [])
    
    # Validate required fields
    if not name:
        return Response({'error': 'Name is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not start_point_id:
        return Response({'error': 'Start point is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not end_point_id:
        return Response({'error': 'End point is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if places exist
    try:
        start_point = Place.objects.get(pk=start_point_id)
    except Place.DoesNotExist:
        return Response({'error': 'Start point not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        end_point = Place.objects.get(pk=end_point_id)
    except Place.DoesNotExist:
        return Response({'error': 'End point not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Convert boolean
    is_bidirectional = is_bidirectional.lower() == 'true' if isinstance(is_bidirectional, str) else bool(is_bidirectional)
    
    # Parse stop_points if it's a string
    if isinstance(stop_points_data, str):
        try:
            stop_points_data = json.loads(stop_points_data)
        except:
            stop_points_data = []
    
    # Create route directly without serializer
    route = Route.objects.create(
        name=name,
        start_point=start_point,
        end_point=end_point,
        is_bidirectional=is_bidirectional,
    )
    
    # Handle stop points if provided
    if stop_points_data:
        for sp_data in stop_points_data:
            place_id = sp_data.get('place')
            order = sp_data.get('order', 0)
            if place_id:
                try:
                    place = Place.objects.get(pk=place_id)
                    RouteStopPoint.objects.create(
                        route=route,
                        place=place,
                        order=order
                    )
                except Place.DoesNotExist:
                    pass  # Skip invalid place
    
    # Reload route with stop points
    route.refresh_from_db()
    route = Route.objects.select_related('start_point', 'end_point').prefetch_related('stop_points').get(pk=route.id)
    
    # Build stop_points response
    stop_points = []
    for sp in route.stop_points.all():
        stop_points.append({
            'id': str(sp.id),
            'route': str(sp.route.id),
            'place': str(sp.place.id),
            'place_details': {
                'id': str(sp.place.id),
                'name': sp.place.name,
                'code': sp.place.code,
                'latitude': str(sp.place.latitude),
                'longitude': str(sp.place.longitude),
            },
            'order': sp.order,
            'created_at': sp.created_at.isoformat(),
            'updated_at': sp.updated_at.isoformat(),
        })
    
    # Return response
    return Response({
        'id': str(route.id),
        'name': route.name,
        'is_bidirectional': route.is_bidirectional,
        'start_point': str(route.start_point.id),
        'start_point_details': {
            'id': str(route.start_point.id),
            'name': route.start_point.name,
            'code': route.start_point.code,
            'latitude': str(route.start_point.latitude),
            'longitude': str(route.start_point.longitude),
        },
        'end_point': str(route.end_point.id),
        'end_point_details': {
            'id': str(route.end_point.id),
            'name': route.end_point.name,
            'code': route.end_point.code,
            'latitude': str(route.end_point.latitude),
            'longitude': str(route.end_point.longitude),
        },
        'stop_points': stop_points,
        'created_at': route.created_at.isoformat(),
        'updated_at': route.updated_at.isoformat(),
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def route_detail_get_view(request, pk):
    """Retrieve a single route"""
    try:
        route = Route.objects.select_related('start_point', 'end_point').prefetch_related('stop_points').get(pk=pk)
    except Route.DoesNotExist:
        return Response({'error': 'Route not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Build stop_points response
    stop_points = []
    for sp in route.stop_points.all():
        stop_points.append({
            'id': str(sp.id),
            'route': str(sp.route.id),
            'place': str(sp.place.id),
            'place_details': {
                'id': str(sp.place.id),
                'name': sp.place.name,
                'code': sp.place.code,
                'latitude': str(sp.place.latitude),
                'longitude': str(sp.place.longitude),
            },
            'order': sp.order,
            'created_at': sp.created_at.isoformat(),
            'updated_at': sp.updated_at.isoformat(),
        })
    
    # Return data without serializer
    return Response({
        'id': str(route.id),
        'name': route.name,
        'is_bidirectional': route.is_bidirectional,
        'start_point': str(route.start_point.id),
        'start_point_details': {
            'id': str(route.start_point.id),
            'name': route.start_point.name,
            'code': route.start_point.code,
            'latitude': str(route.start_point.latitude),
            'longitude': str(route.start_point.longitude),
        },
        'end_point': str(route.end_point.id),
        'end_point_details': {
            'id': str(route.end_point.id),
            'name': route.end_point.name,
            'code': route.end_point.code,
            'latitude': str(route.end_point.latitude),
            'longitude': str(route.end_point.longitude),
        },
        'stop_points': stop_points,
        'created_at': route.created_at.isoformat(),
        'updated_at': route.updated_at.isoformat(),
    })


@api_view(['POST'])
def route_detail_post_view(request, pk):
    """Update/edit a route"""
    try:
        route = Route.objects.select_related('start_point', 'end_point').prefetch_related('stop_points').get(pk=pk)
    except Route.DoesNotExist:
        return Response({'error': 'Route not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Extract data from request.POST or request.data
    if 'name' in request.POST or 'name' in request.data:
        name = request.POST.get('name') or request.data.get('name')
        if name:
            route.name = name
    
    if 'start_point' in request.POST or 'start_point' in request.data:
        start_point_id = request.POST.get('start_point') or request.data.get('start_point')
        try:
            start_point = Place.objects.get(pk=start_point_id)
            route.start_point = start_point
        except Place.DoesNotExist:
            return Response({'error': 'Start point not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'end_point' in request.POST or 'end_point' in request.data:
        end_point_id = request.POST.get('end_point') or request.data.get('end_point')
        try:
            end_point = Place.objects.get(pk=end_point_id)
            route.end_point = end_point
        except Place.DoesNotExist:
            return Response({'error': 'End point not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'is_bidirectional' in request.POST or 'is_bidirectional' in request.data:
        is_bidirectional = request.POST.get('is_bidirectional') or request.data.get('is_bidirectional')
        route.is_bidirectional = is_bidirectional.lower() == 'true' if isinstance(is_bidirectional, str) else bool(is_bidirectional)
    
    route.save()
    
    # Handle stop points update if provided
    if 'stop_points' in request.POST or 'stop_points' in request.data:
        stop_points_data = request.POST.get('stop_points') or request.data.get('stop_points', [])
        
        # Parse if string
        if isinstance(stop_points_data, str):
            try:
                stop_points_data = json.loads(stop_points_data)
            except:
                stop_points_data = []
        
        # Delete existing stop points
        RouteStopPoint.objects.filter(route=route).delete()
        
        # Create new stop points
        if stop_points_data:
            for sp_data in stop_points_data:
                place_id = sp_data.get('place')
                order = sp_data.get('order', 0)
                if place_id:
                    try:
                        place = Place.objects.get(pk=place_id)
                        RouteStopPoint.objects.create(
                            route=route,
                            place=place,
                            order=order
                        )
                    except Place.DoesNotExist:
                        pass  # Skip invalid place
    
    # Reload route with stop points
    route.refresh_from_db()
    route = Route.objects.select_related('start_point', 'end_point').prefetch_related('stop_points').get(pk=route.id)
    
    # Build stop_points response
    stop_points = []
    for sp in route.stop_points.all():
        stop_points.append({
            'id': str(sp.id),
            'route': str(sp.route.id),
            'place': str(sp.place.id),
            'place_details': {
                'id': str(sp.place.id),
                'name': sp.place.name,
                'code': sp.place.code,
                'latitude': str(sp.place.latitude),
                'longitude': str(sp.place.longitude),
            },
            'order': sp.order,
            'created_at': sp.created_at.isoformat(),
            'updated_at': sp.updated_at.isoformat(),
        })
    
    # Return updated data
    return Response({
        'id': str(route.id),
        'name': route.name,
        'is_bidirectional': route.is_bidirectional,
        'start_point': str(route.start_point.id),
        'start_point_details': {
            'id': str(route.start_point.id),
            'name': route.start_point.name,
            'code': route.start_point.code,
            'latitude': str(route.start_point.latitude),
            'longitude': str(route.start_point.longitude),
        },
        'end_point': str(route.end_point.id),
        'end_point_details': {
            'id': str(route.end_point.id),
            'name': route.end_point.name,
            'code': route.end_point.code,
            'latitude': str(route.end_point.latitude),
            'longitude': str(route.end_point.longitude),
        },
        'stop_points': stop_points,
        'created_at': route.created_at.isoformat(),
        'updated_at': route.updated_at.isoformat(),
    })


@api_view(['GET'])
def route_delete_get_view(request, pk):
    """Delete a route"""
    try:
        route = Route.objects.get(pk=pk)
        route.delete()
        return Response({'message': 'Route deleted successfully'})
    except Route.DoesNotExist:
        return Response({'error': 'Route not found'}, status=status.HTTP_404_NOT_FOUND)


# Route Stop Point Views
@api_view(['GET'])
def route_stop_point_list_get_view(request, route_id):
    """List all stop points for a route"""
    try:
        route = Route.objects.get(pk=route_id)
    except Route.DoesNotExist:
        return Response({'error': 'Route not found'}, status=status.HTTP_404_NOT_FOUND)
    
    stop_points = RouteStopPoint.objects.filter(route=route).select_related('place').order_by('order')
    
    # Return data without serializer
    results = []
    for sp in stop_points:
        results.append({
            'id': str(sp.id),
            'route': str(sp.route.id),
            'place': str(sp.place.id),
            'place_details': {
                'id': str(sp.place.id),
                'name': sp.place.name,
                'code': sp.place.code,
                'latitude': str(sp.place.latitude),
                'longitude': str(sp.place.longitude),
            },
            'order': sp.order,
            'created_at': sp.created_at.isoformat(),
            'updated_at': sp.updated_at.isoformat(),
        })
    
    return Response(results)


@api_view(['POST'])
def route_stop_point_list_post_view(request, route_id):
    """Create a new stop point for a route"""
    try:
        route = Route.objects.get(pk=route_id)
    except Route.DoesNotExist:
        return Response({'error': 'Route not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Extract data
    place_id = request.POST.get('place') or request.data.get('place')
    order = request.POST.get('order') or request.data.get('order', 0)
    
    if not place_id:
        return Response({'error': 'Place is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        place = Place.objects.get(pk=place_id)
    except Place.DoesNotExist:
        return Response({'error': 'Place not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        order = int(order)
    except (ValueError, TypeError):
        order = 0
    
    # Create stop point directly without serializer
    stop_point = RouteStopPoint.objects.create(
        route=route,
        place=place,
        order=order
    )
    
    return Response({
        'id': str(stop_point.id),
        'route': str(stop_point.route.id),
        'place': str(stop_point.place.id),
        'place_details': {
            'id': str(stop_point.place.id),
            'name': stop_point.place.name,
            'code': stop_point.place.code,
            'latitude': str(stop_point.place.latitude),
            'longitude': str(stop_point.place.longitude),
        },
        'order': stop_point.order,
        'created_at': stop_point.created_at.isoformat(),
        'updated_at': stop_point.updated_at.isoformat(),
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def route_stop_point_detail_get_view(request, route_id, pk):
    """Retrieve a single stop point"""
    try:
        stop_point = RouteStopPoint.objects.select_related('place').get(pk=pk, route_id=route_id)
    except RouteStopPoint.DoesNotExist:
        return Response({'error': 'Stop point not found'}, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'id': str(stop_point.id),
        'route': str(stop_point.route.id),
        'place': str(stop_point.place.id),
        'place_details': {
            'id': str(stop_point.place.id),
            'name': stop_point.place.name,
            'code': stop_point.place.code,
            'latitude': str(stop_point.place.latitude),
            'longitude': str(stop_point.place.longitude),
        },
        'order': stop_point.order,
        'created_at': stop_point.created_at.isoformat(),
        'updated_at': stop_point.updated_at.isoformat(),
    })


@api_view(['POST'])
def route_stop_point_detail_post_view(request, route_id, pk):
    """Update/edit a stop point"""
    try:
        stop_point = RouteStopPoint.objects.select_related('place').get(pk=pk, route_id=route_id)
    except RouteStopPoint.DoesNotExist:
        return Response({'error': 'Stop point not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Extract data
    if 'place' in request.POST or 'place' in request.data:
        place_id = request.POST.get('place') or request.data.get('place')
        try:
            place = Place.objects.get(pk=place_id)
            stop_point.place = place
        except Place.DoesNotExist:
            return Response({'error': 'Place not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'order' in request.POST or 'order' in request.data:
        order = request.POST.get('order') or request.data.get('order')
        try:
            stop_point.order = int(order)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid order value'}, status=status.HTTP_400_BAD_REQUEST)
    
    stop_point.save()
    
    return Response({
        'id': str(stop_point.id),
        'route': str(stop_point.route.id),
        'place': str(stop_point.place.id),
        'place_details': {
            'id': str(stop_point.place.id),
            'name': stop_point.place.name,
            'code': stop_point.place.code,
            'latitude': str(stop_point.place.latitude),
            'longitude': str(stop_point.place.longitude),
        },
        'order': stop_point.order,
        'created_at': stop_point.created_at.isoformat(),
        'updated_at': stop_point.updated_at.isoformat(),
    })


@api_view(['GET'])
def route_stop_point_delete_get_view(request, route_id, pk):
    """Delete a stop point"""
    try:
        stop_point = RouteStopPoint.objects.get(pk=pk, route_id=route_id)
        stop_point.delete()
        return Response({'message': 'Stop point deleted successfully'})
    except RouteStopPoint.DoesNotExist:
        return Response({'error': 'Stop point not found'}, status=status.HTTP_404_NOT_FOUND)
