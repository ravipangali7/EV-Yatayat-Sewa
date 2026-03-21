from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from ..models import SuperSetting


def _require_superuser(request):
    if not request.user or not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    if not getattr(request.user, 'is_superuser', False):
        return Response({'error': 'Superuser access required'}, status=status.HTTP_403_FORBIDDEN)
    return None


def _setting_to_dict(setting):
    return {
        'id': str(setting.id),
        'per_km_charge': str(setting.per_km_charge),
        'initial_km': str(setting.initial_km) if getattr(setting, 'initial_km', None) is not None else None,
        'initial_km_charge': str(setting.initial_km_charge) if getattr(setting, 'initial_km_charge', None) is not None else None,
        'gps_threshold_second': str(setting.gps_threshold_second),
        'point_cover_radius': str(setting.point_cover_radius) if setting.point_cover_radius is not None else None,
        'minute_coverage_schedule': setting.minute_coverage_schedule,
        'seat_layout': getattr(setting, 'seat_layout', []) or [],
        'stop_point_announcement_header': getattr(setting, 'stop_point_announcement_header', '') or '',
        'short_trip_min_distance_for_booking': str(setting.short_trip_min_distance_for_booking) if getattr(setting, 'short_trip_min_distance_for_booking', None) is not None else None,
        'short_trip_max_distance_for_booking': str(setting.short_trip_max_distance_for_booking) if getattr(setting, 'short_trip_max_distance_for_booking', None) is not None else None,
        'luna_web_origin': getattr(setting, 'luna_web_origin', '') or '',
        'luna_api_token': getattr(setting, 'luna_api_token', '') or '',
        'created_at': setting.created_at.isoformat(),
        'updated_at': setting.updated_at.isoformat(),
    }


def _get_luna_token_from_request(request):
    if hasattr(request, 'data') and request.data is not None:
        if 'luna_api_token' in request.data:
            return request.data.get('luna_api_token')
    return request.POST.get('luna_api_token')


def _apply_luna_token_update(setting, request):
    """Update luna_api_token only when client sends a non-empty new value."""
    token = _get_luna_token_from_request(request)
    if token is None:
        return
    if isinstance(token, str) and token.strip() != '':
        setting.luna_api_token = token.strip()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def super_setting_list_get_view(request):
    """List all super settings (superuser only)."""
    denied = _require_superuser(request)
    if denied:
        return denied

    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 10))
    start = (page - 1) * per_page
    end = start + per_page

    queryset = SuperSetting.objects.all()
    total = queryset.count()
    settings = queryset[start:end]

    results = [_setting_to_dict(s) for s in settings]

    return Response({
        'results': results,
        'count': total,
        'page': page,
        'per_page': per_page
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def super_setting_list_post_view(request):
    """Create a new super setting (superuser only)."""
    denied = _require_superuser(request)
    if denied:
        return denied

    per_km_charge = request.POST.get('per_km_charge') or request.data.get('per_km_charge')

    if not per_km_charge:
        return Response({'error': 'Per KM charge is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        per_km_charge = Decimal(str(per_km_charge))
    except (ValueError, TypeError):
        return Response({'error': 'Invalid per_km_charge value'}, status=status.HTTP_400_BAD_REQUEST)

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

    short_trip_min = request.POST.get('short_trip_min_distance_for_booking') or request.data.get('short_trip_min_distance_for_booking')
    short_trip_max = request.POST.get('short_trip_max_distance_for_booking') or request.data.get('short_trip_max_distance_for_booking')
    try:
        short_trip_min_distance_for_booking = Decimal(str(short_trip_min)) if short_trip_min is not None and str(short_trip_min).strip() != '' else None
    except (ValueError, TypeError):
        short_trip_min_distance_for_booking = None
    try:
        short_trip_max_distance_for_booking = Decimal(str(short_trip_max)) if short_trip_max is not None and str(short_trip_max).strip() != '' else None
    except (ValueError, TypeError):
        short_trip_max_distance_for_booking = None

    initial_km = request.POST.get('initial_km') or request.data.get('initial_km')
    initial_km_charge = request.POST.get('initial_km_charge') or request.data.get('initial_km_charge')
    try:
        initial_km = Decimal(str(initial_km)) if initial_km is not None and str(initial_km).strip() != '' else None
    except (ValueError, TypeError):
        initial_km = None
    try:
        initial_km_charge = Decimal(str(initial_km_charge)) if initial_km_charge is not None and str(initial_km_charge).strip() != '' else None
    except (ValueError, TypeError):
        initial_km_charge = None

    luna_web_origin = (request.POST.get('luna_web_origin') or request.data.get('luna_web_origin') or '').strip()
    luna_api_token = (request.POST.get('luna_api_token') or request.data.get('luna_api_token') or '').strip()

    setting = SuperSetting.objects.create(
        per_km_charge=per_km_charge,
        initial_km=initial_km,
        initial_km_charge=initial_km_charge,
        gps_threshold_second=gps_threshold_second,
        point_cover_radius=point_cover_radius,
        minute_coverage_schedule=minute_coverage_schedule,
        seat_layout=seat_layout,
        stop_point_announcement_header=stop_point_announcement_header,
        short_trip_min_distance_for_booking=short_trip_min_distance_for_booking,
        short_trip_max_distance_for_booking=short_trip_max_distance_for_booking,
        luna_web_origin=luna_web_origin,
        luna_api_token=luna_api_token,
    )

    return Response(_setting_to_dict(setting), status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def super_setting_detail_get_view(request, pk):
    """Retrieve a single super setting (superuser only)."""
    denied = _require_superuser(request)
    if denied:
        return denied

    try:
        setting = SuperSetting.objects.get(pk=pk)
    except SuperSetting.DoesNotExist:
        return Response({'error': 'Super setting not found'}, status=status.HTTP_404_NOT_FOUND)

    return Response(_setting_to_dict(setting))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def super_setting_detail_post_view(request, pk):
    """Update/edit a super setting (superuser only)."""
    denied = _require_superuser(request)
    if denied:
        return denied

    try:
        setting = SuperSetting.objects.get(pk=pk)
    except SuperSetting.DoesNotExist:
        return Response({'error': 'Super setting not found'}, status=status.HTTP_404_NOT_FOUND)

    if 'per_km_charge' in request.POST or 'per_km_charge' in request.data:
        per_km_charge = request.POST.get('per_km_charge') or request.data.get('per_km_charge')
        try:
            setting.per_km_charge = Decimal(str(per_km_charge))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid per_km_charge value'}, status=status.HTTP_400_BAD_REQUEST)

    if 'initial_km' in request.POST or 'initial_km' in request.data:
        val = request.POST.get('initial_km') or request.data.get('initial_km')
        try:
            setting.initial_km = Decimal(str(val)) if val is not None and str(val).strip() != '' else None
        except (ValueError, TypeError):
            return Response({'error': 'Invalid initial_km value'}, status=status.HTTP_400_BAD_REQUEST)
    if 'initial_km_charge' in request.POST or 'initial_km_charge' in request.data:
        val = request.POST.get('initial_km_charge') or request.data.get('initial_km_charge')
        try:
            setting.initial_km_charge = Decimal(str(val)) if val is not None and str(val).strip() != '' else None
        except (ValueError, TypeError):
            return Response({'error': 'Invalid initial_km_charge value'}, status=status.HTTP_400_BAD_REQUEST)

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

    if 'short_trip_min_distance_for_booking' in request.POST or 'short_trip_min_distance_for_booking' in request.data:
        val = request.POST.get('short_trip_min_distance_for_booking') or request.data.get('short_trip_min_distance_for_booking')
        try:
            setting.short_trip_min_distance_for_booking = Decimal(str(val)) if val is not None and str(val).strip() != '' else None
        except (ValueError, TypeError):
            return Response({'error': 'Invalid short_trip_min_distance_for_booking value'}, status=status.HTTP_400_BAD_REQUEST)
    if 'short_trip_max_distance_for_booking' in request.POST or 'short_trip_max_distance_for_booking' in request.data:
        val = request.POST.get('short_trip_max_distance_for_booking') or request.data.get('short_trip_max_distance_for_booking')
        try:
            setting.short_trip_max_distance_for_booking = Decimal(str(val)) if val is not None and str(val).strip() != '' else None
        except (ValueError, TypeError):
            return Response({'error': 'Invalid short_trip_max_distance_for_booking value'}, status=status.HTTP_400_BAD_REQUEST)

    if 'luna_web_origin' in request.POST or 'luna_web_origin' in request.data:
        setting.luna_web_origin = (request.POST.get('luna_web_origin') or request.data.get('luna_web_origin') or '').strip()

    _apply_luna_token_update(setting, request)

    setting.save()

    return Response(_setting_to_dict(setting))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def super_setting_delete_get_view(request, pk):
    """Delete a super setting (superuser only)."""
    denied = _require_superuser(request)
    if denied:
        return denied

    try:
        setting = SuperSetting.objects.get(pk=pk)
        setting.delete()
        return Response({'message': 'Super setting deleted successfully'})
    except SuperSetting.DoesNotExist:
        return Response({'error': 'Super setting not found'}, status=status.HTTP_404_NOT_FOUND)
