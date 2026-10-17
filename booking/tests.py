from django.test import SimpleTestCase

from booking.views.trip_views import select_reached_stop_index


class _Place:
    def __init__(self, lat, lng):
        self.latitude = lat
        self.longitude = lng


class ReachedStopTests(SimpleTestCase):
    def test_picks_stop_on_the_far_side_of_the_road(self):
        # About 40m apart. The vehicle is beside the second pin, still inside
        # the first pin's circle. The second stop is the one to announce.
        first = _Place(27.7000, 85.3000)
        second = _Place(27.7003617, 85.3000)
        vehicle_lat, vehicle_lng = 27.7003617, 85.300152
        points = [
            ('stop', first, None),
            ('stop', second, None),
        ]
        index, crossed = select_reached_stop_index(points, vehicle_lat, vehicle_lng, 0.5)
        self.assertEqual(index, 1)
        self.assertTrue(crossed)

    def test_stays_on_the_stop_not_yet_crossed(self):
        first = _Place(27.7000, 85.3000)
        second = _Place(27.7003617, 85.3000)
        points = [
            ('stop', first, None),
            ('stop', second, None),
        ]
        index, crossed = select_reached_stop_index(points, 27.7000, 85.3000, 0.5)
        self.assertEqual(index, 0)
        self.assertTrue(crossed)

    def test_ignores_a_stop_far_ahead(self):
        here = _Place(27.7000, 85.3000)
        ahead = _Place(27.7180, 85.3000)
        points = [
            ('stop', here, None),
            ('stop', ahead, None),
        ]
        index, crossed = select_reached_stop_index(points, 27.7000, 85.3000, 0.5)
        self.assertEqual(index, 0)
        self.assertTrue(crossed)


from datetime import datetime, timezone
from decimal import Decimal
import json
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import User, Wallet, Transaction, SuperSetting
from booking.models import Place, Route, RouteStopPoint, Vehicle, VehicleSeat, Trip, SeatBooking


class BookingLifecycleAndCheckoutIntegrityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.super_setting = SuperSetting.objects.create(
            per_km_charge=Decimal('10.00'),
            initial_km=Decimal('2.00'),
            initial_km_charge=Decimal('25.00'),
            point_cover_radius=Decimal('0.5'),
        )
        self.driver = User.objects.create_user(
            phone='9811111111',
            username='9811111111',
            name='Test Driver',
            password='password123',
            is_driver=True,
        )
        self.passenger = User.objects.create_user(
            phone='9822222222',
            username='9822222222',
            name='Test Passenger',
            password='password123',
        )
        self.driver_wallet = Wallet.objects.create(
            user=self.driver,
            balance=Decimal('500.00'),
            to_pay=Decimal('0.00'),
            to_receive=Decimal('0.00'),
        )
        self.passenger_wallet = Wallet.objects.create(
            user=self.passenger,
            balance=Decimal('500.00'),
            to_pay=Decimal('0.00'),
            to_receive=Decimal('0.00'),
        )
        self.place_start = Place.objects.create(
            name='Ratnapark',
            code='RTP',
            latitude=Decimal('27.70600000'),
            longitude=Decimal('85.31500000'),
        )
        self.place_mid = Place.objects.create(
            name='Koteshwor',
            code='KTS',
            latitude=Decimal('27.67800000'),
            longitude=Decimal('85.34900000'),
        )
        self.place_end = Place.objects.create(
            name='Suryabinayak',
            code='SRB',
            latitude=Decimal('27.66900000'),
            longitude=Decimal('85.43200000'),
        )
        self.route = Route.objects.create(
            name='Ratnapark - Suryabinayak',
            is_bidirectional=True,
            start_point=self.place_start,
            end_point=self.place_end,
        )
        RouteStopPoint.objects.create(route=self.route, place=self.place_mid, order=1)

        self.vehicle = Vehicle.objects.create(
            imei='123456789012345',
            name='EV Micro 1',
            vehicle_no='BA 1 PA 1001',
            vehicle_type='Micro',
            active_driver=self.driver,
            active_route=self.route,
            is_active=True,
        )
        self.vehicle.drivers.add(self.driver)
        self.vehicle.routes.add(self.route)
        self.seat_a1 = VehicleSeat.objects.create(vehicle=self.vehicle, side='A', number=1, status='available')
        self.seat_a2 = VehicleSeat.objects.create(vehicle=self.vehicle, side='A', number=2, status='available')

        self.trip = Trip.objects.create(
            trip_id='TRIP-TEST-001',
            vehicle=self.vehicle,
            driver=self.driver,
            route=self.route,
            start_time=datetime.now(timezone.utc),
            is_scheduled=False,
        )

    def test_a2_toggling_vehicle_seat_available_booked_preserves_seat_booking_history(self):
        """A2: Updating vehicle seats between available and booked must not cascade-delete SeatBooking records."""
        booking = SeatBooking.objects.create(
            user=self.passenger,
            is_guest=False,
            vehicle=self.vehicle,
            vehicle_seat=self.seat_a1,
            trip=self.trip,
            check_in_lat=self.place_start.latitude,
            check_in_lng=self.place_start.longitude,
            check_in_datetime=datetime.now(timezone.utc),
            check_in_address='Ratnapark',
            destination_place=self.place_end,
            trip_amount=Decimal('60.00'),
            is_paid=True,
        )
        self.client.force_authenticate(user=self.driver)

        # Toggle A1 to booked and A2 to available via vehicle edit endpoint
        seats_payload = json.dumps([
            {'side': 'A', 'number': 1, 'status': 'booked'},
            {'side': 'A', 'number': 2, 'status': 'available'},
        ])
        res = self.client.post(f'/api/vehicles/{self.vehicle.id}/edit/', data={'seats': seats_payload})
        self.assertEqual(res.status_code, 200)

        # Toggle A1 back to available
        seats_payload_avail = json.dumps([
            {'side': 'A', 'number': 1, 'status': 'available'},
            {'side': 'A', 'number': 2, 'status': 'booked'},
        ])
        res = self.client.post(f'/api/vehicles/{self.vehicle.id}/edit/', data={'seats': seats_payload_avail})
        self.assertEqual(res.status_code, 200)

        # SeatBooking record and seat PK must remain intact
        self.assertTrue(SeatBooking.objects.filter(pk=booking.pk).exists())
        self.seat_a1.refresh_from_db()
        self.assertEqual(self.seat_a1.status, 'available')

    def test_b3_early_checkout_before_destination_does_not_deduct_or_charge_driver(self):
        """B3: Checking out a passenger before reaching destination must not charge driver_wallet.to_pay or balance."""
        self.seat_a1.status = 'booked'
        self.seat_a1.save()
        booking = SeatBooking.objects.create(
            user=None,
            is_guest=True,
            vehicle=self.vehicle,
            vehicle_seat=self.seat_a1,
            trip=self.trip,
            check_in_lat=self.place_start.latitude,
            check_in_lng=self.place_start.longitude,
            check_in_datetime=datetime.now(timezone.utc),
            check_in_address='Ratnapark',
            destination_place=self.place_end,
            trip_amount=Decimal('80.00'),
            is_paid=True,
        )
        self.client.force_authenticate(user=self.driver)

        # 1. Attempt checkout at mid-route (Koteshwor, > 500m from Suryabinayak destination) without confirm_out_of_range
        preview_res = self.client.post(
            '/api/seat-bookings/checkout/',
            data={
                'vehicle_seat_id': str(self.seat_a1.id),
                'check_out_lat': str(self.place_mid.latitude),
                'check_out_lng': str(self.place_mid.longitude),
                'is_paid': 'false',
            },
            format='json',
        )
        self.assertEqual(preview_res.status_code, 200)
        self.assertFalse(preview_res.data.get('within_destination', True))

        # 2. Confirm early checkout before reaching destination
        confirm_res = self.client.post(
            '/api/seat-bookings/checkout/',
            data={
                'vehicle_seat_id': str(self.seat_a1.id),
                'check_out_lat': str(self.place_mid.latitude),
                'check_out_lng': str(self.place_mid.longitude),
                'is_paid': 'false',
                'confirm_out_of_range': 'true',
            },
            format='json',
        )
        self.assertEqual(confirm_res.status_code, 200)

        self.driver_wallet.refresh_from_db()
        self.seat_a1.refresh_from_db()
        booking.refresh_from_db()

        self.assertEqual(self.seat_a1.status, 'available')
        self.assertIsNotNone(booking.check_out_datetime)
        # Driver balance and to_pay must be completely untouched on early checkout before destination
        self.assertEqual(self.driver_wallet.balance, Decimal('500.00'))
        self.assertEqual(self.driver_wallet.to_pay, Decimal('0.00'))
        self.assertEqual(Transaction.objects.filter(wallet=self.driver_wallet).count(), 0)

    def test_b3_completed_guest_checkout_at_destination_settles_once_idempotently(self):
        """B3: Legitimate guest checkout at destination settles driver to_pay once and retries do not duplicate."""
        self.seat_a1.status = 'booked'
        self.seat_a1.save()
        booking = SeatBooking.objects.create(
            user=None,
            is_guest=True,
            vehicle=self.vehicle,
            vehicle_seat=self.seat_a1,
            trip=self.trip,
            check_in_lat=self.place_start.latitude,
            check_in_lng=self.place_start.longitude,
            check_in_datetime=datetime.now(timezone.utc),
            check_in_address='Ratnapark',
            destination_place=self.place_end,
            trip_amount=Decimal('80.00'),
            is_paid=True,
        )
        self.client.force_authenticate(user=self.driver)

        res1 = self.client.post(
            '/api/seat-bookings/checkout/',
            data={
                'vehicle_seat_id': str(self.seat_a1.id),
                'check_out_lat': str(self.place_end.latitude),
                'check_out_lng': str(self.place_end.longitude),
                'place_id': str(self.place_end.id),
                'is_paid': 'true',
            },
            format='json',
        )
        self.assertEqual(res1.status_code, 200)
        self.driver_wallet.refresh_from_db()
        self.assertEqual(self.driver_wallet.to_pay, Decimal('80.00'))
        self.assertEqual(Transaction.objects.filter(wallet=self.driver_wallet).count(), 1)

        # Retry checkout on already-released seat -> must not double charge driver
        res2 = self.client.post(
            '/api/seat-bookings/checkout/',
            data={
                'vehicle_seat_id': str(self.seat_a1.id),
                'check_out_lat': str(self.place_end.latitude),
                'check_out_lng': str(self.place_end.longitude),
                'place_id': str(self.place_end.id),
                'is_paid': 'true',
            },
            format='json',
        )
        self.driver_wallet.refresh_from_db()
        self.assertEqual(self.driver_wallet.to_pay, Decimal('80.00'))
        self.assertEqual(Transaction.objects.filter(wallet=self.driver_wallet).count(), 1)

    def test_b3_wallet_paid_passenger_booking_never_charges_driver_and_refunds_on_early_checkout(self):
        """B3: Non-guest booking paid via passenger wallet never charges driver to_pay, and early checkout refunds unused fare."""
        self.seat_a2.status = 'booked'
        self.seat_a2.save()
        # Simulate passenger wallet payment of Rs. 120.00 at booking time
        self.passenger_wallet.balance = Decimal('380.00')
        self.passenger_wallet.save()
        booking = SeatBooking.objects.create(
            user=self.passenger,
            is_guest=False,
            vehicle=self.vehicle,
            vehicle_seat=self.seat_a2,
            trip=self.trip,
            check_in_lat=self.place_start.latitude,
            check_in_lng=self.place_start.longitude,
            check_in_datetime=datetime.now(timezone.utc),
            check_in_address='Ratnapark',
            destination_place=self.place_end,
            trip_amount=Decimal('120.00'),
            is_paid=True,
        )
        self.client.force_authenticate(user=self.driver)

        # Early checkout at check-in location (0 km traveled -> 0 actual fare -> full refund of 120.00 to passenger, 0 due on driver)
        res = self.client.post(
            '/api/seat-bookings/checkout/',
            data={
                'vehicle_seat_id': str(self.seat_a2.id),
                'check_out_lat': str(self.place_start.latitude),
                'check_out_lng': str(self.place_start.longitude),
                'is_paid': 'true',
                'confirm_out_of_range': 'true',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.driver_wallet.refresh_from_db()
        self.passenger_wallet.refresh_from_db()
        self.assertEqual(self.driver_wallet.to_pay, Decimal('0.00'))
        self.assertEqual(self.passenger_wallet.balance, Decimal('500.00'))

    def test_c1_trip_detail_includes_complete_ordered_route_for_active_trip(self):
        """C1: GET /api/trips/<id>/ returns start/end coordinates and ordered_points so route remains visible."""
        self.client.force_authenticate(user=self.passenger)
        res = self.client.get(f'/api/trips/{self.trip.id}/')
        self.assertEqual(res.status_code, 200)
        route_data = res.data.get('route')
        self.assertIsNotNone(route_data)
        self.assertEqual(route_data['name'], 'Ratnapark - Suryabinayak')
        self.assertEqual(route_data['start_point_name'], 'Ratnapark')
        self.assertEqual(route_data['end_point_name'], 'Suryabinayak')
        self.assertIsNotNone(route_data['start_point_lat'])
        self.assertIsNotNone(route_data['end_point_lat'])
        ordered = route_data.get('ordered_points', [])
        self.assertEqual(len(ordered), 3)
        self.assertEqual([p['name'] for p in ordered], ['Ratnapark', 'Koteshwor', 'Suryabinayak'])

