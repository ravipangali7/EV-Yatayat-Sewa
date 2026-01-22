from django.db import models


class Place(models.Model):
    """Place/Location model"""
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    latitude = models.DecimalField(max_digits=20, decimal_places=16)
    longitude = models.DecimalField(max_digits=20, decimal_places=16)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')
    
    class Meta:
        db_table = 'places'
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['latitude', 'longitude']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class Route(models.Model):
    """Route model connecting two places"""
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    is_bidirectional = models.BooleanField(default=False)
    start_point = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='routes_starting_here')
    end_point = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='routes_ending_here')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')
    
    class Meta:
        db_table = 'routes'
        indexes = [
            models.Index(fields=['start_point', 'end_point']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.start_point.name} -> {self.end_point.name})"


class RouteStopPoint(models.Model):
    """Stop points along a route"""
    id = models.BigAutoField(primary_key=True)
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stop_points')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='route_stops')
    order = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')
    
    class Meta:
        db_table = 'route_stop_points'
        unique_together = [['route', 'place']]
        indexes = [
            models.Index(fields=['route', 'place']),
            models.Index(fields=['route', 'order']),
        ]
    
    def __str__(self):
        return f"{self.route.name} - {self.place.name} (Order: {self.order})"


class Vehicle(models.Model):
    """Vehicle model"""
    id = models.BigAutoField(primary_key=True)
    imei = models.CharField(max_length=50, null=True, blank=True)
    name = models.CharField(max_length=255)
    vehicle_no = models.CharField(max_length=50, unique=True)
    vehicle_type = models.CharField(max_length=100)
    odometer = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    overspeed_limit = models.IntegerField(default=80)  # in km/h
    description = models.TextField(blank=True, null=True)
    featured_image = models.ImageField(upload_to='uploads/vehicles/', blank=True, null=True)
    drivers = models.ManyToManyField('core.User', related_name='vehicles', blank=True, limit_choices_to={'is_driver': True})
    active_driver = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='active_vehicles', limit_choices_to={'is_driver': True})
    routes = models.ManyToManyField(Route, related_name='vehicles', blank=True)
    active_route = models.ForeignKey(Route, on_delete=models.SET_NULL, null=True, blank=True, related_name='active_vehicles_route')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')
    
    class Meta:
        db_table = 'vehicles'
        indexes = [
            models.Index(fields=['vehicle_no']),
            models.Index(fields=['imei']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.vehicle_no})"


class VehicleSeat(models.Model):
    """Seat model for vehicles"""
    SIDE_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
    ]
    
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('booked', 'Booked'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='seats')
    side = models.CharField(max_length=1, choices=SIDE_CHOICES)
    number = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')
    
    class Meta:
        db_table = 'vehicle_seats'
        unique_together = [['vehicle', 'side', 'number']]
        indexes = [
            models.Index(fields=['vehicle', 'status']),
        ]
    
    def __str__(self):
        return f"{self.vehicle.name} - {self.side}{self.number} ({self.status})"


class VehicleImage(models.Model):
    """Image model for vehicles"""
    id = models.BigAutoField(primary_key=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='images')
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='uploads/vehicles/images/')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')
    
    class Meta:
        db_table = 'vehicle_images'
        indexes = [
            models.Index(fields=['vehicle']),
        ]
    
    def __str__(self):
        return f"{self.vehicle.name} - {self.title or 'Image'}"
