"""VehicleTicketBooking CRUD. pnr = EYS{ticket_id} on create."""
import json
from decimal import Decimal

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from ..models import VehicleTicketBooking, VehicleSchedule
from core.models import User


def _ticket_booking_to_response(b):
    return {
        'id': str(b.id),
        'user': str(b.user.id) if b.user else None,
        'is_guest': b.is_guest,
        'name': b.name,
        'phone': b.phone,
        'vehicle_schedule': str(b.vehicle_schedule.id),
        'ticket_id': b.ticket_id,
        'seat': b.seat,
        'price': str(b.price),
        'is_paid': b.is_paid,
        'pnr': b.pnr,
        'created_at': b.created_at.isoformat(),
        'updated_at': b.updated_at.isoformat(),
    }


@api_view(['GET'])
def vehicle_ticket_booking_list_get_view(request):
    vs_id = request.query_params.get('vehicle_schedule')
    user_id = request.query_params.get('user')
    queryset = VehicleTicketBooking.objects.select_related('user', 'vehicle_schedule').all()
    if vs_id:
        queryset = queryset.filter(vehicle_schedule_id=vs_id)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 10))
    start = (page - 1) * per_page
    end = start + per_page
    total = queryset.count()
    items = queryset.order_by('-created_at')[start:end]
    return Response({
        'results': [_ticket_booking_to_response(b) for b in items],
        'count': total,
        'page': page,
        'per_page': per_page,
    })


@api_view(['POST'])
def vehicle_ticket_booking_list_post_view(request):
    user_id = request.POST.get('user') or request.data.get('user')
    is_guest = request.POST.get('is_guest') or request.data.get('is_guest', 'false')
    name = request.POST.get('name') or request.data.get('name')
    phone = request.POST.get('phone') or request.data.get('phone')
    vehicle_schedule_id = request.POST.get('vehicle_schedule') or request.data.get('vehicle_schedule')
    ticket_id = request.POST.get('ticket_id') or request.data.get('ticket_id')
    seat = request.POST.get('seat') or request.data.get('seat')
    price = request.POST.get('price') or request.data.get('price')
    is_paid = request.POST.get('is_paid') or request.data.get('is_paid', 'false')

    if not name or not phone or not vehicle_schedule_id or not ticket_id or not price:
        return Response({'error': 'name, phone, vehicle_schedule, ticket_id, price are required'}, status=status.HTTP_400_BAD_REQUEST)

    is_guest = is_guest.lower() == 'true' if isinstance(is_guest, str) else bool(is_guest)
    if not is_guest and not user_id:
        return Response({'error': 'user required when not guest'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        vs = VehicleSchedule.objects.get(pk=vehicle_schedule_id)
    except VehicleSchedule.DoesNotExist:
        return Response({'error': 'Vehicle schedule not found'}, status=status.HTTP_404_NOT_FOUND)

    if VehicleTicketBooking.objects.filter(ticket_id=ticket_id).exists():
        return Response({'error': 'ticket_id already exists'}, status=status.HTTP_400_BAD_REQUEST)

    user = None
    if user_id:
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(seat, str):
        try:
            seat = json.loads(seat)
        except json.JSONDecodeError:
            seat = {}
    if not isinstance(seat, dict):
        seat = {}

    pnr = f"EYS{ticket_id}"
    b = VehicleTicketBooking.objects.create(
        user=user,
        is_guest=is_guest,
        name=name,
        phone=phone,
        vehicle_schedule=vs,
        ticket_id=ticket_id,
        seat=seat,
        price=Decimal(str(price)),
        is_paid=is_paid.lower() == 'true' if isinstance(is_paid, str) else bool(is_paid),
        pnr=pnr,
    )
    return Response(_ticket_booking_to_response(b), status=status.HTTP_201_CREATED)


@api_view(['GET'])
def vehicle_ticket_booking_detail_get_view(request, pk):
    try:
        b = VehicleTicketBooking.objects.select_related('user', 'vehicle_schedule').get(pk=pk)
    except VehicleTicketBooking.DoesNotExist:
        return Response({'error': 'Vehicle ticket booking not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(_ticket_booking_to_response(b))


@api_view(['POST'])
def vehicle_ticket_booking_detail_post_view(request, pk):
    try:
        b = VehicleTicketBooking.objects.get(pk=pk)
    except VehicleTicketBooking.DoesNotExist:
        return Response({'error': 'Vehicle ticket booking not found'}, status=status.HTTP_404_NOT_FOUND)
    data = request.data or request.POST
    if 'is_paid' in data:
        b.is_paid = data['is_paid'].lower() == 'true' if isinstance(data['is_paid'], str) else bool(data['is_paid'])
    if 'price' in data:
        b.price = Decimal(str(data['price']))
    b.save()
    return Response(_ticket_booking_to_response(b))


@api_view(['GET'])
def vehicle_ticket_booking_delete_get_view(request, pk):
    try:
        b = VehicleTicketBooking.objects.get(pk=pk)
        b.delete()
        return Response({'message': 'Deleted'}, status=status.HTTP_200_OK)
    except VehicleTicketBooking.DoesNotExist:
        return Response({'error': 'Vehicle ticket booking not found'}, status=status.HTTP_404_NOT_FOUND)
