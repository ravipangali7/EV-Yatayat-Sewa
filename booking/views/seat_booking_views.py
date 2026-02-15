from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from decimal import Decimal
from datetime import datetime
import math
import json
from django.db.models import F
from ..models import Vehicle, VehicleSeat, SeatBooking, Trip
from core.models import User, SuperSetting, Wallet, Transaction
from ..serializers import SeatBookingSerializer


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points on Earth (in kilometers)
    using the Haversine formula
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return Decimal(str(round(c * r, 2)))


@api_view(['GET'])
def seat_booking_list_get_view(request):
    """List all seat bookings"""
    # Get query parameters
    search = request.query_params.get('search', '')
    vehicle_id = request.query_params.get('vehicle', None)
    user_id = request.query_params.get('user', None)
    is_guest = request.query_params.get('is_guest', None)
    is_paid = request.query_params.get('is_paid', None)
    vehicle_seat_id = request.query_params.get('vehicle_seat', None)
    
    # Build queryset
    queryset = SeatBooking.objects.select_related(
        'user', 'vehicle', 'vehicle_seat', 'trip'
    ).all()
    
    if search:
        queryset = queryset.filter(
            Q(vehicle__name__icontains=search) |
            Q(vehicle__vehicle_no__icontains=search) |
            Q(user__name__icontains=search) |
            Q(user__phone__icontains=search) |
            Q(check_in_address__icontains=search) |
            Q(check_out_address__icontains=search)
        )
    
    if vehicle_id:
        queryset = queryset.filter(vehicle_id=vehicle_id)
    
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    
    if is_guest is not None:
        queryset = queryset.filter(is_guest=is_guest.lower() == 'true')
    
    if is_paid is not None:
        queryset = queryset.filter(is_paid=is_paid.lower() == 'true')
    
    if vehicle_seat_id:
        queryset = queryset.filter(vehicle_seat_id=vehicle_seat_id)
    
    # Pagination
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 10))
    start = (page - 1) * per_page
    end = start + per_page
    
    total = queryset.count()
    bookings = queryset.order_by('-created_at')[start:end]
    
    # Serialize results
    serializer = SeatBookingSerializer(bookings, many=True)
    
    return Response({
        'results': serializer.data,
        'count': total,
        'page': page,
        'per_page': per_page
    })


def _create_seat_booking(request):
    """Helper function to create a seat booking - extracted to avoid double @api_view wrapping"""
    # Extract data from request.POST or request.data
    user_id = request.POST.get('user') or request.data.get('user') or None
    is_guest = request.POST.get('is_guest') or request.data.get('is_guest', 'false')
    vehicle_id = request.POST.get('vehicle') or request.data.get('vehicle')
    vehicle_seat_id = request.POST.get('vehicle_seat') or request.data.get('vehicle_seat')
    check_in_lat = request.POST.get('check_in_lat') or request.data.get('check_in_lat')
    check_in_lng = request.POST.get('check_in_lng') or request.data.get('check_in_lng')
    check_in_datetime = request.POST.get('check_in_datetime') or request.data.get('check_in_datetime')
    check_in_address = request.POST.get('check_in_address') or request.data.get('check_in_address', '')
    
    # Validate required fields
    if not vehicle_id:
        return Response({'error': 'Vehicle is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not vehicle_seat_id:
        return Response({'error': 'Vehicle seat is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not check_in_lat or not check_in_lng:
        return Response({'error': 'Check-in location (lat/lng) is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not check_in_datetime:
        return Response({'error': 'Check-in datetime is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Convert boolean
    is_guest = is_guest.lower() == 'true' if isinstance(is_guest, str) else bool(is_guest)
    
    # Validate user/guest logic
    if not is_guest and not user_id:
        return Response({'error': 'User is required when is_guest is false'}, status=status.HTTP_400_BAD_REQUEST)
    if is_guest and user_id:
        return Response({'error': 'User should not be provided when is_guest is true'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if vehicle and seat exist
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vehicle_seat = VehicleSeat.objects.get(pk=vehicle_seat_id, vehicle=vehicle)
    except VehicleSeat.DoesNotExist:
        return Response({'error': 'Vehicle seat not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if seat is available
    if vehicle_seat.status != 'available':
        return Response({'error': 'Seat is not available'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Get user if provided
    user = None
    if user_id:
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Parse datetime
    try:
        if isinstance(check_in_datetime, str):
            check_in_datetime = datetime.fromisoformat(check_in_datetime.replace('Z', '+00:00'))
        else:
            check_in_datetime = datetime.fromisoformat(str(check_in_datetime).replace('Z', '+00:00'))
    except:
        return Response({'error': 'Invalid check_in_datetime format'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Link to active trip if vehicle has one
    active_trip = Trip.objects.filter(vehicle=vehicle, end_time__isnull=True).order_by('-start_time').first()
    
    # Create booking
    booking = SeatBooking.objects.create(
        user=user,
        is_guest=is_guest,
        vehicle=vehicle,
        vehicle_seat=vehicle_seat,
        trip=active_trip,
        check_in_lat=Decimal(str(check_in_lat)),
        check_in_lng=Decimal(str(check_in_lng)),
        check_in_datetime=check_in_datetime,
        check_in_address=check_in_address,
    )
    
    # Update seat status to booked
    vehicle_seat.status = 'booked'
    vehicle_seat.save()
    
    # Serialize and return
    serializer = SeatBookingSerializer(booking)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def seat_booking_list_post_view(request):
    """Create a new seat booking"""
    return _create_seat_booking(request)


@api_view(['GET'])
def seat_booking_detail_get_view(request, pk):
    """Retrieve a single seat booking"""
    try:
        booking = SeatBooking.objects.select_related('user', 'vehicle', 'vehicle_seat', 'trip').get(pk=pk)
    except SeatBooking.DoesNotExist:
        return Response({'error': 'Seat booking not found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = SeatBookingSerializer(booking)
    return Response(serializer.data)


@api_view(['POST'])
def seat_booking_detail_post_view(request, pk):
    """Update/edit a seat booking"""
    try:
        booking = SeatBooking.objects.get(pk=pk)
    except SeatBooking.DoesNotExist:
        return Response({'error': 'Seat booking not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Extract data
    is_paid = request.POST.get('is_paid') or request.data.get('is_paid')
    check_out_lat = request.POST.get('check_out_lat') or request.data.get('check_out_lat')
    check_out_lng = request.POST.get('check_out_lng') or request.data.get('check_out_lng')
    check_out_datetime = request.POST.get('check_out_datetime') or request.data.get('check_out_datetime')
    check_out_address = request.POST.get('check_out_address') or request.data.get('check_out_address')
    trip_distance = request.POST.get('trip_distance') or request.data.get('trip_distance')
    trip_duration = request.POST.get('trip_duration') or request.data.get('trip_duration')
    trip_amount = request.POST.get('trip_amount') or request.data.get('trip_amount')
    
    # Update fields
    if is_paid is not None:
        booking.is_paid = is_paid.lower() == 'true' if isinstance(is_paid, str) else bool(is_paid)
    
    if check_out_lat and check_out_lng:
        booking.check_out_lat = Decimal(str(check_out_lat))
        booking.check_out_lng = Decimal(str(check_out_lng))
    
    if check_out_datetime:
        try:
            if isinstance(check_out_datetime, str):
                booking.check_out_datetime = datetime.fromisoformat(check_out_datetime.replace('Z', '+00:00'))
            else:
                booking.check_out_datetime = datetime.fromisoformat(str(check_out_datetime).replace('Z', '+00:00'))
        except:
            return Response({'error': 'Invalid check_out_datetime format'}, status=status.HTTP_400_BAD_REQUEST)
    
    if check_out_address is not None:
        booking.check_out_address = check_out_address
    
    if trip_distance is not None:
        booking.trip_distance = Decimal(str(trip_distance))
    
    if trip_duration is not None:
        booking.trip_duration = int(trip_duration)
    
    if trip_amount is not None:
        booking.trip_amount = Decimal(str(trip_amount))
    
    booking.save()
    
    serializer = SeatBookingSerializer(booking)
    return Response(serializer.data)


@api_view(['GET'])
def seat_booking_delete_get_view(request, pk):
    """Delete a seat booking"""
    try:
        booking = SeatBooking.objects.get(pk=pk)
    except SeatBooking.DoesNotExist:
        return Response({'error': 'Seat booking not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # If booking is not checked out, make seat available again
    if not booking.check_out_datetime:
        vehicle_seat = booking.vehicle_seat
        vehicle_seat.status = 'available'
        vehicle_seat.save()
    
    booking.delete()
    return Response({'message': 'Seat booking deleted successfully'}, status=status.HTTP_200_OK)


@api_view(['POST'])
def seat_booking_create_view(request):
    """Create booking with user/guest logic and update seat status"""
    return _create_seat_booking(request)


@api_view(['POST'])
def seat_booking_switch_view(request):
    """Switch seat from one to another"""
    vehicle_seat_id = request.POST.get('vehicle_seat_id') or request.data.get('vehicle_seat_id')
    new_vehicle_seat_id = request.POST.get('new_vehicle_seat_id') or request.data.get('new_vehicle_seat_id')
    
    if not vehicle_seat_id or not new_vehicle_seat_id:
        return Response({'error': 'Both vehicle_seat_id and new_vehicle_seat_id are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Get the current seat
    try:
        current_seat = VehicleSeat.objects.get(pk=vehicle_seat_id)
    except VehicleSeat.DoesNotExist:
        return Response({'error': 'Current seat not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get the new seat
    try:
        new_seat = VehicleSeat.objects.get(pk=new_vehicle_seat_id, vehicle=current_seat.vehicle)
    except VehicleSeat.DoesNotExist:
        return Response({'error': 'New seat not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if new seat is available
    if new_seat.status != 'available':
        return Response({'error': 'New seat is not available'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Get the latest booking for the current seat that hasn't been checked out
    try:
        booking = SeatBooking.objects.filter(
            vehicle_seat=current_seat,
            check_out_datetime__isnull=True
        ).latest('created_at')
    except SeatBooking.DoesNotExist:
        return Response({'error': 'No active booking found for current seat'}, status=status.HTTP_404_NOT_FOUND)
    
    # Update booking to use new seat
    booking.vehicle_seat = new_seat
    booking.save()
    
    # Update seat statuses
    current_seat.status = 'available'
    current_seat.save()
    
    new_seat.status = 'booked'
    new_seat.save()
    
    serializer = SeatBookingSerializer(booking)
    return Response(serializer.data)


@api_view(['POST'])
def seat_booking_checkout_view(request):
    """Checkout with distance/duration/amount calculation"""
    vehicle_seat_id = request.POST.get('vehicle_seat_id') or request.data.get('vehicle_seat_id')
    check_out_lat = request.POST.get('check_out_lat') or request.data.get('check_out_lat')
    check_out_lng = request.POST.get('check_out_lng') or request.data.get('check_out_lng')
    check_out_address = request.POST.get('check_out_address') or request.data.get('check_out_address', '')
    is_paid = request.POST.get('is_paid') or request.data.get('is_paid', 'false')
    
    if not vehicle_seat_id:
        return Response({'error': 'Vehicle seat is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not check_out_lat or not check_out_lng:
        return Response({'error': 'Check-out location (lat/lng) is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Get the seat
    try:
        vehicle_seat = VehicleSeat.objects.get(pk=vehicle_seat_id)
    except VehicleSeat.DoesNotExist:
        return Response({'error': 'Vehicle seat not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get the latest booking for this seat that hasn't been checked out
    try:
        booking = SeatBooking.objects.select_related('trip', 'trip__driver').filter(
            vehicle_seat=vehicle_seat,
            check_out_datetime__isnull=True
        ).latest('created_at')
    except SeatBooking.DoesNotExist:
        return Response({'error': 'No active booking found for this seat'}, status=status.HTTP_404_NOT_FOUND)
    
    # Calculate distance
    distance = haversine_distance(
        booking.check_in_lat,
        booking.check_in_lng,
        Decimal(str(check_out_lat)),
        Decimal(str(check_out_lng))
    )
    
    # Calculate duration (in seconds)
    check_out_time = datetime.now()
    if booking.check_in_datetime.tzinfo:
        check_out_time = datetime.now(booking.check_in_datetime.tzinfo)
    duration = int((check_out_time - booking.check_in_datetime).total_seconds())
    
    # Trip amount: for scheduled trips use existing (pre-set from ticket); else calculate from distance
    is_scheduled_trip = booking.trip_id and getattr(booking.trip, 'is_scheduled', False)
    if is_scheduled_trip and booking.trip_amount is not None and booking.trip_amount > 0:
        trip_amount = booking.trip_amount
    else:
        try:
            super_setting = SuperSetting.objects.latest('created_at')
            per_km_charge = super_setting.per_km_charge
        except SuperSetting.DoesNotExist:
            return Response({'error': 'Super setting not found. Please configure per_km_charge.'}, status=status.HTTP_400_BAD_REQUEST)
        trip_amount = Decimal(str(distance)) * per_km_charge
        trip_amount = Decimal(str(round(trip_amount, 2)))
    
    # Update booking
    booking.check_out_lat = Decimal(str(check_out_lat))
    booking.check_out_lng = Decimal(str(check_out_lng))
    booking.check_out_datetime = check_out_time
    booking.check_out_address = check_out_address
    booking.trip_distance = distance
    booking.trip_duration = duration
    booking.trip_amount = trip_amount
    booking.is_paid = is_paid.lower() == 'true' if isinstance(is_paid, str) else bool(is_paid)
    booking.save()
    
    # Update seat status to available
    vehicle_seat.status = 'available'
    vehicle_seat.save()
    
    # Add trip amount to passenger wallet to_pay and create transaction (driver -> user -> wallet -> to_pay)
    if booking.user and booking.trip_amount and booking.trip_amount > 0:
        wallet, _ = Wallet.objects.get_or_create(user=booking.user, defaults={'balance': 0, 'to_pay': 0, 'to_receive': 0})
        balance_before = wallet.balance
        balance_after = wallet.balance
        Wallet.objects.filter(pk=wallet.pk).update(to_pay=F('to_pay') + booking.trip_amount)
        wallet.refresh_from_db()
        Transaction.objects.create(
            wallet=wallet,
            user=booking.user,
            amount=booking.trip_amount,
            balance_before=balance_before,
            balance_after=balance_after,
            type='add',
            status='success',
            remarks=f'Trip amount - Seat booking #{booking.id}',
        )
    
    # For normal (non-scheduled) trip: add trip_amount to driver's to_receive. Scheduled trips already paid via ticket.
    if booking.trip_id and booking.trip_amount and booking.trip_amount > 0 and booking.trip and not getattr(booking.trip, 'is_scheduled', False):
        driver = booking.trip.driver
        if driver:
            driver_wallet, _ = Wallet.objects.get_or_create(user=driver, defaults={'balance': 0, 'to_pay': 0, 'to_receive': 0})
            balance_before = driver_wallet.balance
            Wallet.objects.filter(pk=driver_wallet.pk).update(to_receive=F('to_receive') + booking.trip_amount)
            driver_wallet.refresh_from_db()
            Transaction.objects.create(
                wallet=driver_wallet,
                user=driver,
                amount=booking.trip_amount,
                balance_before=balance_before,
                balance_after=driver_wallet.balance,
                type='add',
                status='success',
                remarks=f'Trip amount (driver) - Seat booking #{booking.id}',
            )
    
    serializer = SeatBookingSerializer(booking)
    return Response(serializer.data)
