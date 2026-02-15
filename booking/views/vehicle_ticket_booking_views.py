"""VehicleTicketBooking CRUD. pnr = EYS{ticket_id} on create."""
import json
import uuid
from decimal import Decimal

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from django.db import transaction as db_transaction

from ..models import VehicleTicketBooking, VehicleSchedule, VehicleSeat, Place
from core.models import User, Wallet
from core.services.wallet_transaction import create_wallet_transaction


def _seat_to_list(seat):
    """Normalize seat (dict or list) to list of {side, number}."""
    if isinstance(seat, list):
        return [s for s in seat if isinstance(s, dict) and s.get('side') is not None and s.get('number') is not None]
    if isinstance(seat, dict) and seat.get('side') is not None and seat.get('number') is not None:
        return [seat]
    return []


def _ticket_booking_to_response(b, include_schedule_details=False):
    seat = b.seat
    if not isinstance(seat, list):
        seat = _seat_to_list(seat) if seat else []
    data = {
        'id': str(b.id),
        'user': str(b.user.id) if b.user else None,
        'is_guest': b.is_guest,
        'booked_by': str(b.booked_by.id) if b.booked_by_id else None,
        'name': b.name,
        'phone': b.phone,
        'vehicle_schedule': str(b.vehicle_schedule.id),
        'pickup_point': str(b.pickup_point.id) if b.pickup_point_id else None,
        'destination_point': str(b.destination_point.id) if b.destination_point_id else None,
        'ticket_id': b.ticket_id,
        'seat': seat,
        'price': str(b.price),
        'is_paid': b.is_paid,
        'pnr': b.pnr,
        'created_at': b.created_at.isoformat(),
        'updated_at': b.updated_at.isoformat(),
    }
    if include_schedule_details and b.vehicle_schedule_id:
        vs = b.vehicle_schedule
        route = vs.route if vs else None
        data['schedule_details'] = {
            'date': vs.date.strftime('%Y-%m-%d') if vs and vs.date else None,
            'time': vs.time.strftime('%H:%M') if vs and vs.time else None,
            'price': str(vs.price) if vs else None,
            'vehicle_name': vs.vehicle.name if vs and vs.vehicle else None,
            'route_name': route.name if route else None,
            'start_point_name': route.start_point.name if route and route.start_point else None,
            'end_point_name': route.end_point.name if route and route.end_point else None,
        }
    return data


@api_view(['GET'])
def vehicle_ticket_booking_list_get_view(request):
    vs_id = request.query_params.get('vehicle_schedule')
    user_id = request.query_params.get('user')
    booked_by_id = request.query_params.get('booked_by')
    queryset = VehicleTicketBooking.objects.select_related('user', 'booked_by', 'vehicle_schedule', 'pickup_point', 'destination_point').all()
    if vs_id:
        queryset = queryset.filter(vehicle_schedule_id=vs_id)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    if booked_by_id:
        queryset = queryset.filter(booked_by_id=booked_by_id)
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 10))
    start = (page - 1) * per_page
    end = start + per_page
    total = queryset.count()
    items = queryset.order_by('-created_at')[start:end]
    expand = request.query_params.get('expand', '').lower() in ('1', 'true', 'yes')
    return Response({
        'results': [_ticket_booking_to_response(b, include_schedule_details=expand) for b in items],
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
    pickup_point_id = request.POST.get('pickup_point') or request.data.get('pickup_point')
    destination_point_id = request.POST.get('destination_point') or request.data.get('destination_point')
    ticket_id = request.POST.get('ticket_id') or request.data.get('ticket_id')
    seat = request.POST.get('seat') or request.data.get('seat')
    seats = request.POST.get('seats') or request.data.get('seats')
    price = request.POST.get('price') or request.data.get('price')
    is_paid = request.POST.get('is_paid') or request.data.get('is_paid', 'false')

    if not name or not phone or not vehicle_schedule_id:
        return Response({'error': 'name, phone, vehicle_schedule are required'}, status=status.HTTP_400_BAD_REQUEST)

    is_guest = is_guest.lower() == 'true' if isinstance(is_guest, str) else bool(is_guest)
    if not request.user.is_authenticated and not is_guest and not user_id:
        return Response({'error': 'user required when not guest'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        vs = VehicleSchedule.objects.select_related('vehicle', 'route').prefetch_related('route__stop_points__place').get(pk=vehicle_schedule_id)
    except VehicleSchedule.DoesNotExist:
        return Response({'error': 'Vehicle schedule not found'}, status=status.HTTP_404_NOT_FOUND)

    # Validate pickup_point and destination_point if provided (must be on route, pickup before destination)
    pickup_point = None
    destination_point = None
    if pickup_point_id or destination_point_id:
        route = vs.route
        # Build place_id -> order: start=0, stop_points by order 1..n, end=n+1
        place_order = {route.start_point_id: 0}
        stops = list(route.stop_points.all().order_by('order'))
        for i, sp in enumerate(stops):
            place_order[sp.place_id] = i + 1
        place_order[route.end_point_id] = len(stops) + 1
        if pickup_point_id:
            try:
                pickup_point = Place.objects.get(pk=pickup_point_id)
            except Place.DoesNotExist:
                return Response({'error': 'pickup_point not found'}, status=status.HTTP_400_BAD_REQUEST)
            if pickup_point.id not in place_order:
                return Response({'error': 'pickup_point is not on this schedule route'}, status=status.HTTP_400_BAD_REQUEST)
        if destination_point_id:
            try:
                destination_point = Place.objects.get(pk=destination_point_id)
            except Place.DoesNotExist:
                return Response({'error': 'destination_point not found'}, status=status.HTTP_400_BAD_REQUEST)
            if destination_point.id not in place_order:
                return Response({'error': 'destination_point is not on this schedule route'}, status=status.HTTP_400_BAD_REQUEST)
        if pickup_point and destination_point and place_order[pickup_point.id] >= place_order[destination_point.id]:
            return Response({'error': 'pickup_point must be before destination_point on the route'}, status=status.HTTP_400_BAD_REQUEST)
        if (pickup_point_id and not destination_point_id) or (destination_point_id and not pickup_point_id):
            return Response({'error': 'both pickup_point and destination_point are required when using segment booking'}, status=status.HTTP_400_BAD_REQUEST)

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

    # Already booked seats: by segment overlap when pickup/destination provided, else whole schedule
    route = vs.route
    place_order = {route.start_point_id: 0}
    stops = list(route.stop_points.all().order_by('order'))
    for i, sp in enumerate(stops):
        place_order[sp.place_id] = i + 1
    place_order[route.end_point_id] = len(stops) + 1
    from_order = place_order.get(pickup_point.id) if pickup_point else 0
    to_order = place_order.get(destination_point.id) if destination_point else (max(place_order.values()) + 1)

    booked = set()
    for existing in VehicleTicketBooking.objects.filter(vehicle_schedule=vs).select_related('pickup_point', 'destination_point').only('seat', 'pickup_point_id', 'destination_point_id'):
        seat_list = _seat_to_list(existing.seat)
        if not seat_list:
            continue
        if existing.pickup_point_id and existing.destination_point_id and existing.pickup_point_id in place_order and existing.destination_point_id in place_order:
            b_start = place_order[existing.pickup_point_id]
            b_end = place_order[existing.destination_point_id]
        else:
            b_start = 0
            b_end = max(place_order.values()) + 1
        # overlap: [from_order, to_order] vs [b_start, b_end]
        if not (to_order <= b_start or b_end <= from_order):
            for s in seat_list:
                booked.add((str(s.get('side')), int(s.get('number', 0))))
    for s in seats_list:
        if (str(s.get('side')), int(s.get('number', 0))) in booked:
            return Response({'error': f"Seat {s.get('side')}{s.get('number')} is already booked for this segment"}, status=status.HTTP_400_BAD_REQUEST)

    # Generate ticket_id if not provided
    if not ticket_id or not str(ticket_id).strip():
        ticket_id = str(uuid.uuid4().hex)[:12].upper()
    if VehicleTicketBooking.objects.filter(ticket_id=ticket_id).exists():
        ticket_id = str(uuid.uuid4().hex)[:12].upper()

    # Price = schedule price * number of seats (server-side)
    total_price = vs.price * len(seats_list)

    user = None
    booked_by = None
    # Logged-in user: always set user=request.user, is_guest=False (ignore client user/id)
    if request.user.is_authenticated:
        user = request.user
        is_guest = False
        if getattr(request.user, 'is_ticket_dealer', False):
            booked_by = request.user
    elif user_id:
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)

    pnr = f"EYS{ticket_id}"
    is_paid_val = is_paid.lower() == 'true' if isinstance(is_paid, str) else bool(is_paid)
    b = VehicleTicketBooking.objects.create(
        user=user,
        is_guest=is_guest,
        booked_by=booked_by,
        name=name,
        phone=phone,
        vehicle_schedule=vs,
        pickup_point=pickup_point,
        destination_point=destination_point,
        ticket_id=ticket_id,
        seat=seats_list,
        price=total_price,
        is_paid=is_paid_val,
        pnr=pnr,
    )
    return Response(_ticket_booking_to_response(b), status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vehicle_ticket_booking_pay_view(request, pk):
    """Pay for a booking from wallet. Creates deducted transaction; if dealer, adds commission."""
    try:
        b = VehicleTicketBooking.objects.select_related('vehicle_schedule').get(pk=pk)
    except VehicleTicketBooking.DoesNotExist:
        return Response({'error': 'Vehicle ticket booking not found'}, status=status.HTTP_404_NOT_FOUND)
    if b.is_paid:
        return Response({'error': 'Booking is already paid'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        wallet = Wallet.objects.get(user=request.user)
    except Wallet.DoesNotExist:
        return Response(
            {'error': 'Wallet not found', 'code': 'no_wallet'},
            status=status.HTTP_400_BAD_REQUEST
        )
    amount = b.price
    if wallet.balance < amount:
        return Response(
            {'error': 'Insufficient wallet balance. Please recharge.', 'code': 'insufficient_balance'},
            status=status.HTTP_400_BAD_REQUEST
        )
    commission = Decimal('0')
    if getattr(request.user, 'is_ticket_dealer', False) and getattr(request.user, 'ticket_commission', None):
        try:
            commission = amount * (request.user.ticket_commission / Decimal('100'))
        except (TypeError, ValueError):
            pass
    with db_transaction.atomic():
        wallet.balance -= amount
        wallet.save(update_fields=['balance', 'updated_at'])
        create_wallet_transaction(
            wallet=wallet,
            user=request.user,
            amount=amount,
            type='deducted',
            remarks=f'Ticket payment {b.pnr}',
            status='success',
        )
        b.is_paid = True
        b.save(update_fields=['is_paid', 'updated_at'])
        if commission > 0:
            wallet.balance += commission
            wallet.save(update_fields=['balance', 'updated_at'])
            create_wallet_transaction(
                wallet=wallet,
                user=request.user,
                amount=commission,
                type='add',
                remarks=f'Commission for {b.pnr}',
                status='success',
            )
    return Response(_ticket_booking_to_response(b, include_schedule_details=True))


@api_view(['GET'])
def vehicle_ticket_booking_detail_get_view(request, pk):
    try:
        b = VehicleTicketBooking.objects.select_related(
            'user', 'booked_by', 'vehicle_schedule', 'vehicle_schedule__vehicle',
            'vehicle_schedule__route', 'vehicle_schedule__route__start_point',
            'vehicle_schedule__route__end_point', 'pickup_point', 'destination_point'
        ).get(pk=pk)
    except VehicleTicketBooking.DoesNotExist:
        return Response({'error': 'Vehicle ticket booking not found'}, status=status.HTTP_404_NOT_FOUND)
    expand = request.query_params.get('expand', '').lower() in ('1', 'true', 'yes')
    return Response(_ticket_booking_to_response(b, include_schedule_details=expand))


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
    """Generate ticket PDF with 6:4 aspect ratio, EV Yatayat Sewa branding."""
    try:
        b = VehicleTicketBooking.objects.select_related(
            'vehicle_schedule', 'vehicle_schedule__vehicle', 'vehicle_schedule__route',
            'vehicle_schedule__route__start_point', 'vehicle_schedule__route__end_point',
            'pickup_point', 'destination_point'
        ).get(pk=pk)
    except VehicleTicketBooking.DoesNotExist:
        return Response({'error': 'Vehicle ticket booking not found'}, status=status.HTTP_404_NOT_FOUND)

    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    import io

    # 6:4 aspect ratio: 150mm x 100mm (6*25mm x 4*25mm)
    width = 150 * mm
    height = 100 * mm
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(width, height))
    c.setPageSize((width, height))

    margin = 6 * mm
    y = height - margin

    # Border
    c.setLineWidth(0.5)
    c.rect(2 * mm, 2 * mm, width - 4 * mm, height - 4 * mm)

    # EV Yatayat Sewa branding
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, y, "EV YATAYAT SEWA")
    y -= 6 * mm
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, y, "E-Ticket")
    y -= 8 * mm

    # Dashed perforation line (optional)
    c.setDash(2, 2)
    c.line(margin, y, width - margin, y)
    c.setDash([])
    y -= 6 * mm

    vs = b.vehicle_schedule
    route = vs.route if vs else None
    start_name = b.pickup_point.name if b.pickup_point else (route.start_point.name if route and route.start_point else "-")
    end_name = b.destination_point.name if b.destination_point else (route.end_point.name if route and route.end_point else "-")
    vehicle_name = vs.vehicle.name if vs and vs.vehicle else "-"
    date_str = vs.date.strftime('%d %b %Y') if vs and vs.date else "-"
    time_str = vs.time.strftime('%H:%M') if vs and vs.time else "-"

    # Row 1: PNR and Ticket ID
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, f"PNR: {b.pnr}")
    c.drawString(width / 2 + 2 * mm, y, f"Ticket: {b.ticket_id}")
    y -= 6 * mm

    # Row 2: Route
    c.setFont("Helvetica", 9)
    c.drawString(margin, y, "Route:")
    c.drawString(margin + 18 * mm, y, f"{start_name}  →  {end_name}")
    y -= 5 * mm

    # Row 3: Vehicle, Date, Time
    c.drawString(margin, y, f"Vehicle: {vehicle_name}")
    c.drawString(width / 2 + 2 * mm, y, f"Date: {date_str}  |  Time: {time_str}")
    y -= 6 * mm

    # Row 4: Passenger
    c.drawString(margin, y, f"Name: {b.name}")
    c.drawString(width / 2 + 2 * mm, y, f"Phone: {b.phone}")
    y -= 6 * mm

    seat_list = _seat_to_list(b.seat) if b.seat else []
    seats_str = ", ".join(f"{s.get('side', '')}{s.get('number', '')}" for s in seat_list) or "N/A"

    # Row 5: Seats, Price, Paid
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin, y, f"Seats: {seats_str}")
    c.drawString(margin + 70 * mm, y, f"Price: Rs. {b.price}")
    c.drawString(width - margin - 25 * mm, y, f"Paid: {'Yes' if b.is_paid else 'No'}")

    c.save()
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket-{b.pnr}.pdf"'
    return response
