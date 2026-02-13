"""VehicleTicketBooking CRUD. pnr = EYS{ticket_id} on create."""
import json
import uuid
from decimal import Decimal

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse

from ..models import VehicleTicketBooking, VehicleSchedule, VehicleSeat
from core.models import User


def _seat_to_list(seat):
    """Normalize seat (dict or list) to list of {side, number}."""
    if isinstance(seat, list):
        return [s for s in seat if isinstance(s, dict) and s.get('side') is not None and s.get('number') is not None]
    if isinstance(seat, dict) and seat.get('side') is not None and seat.get('number') is not None:
        return [seat]
    return []


def _ticket_booking_to_response(b):
    seat = b.seat
    if not isinstance(seat, list):
        seat = _seat_to_list(seat) if seat else []
    return {
        'id': str(b.id),
        'user': str(b.user.id) if b.user else None,
        'is_guest': b.is_guest,
        'name': b.name,
        'phone': b.phone,
        'vehicle_schedule': str(b.vehicle_schedule.id),
        'ticket_id': b.ticket_id,
        'seat': seat,
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
    seats = request.POST.get('seats') or request.data.get('seats')
    price = request.POST.get('price') or request.data.get('price')
    is_paid = request.POST.get('is_paid') or request.data.get('is_paid', 'false')

    if not name or not phone or not vehicle_schedule_id:
        return Response({'error': 'name, phone, vehicle_schedule are required'}, status=status.HTTP_400_BAD_REQUEST)

    is_guest = is_guest.lower() == 'true' if isinstance(is_guest, str) else bool(is_guest)
    if not is_guest and not user_id:
        return Response({'error': 'user required when not guest'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        vs = VehicleSchedule.objects.select_related('vehicle').get(pk=vehicle_schedule_id)
    except VehicleSchedule.DoesNotExist:
        return Response({'error': 'Vehicle schedule not found'}, status=status.HTTP_404_NOT_FOUND)

    # Normalize seats: accept seats (list) or seat (single dict)
    seats_list = seats if seats is not None else seat
    if isinstance(seats_list, str):
        try:
            seats_list = json.loads(seats_list)
        except json.JSONDecodeError:
            seats_list = []
    seats_list = _seat_to_list(seats_list) if seats_list else []
    if not seats_list:
        return Response({'error': 'At least one seat is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Validate each seat exists on vehicle
    vehicle = vs.vehicle
    vehicle_seat_keys = set(
        (s.side, int(s.number)) for s in VehicleSeat.objects.filter(vehicle=vehicle).only('side', 'number')
    )
    for s in seats_list:
        side = s.get('side')
        number = s.get('number')
        try:
            number = int(number)
        except (TypeError, ValueError):
            return Response({'error': f'Invalid seat number for {side}{number}'}, status=status.HTTP_400_BAD_REQUEST)
        if (side, number) not in vehicle_seat_keys:
            return Response({'error': f'Seat {side}{number} does not exist on this vehicle'}, status=status.HTTP_400_BAD_REQUEST)

    # Already booked seats for this schedule
    booked = set()
    for existing in VehicleTicketBooking.objects.filter(vehicle_schedule=vs).only('seat'):
        for s in _seat_to_list(existing.seat):
            booked.add((str(s.get('side')), int(s.get('number', 0))))
    for s in seats_list:
        if (str(s.get('side')), int(s.get('number', 0))) in booked:
            return Response({'error': f"Seat {s.get('side')}{s.get('number')} is already booked for this schedule"}, status=status.HTTP_400_BAD_REQUEST)

    # Generate ticket_id if not provided
    if not ticket_id or not str(ticket_id).strip():
        ticket_id = str(uuid.uuid4().hex)[:12].upper()
    if VehicleTicketBooking.objects.filter(ticket_id=ticket_id).exists():
        ticket_id = str(uuid.uuid4().hex)[:12].upper()

    # Price = schedule price * number of seats (server-side)
    total_price = vs.price * len(seats_list)

    user = None
    if user_id:
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)

    pnr = f"EYS{ticket_id}"
    b = VehicleTicketBooking.objects.create(
        user=user,
        is_guest=is_guest,
        name=name,
        phone=phone,
        vehicle_schedule=vs,
        ticket_id=ticket_id,
        seat=seats_list,
        price=total_price,
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


@api_view(['GET'])
def vehicle_ticket_booking_ticket_pdf_view(request, pk):
    """Generate horizontal strip ticket PDF."""
    try:
        b = VehicleTicketBooking.objects.select_related('vehicle_schedule', 'vehicle_schedule__vehicle', 'vehicle_schedule__route').get(pk=pk)
    except VehicleTicketBooking.DoesNotExist:
        return Response({'error': 'Vehicle ticket booking not found'}, status=status.HTTP_404_NOT_FOUND)

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    import io

    # Long horizontal strip: e.g. 297mm x 45mm (landscape strip)
    width = 297 * mm
    height = 45 * mm
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(width, height))
    c.setPageSize((width, height))

    y = height - 8 * mm
    x = 10 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, f"PNR: {b.pnr}")
    x += 45 * mm
    c.drawString(x, y, f"Ticket: {b.ticket_id}")
    x += 40 * mm
    c.setFont("Helvetica", 9)
    c.drawString(x, y, f"Name: {b.name}  |  Phone: {b.phone}")
    x += 75 * mm
    vs = b.vehicle_schedule
    vehicle_name = vs.vehicle.name if vs.vehicle else "-"
    route_name = vs.route.name if vs.route else "-"
    date_str = vs.date.strftime('%Y-%m-%d') if vs.date else "-"
    time_str = vs.time.strftime('%H:%M') if vs.time else "-"
    c.drawString(x, y, f"Vehicle: {vehicle_name}  |  Route: {route_name}  |  {date_str} {time_str}")

    y -= 10 * mm
    x = 10 * mm
    seat_list = _seat_to_list(b.seat) if b.seat else []
    seats_str = ", ".join(f"{s.get('side', '')}{s.get('number', '')}" for s in seat_list) or "N/A"
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, f"Seats: {seats_str}")
    x += 80 * mm
    c.drawString(x, y, f"Price: Rs. {b.price}")
    x += 35 * mm
    c.drawString(x, y, f"Paid: {'Yes' if b.is_paid else 'No'}")

    c.save()
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket-{b.pnr}.pdf"'
    return response
