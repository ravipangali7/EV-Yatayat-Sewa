from rest_framework import serializers
from .models import Place, Route, RouteStopPoint, Vehicle, VehicleSeat, VehicleImage, Trip, SeatBooking


class PlaceSerializer(serializers.ModelSerializer):
    """Serializer for Place model"""
    class Meta:
        model = Place
        fields = [
            'id', 'name', 'code', 'latitude', 'longitude', 
            'address', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PlaceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for place lists"""
    class Meta:
        model = Place
        fields = ['id', 'name', 'code', 'latitude', 'longitude']


class RouteStopPointSerializer(serializers.ModelSerializer):
    """Serializer for RouteStopPoint model"""
    place_details = PlaceListSerializer(source='place', read_only=True)
    
    class Meta:
        model = RouteStopPoint
        fields = [
            'id', 'route', 'place', 'place_details', 'order',
            'announcement_text',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RouteSerializer(serializers.ModelSerializer):
    """Serializer for Route model"""
    start_point_details = PlaceListSerializer(source='start_point', read_only=True)
    end_point_details = PlaceListSerializer(source='end_point', read_only=True)
    stop_points = RouteStopPointSerializer(many=True, read_only=True)
    
    class Meta:
        model = Route
        fields = [
            'id', 'name', 'is_bidirectional', 'start_point', 'start_point_details',
            'end_point', 'end_point_details', 'stop_points', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'stop_points']


class RouteListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for route lists"""
    start_point_details = PlaceListSerializer(source='start_point', read_only=True)
    end_point_details = PlaceListSerializer(source='end_point', read_only=True)
    
    class Meta:
        model = Route
        fields = ['id', 'name', 'is_bidirectional', 'start_point_details', 'end_point_details']


class VehicleSeatSerializer(serializers.ModelSerializer):
    """Serializer for VehicleSeat model"""
    class Meta:
        model = VehicleSeat
        fields = [
            'id', 'vehicle', 'side', 'number', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VehicleImageSerializer(serializers.ModelSerializer):
    """Serializer for VehicleImage model"""
    class Meta:
        model = VehicleImage
        fields = [
            'id', 'vehicle', 'title', 'description', 'image',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VehicleSerializer(serializers.ModelSerializer):
    """Serializer for Vehicle model"""
    from core.serializers import UserListSerializer
    
    driver_details = UserListSerializer(source='drivers', many=True, read_only=True)
    active_driver_details = UserListSerializer(source='active_driver', read_only=True)
    route_details = RouteListSerializer(source='routes', many=True, read_only=True)
    active_route_details = RouteListSerializer(source='active_route', read_only=True)
    seats = VehicleSeatSerializer(many=True, read_only=True)
    images = VehicleImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Vehicle
        fields = [
            'id', 'imei', 'name', 'vehicle_no', 'vehicle_type', 'odometer',
            'overspeed_limit', 'description', 'featured_image', 'drivers',
            'driver_details', 'active_driver', 'active_driver_details',
            'routes', 'route_details', 'active_route', 'active_route_details',
            'is_active', 'seats', 'images', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'seats', 'images']


class TripListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for trip in SeatBooking"""
    class Meta:
        model = Trip
        fields = ['id', 'trip_id', 'start_time', 'end_time', 'route']


class SeatBookingSerializer(serializers.ModelSerializer):
    """Serializer for SeatBooking model"""
    from core.serializers import UserListSerializer
    
    user_details = UserListSerializer(source='user', read_only=True)
    vehicle_details = serializers.SerializerMethodField()
    vehicle_seat_details = VehicleSeatSerializer(source='vehicle_seat', read_only=True)
    trip_details = TripListSerializer(source='trip', read_only=True)
    destination_place_details = PlaceListSerializer(source='destination_place', read_only=True)
    
    class Meta:
        model = SeatBooking
        fields = [
            'id', 'user', 'user_details', 'is_guest', 'vehicle', 'vehicle_details',
            'vehicle_seat', 'vehicle_seat_details', 'trip', 'trip_details',
            'check_in_lat', 'check_in_lng', 'check_in_datetime', 'check_in_address',
            'check_out_lat', 'check_out_lng', 'check_out_datetime', 'check_out_address',
            'trip_distance', 'trip_duration', 'trip_amount', 'is_paid',
            'destination_place', 'destination_place_details',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_vehicle_details(self, obj):
        """Get lightweight vehicle details"""
        return {
            'id': str(obj.vehicle.id),
            'name': obj.vehicle.name,
            'vehicle_no': obj.vehicle.vehicle_no,
            'vehicle_type': obj.vehicle.vehicle_type,
        }
