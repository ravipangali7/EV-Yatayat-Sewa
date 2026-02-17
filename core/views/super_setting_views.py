from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from ..models import SuperSetting


@api_view(['GET'])
def super_setting_list_get_view(request):
    """List all super settings"""
    # Get query parameters
    search = request.query_params.get('search', '')
    
    # Build queryset
    queryset = SuperSetting.objects.all()
    
    # Pagination
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 10))
    start = (page - 1) * per_page
    end = start + per_page
    
    total = queryset.count()
    settings = queryset[start:end]
    
    # Return data without serializer
    results = []
    for setting in settings:
        results.append({
            'id': str(setting.id),
            'per_km_charge': str(setting.per_km_charge),
            'gps_threshold_second': str(setting.gps_threshold_second),
            'point_cover_radius': str(setting.point_cover_radius) if setting.point_cover_radius is not None else None,
            'minute_coverage_schedule': setting.minute_coverage_schedule,
            'seat_layout': getattr(setting, 'seat_layout', []) or [],
            'stop_point_announcement_header': getattr(setting, 'stop_point_announcement_header', '') or '',
            'created_at': setting.created_at.isoformat(),
            'updated_at': setting.updated_at.isoformat(),
        })
    
    return Response({
        'results': results,
        'count': total,
        'page': page,
        'per_page': per_page
    })


@api_view(['POST'])
def super_setting_list_post_view(request):
    """Create a new super setting"""
    # Extract data from request.POST or request.data
    per_km_charge = request.POST.get('per_km_charge') or request.data.get('per_km_charge')
    
    # Validate required fields
    if not per_km_charge:
        return Response({'error': 'Per KM charge is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Convert to Decimal
    try:
        per_km_charge = Decimal(str(per_km_charge))
    except (ValueError, TypeError):
        return Response({'error': 'Invalid per_km_charge value'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Optional gps_threshold_second (default 5)
    gps_threshold_second = request.POST.get('gps_threshold_second') or request.data.get('gps_threshold_second', '5')
    try:
        gps_threshold_second = Decimal(str(gps_threshold_second))
    except (ValueError, TypeError):
        gps_threshold_second = Decimal('5')
    point_cover_radius = request.POST.get('point_cover_radius') or request.data.get('point_cover_radius')
    minute_coverage_schedule = request.POST.get('minute_coverage_schedule') or request.data.get('minute_coverage_schedule')
    try:
        point_cover_radius = Decimal(str(point_cover_radius)) if point_cover_radius is not None else None
    except (ValueError, TypeError):
        point_cover_radius = None
    try:
        minute_coverage_schedule = int(minute_coverage_schedule) if minute_coverage_schedule is not None else None
    except (ValueError, TypeError):
        minute_coverage_schedule = None
    
    seat_layout = request.POST.get('seat_layout') or request.data.get('seat_layout')
    if seat_layout is not None and isinstance(seat_layout, str):
        import json
        try:
            seat_layout = json.loads(seat_layout) if seat_layout else []
        except json.JSONDecodeError:
            seat_layout = []
    if not isinstance(seat_layout, list):
        seat_layout = []
    
    stop_point_announcement_header = (request.POST.get('stop_point_announcement_header') or request.data.get('stop_point_announcement_header') or '').strip()[:255]
    
    # Create setting directly without serializer
    setting = SuperSetting.objects.create(
        per_km_charge=per_km_charge,
        gps_threshold_second=gps_threshold_second,
        point_cover_radius=point_cover_radius,
        minute_coverage_schedule=minute_coverage_schedule,
        seat_layout=seat_layout,
        stop_point_announcement_header=stop_point_announcement_header,
    )
    
    # Return response
    return Response({
        'id': str(setting.id),
        'per_km_charge': str(setting.per_km_charge),
        'gps_threshold_second': str(setting.gps_threshold_second),
        'point_cover_radius': str(setting.point_cover_radius) if setting.point_cover_radius is not None else None,
        'minute_coverage_schedule': setting.minute_coverage_schedule,
        'seat_layout': setting.seat_layout,
        'stop_point_announcement_header': getattr(setting, 'stop_point_announcement_header', '') or '',
        'created_at': setting.created_at.isoformat(),
        'updated_at': setting.updated_at.isoformat(),
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def super_setting_detail_get_view(request, pk):
    """Retrieve a single super setting"""
    try:
        setting = SuperSetting.objects.get(pk=pk)
    except SuperSetting.DoesNotExist:
        return Response({'error': 'Super setting not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Return data without serializer
    return Response({
        'id': str(setting.id),
        'per_km_charge': str(setting.per_km_charge),
        'gps_threshold_second': str(setting.gps_threshold_second),
        'point_cover_radius': str(setting.point_cover_radius) if setting.point_cover_radius is not None else None,
        'minute_coverage_schedule': setting.minute_coverage_schedule,
        'seat_layout': getattr(setting, 'seat_layout', []) or [],
        'stop_point_announcement_header': getattr(setting, 'stop_point_announcement_header', '') or '',
        'created_at': setting.created_at.isoformat(),
        'updated_at': setting.updated_at.isoformat(),
    })


@api_view(['POST'])
def super_setting_detail_post_view(request, pk):
    """Update/edit a super setting"""
    try:
        setting = SuperSetting.objects.get(pk=pk)
    except SuperSetting.DoesNotExist:
        return Response({'error': 'Super setting not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Extract data from request.POST or request.data
    if 'per_km_charge' in request.POST or 'per_km_charge' in request.data:
        per_km_charge = request.POST.get('per_km_charge') or request.data.get('per_km_charge')
        try:
            setting.per_km_charge = Decimal(str(per_km_charge))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid per_km_charge value'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'gps_threshold_second' in request.POST or 'gps_threshold_second' in request.data:
        gps_threshold_second = request.POST.get('gps_threshold_second') or request.data.get('gps_threshold_second')
        try:
            setting.gps_threshold_second = Decimal(str(gps_threshold_second))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid gps_threshold_second value'}, status=status.HTTP_400_BAD_REQUEST)
    if 'point_cover_radius' in request.POST or 'point_cover_radius' in request.data:
        point_cover_radius = request.POST.get('point_cover_radius') or request.data.get('point_cover_radius')
        try:
            setting.point_cover_radius = Decimal(str(point_cover_radius)) if point_cover_radius is not None else None
        except (ValueError, TypeError):
            return Response({'error': 'Invalid point_cover_radius value'}, status=status.HTTP_400_BAD_REQUEST)
    if 'minute_coverage_schedule' in request.POST or 'minute_coverage_schedule' in request.data:
        minute_coverage_schedule = request.POST.get('minute_coverage_schedule') or request.data.get('minute_coverage_schedule')
        try:
            setting.minute_coverage_schedule = int(minute_coverage_schedule) if minute_coverage_schedule is not None else None
        except (ValueError, TypeError):
            return Response({'error': 'Invalid minute_coverage_schedule value'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'seat_layout' in request.POST or 'seat_layout' in request.data:
        seat_layout = request.POST.get('seat_layout') or request.data.get('seat_layout')
        if seat_layout is not None:
            if isinstance(seat_layout, str):
                import json
                try:
                    seat_layout = json.loads(seat_layout) if seat_layout else []
                except json.JSONDecodeError:
                    seat_layout = []
            if isinstance(seat_layout, list):
                setting.seat_layout = seat_layout
    
    if 'stop_point_announcement_header' in request.POST or 'stop_point_announcement_header' in request.data:
        val = request.POST.get('stop_point_announcement_header') or request.data.get('stop_point_announcement_header')
        setting.stop_point_announcement_header = (val or '').strip()[:255]
    
    setting.save()
    
    # Return updated data
    return Response({
        'id': str(setting.id),
        'per_km_charge': str(setting.per_km_charge),
        'gps_threshold_second': str(setting.gps_threshold_second),
        'point_cover_radius': str(setting.point_cover_radius) if setting.point_cover_radius is not None else None,
        'minute_coverage_schedule': setting.minute_coverage_schedule,
        'seat_layout': getattr(setting, 'seat_layout', []) or [],
        'stop_point_announcement_header': getattr(setting, 'stop_point_announcement_header', '') or '',
        'created_at': setting.created_at.isoformat(),
        'updated_at': setting.updated_at.isoformat(),
    })


@api_view(['GET'])
def super_setting_delete_get_view(request, pk):
    """Delete a super setting"""
    try:
        setting = SuperSetting.objects.get(pk=pk)
        setting.delete()
        return Response({'message': 'Super setting deleted successfully'})
    except SuperSetting.DoesNotExist:
        return Response({'error': 'Super setting not found'}, status=status.HTTP_404_NOT_FOUND)
