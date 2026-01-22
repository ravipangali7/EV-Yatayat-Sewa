from rest_framework import serializers
from .models import Place, Route, RouteStopPoint, Vehicle, VehicleSeat, VehicleImage


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
