"""VehicleSchedule CRUD views."""
from decimal import Decimal
from datetime import datetime

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from ..models import VehicleSchedule, Vehicle, Route


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


@api_view(['GET'])
def vehicle_schedule_list_get_view(request):
    vehicle_id = request.query_params.get('vehicle')
    route_id = request.query_params.get('route')
    queryset = VehicleSchedule.objects.select_related('vehicle', 'route').all()
    if vehicle_id:
        queryset = queryset.filter(vehicle_id=vehicle_id)
    if route_id:
        queryset = queryset.filter(route_id=route_id)
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 10))
    start = (page - 1) * per_page
    end = start + per_page
    total = queryset.count()
    items = queryset.order_by('-date', '-time')[start:end]
    return Response({
        'results': [_schedule_to_response(s) for s in items],
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
