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
    bill_book = models.CharField(max_length=255, blank=True, null=True)
    bill_book_expiry_date = models.DateField(null=True, blank=True)
    insurance_expiry_date = models.DateField(null=True, blank=True)
    road_permit_expiry_date = models.DateField(null=True, blank=True)
    seat_layout = models.JSONField(default=list, blank=True)  # e.g. ["x","-","-","y",":", ...]
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


class VehicleSchedule(models.Model):
    """Scheduled trip for a vehicle on a route"""
    id = models.BigAutoField(primary_key=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='vehicle_schedules')
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='vehicle_schedules')
    date = models.DateField()
    time = models.TimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'vehicle_schedules'
        indexes = [
            models.Index(fields=['vehicle', 'date']),
            models.Index(fields=['route', 'date']),
        ]

    def __str__(self):
        return f"{self.vehicle.name} - {self.route.name} ({self.date} {self.time})"


class Trip(models.Model):
    """Trip model for a vehicle/driver/route"""
    id = models.BigAutoField(primary_key=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='trips')
    driver = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='trips', limit_choices_to={'is_driver': True})
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='trips')
    trip_id = models.CharField(max_length=100, unique=True, db_index=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    is_scheduled = models.BooleanField(default=False)
    vehicle_schedule = models.ForeignKey(VehicleSchedule, on_delete=models.SET_NULL, null=True, blank=True, related_name='trips')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'trips'
        indexes = [
            models.Index(fields=['vehicle', 'start_time']),
            models.Index(fields=['driver', 'start_time']),
            models.Index(fields=['route']),
            models.Index(fields=['end_time']),
        ]

    def __str__(self):
        return f"{self.trip_id} - {self.vehicle.name}"


class Location(models.Model):
    """Location record for vehicle/trip"""
    id = models.BigAutoField(primary_key=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='locations')
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, null=True, blank=True, related_name='locations')
    latitude = models.DecimalField(max_digits=20, decimal_places=16)
    longitude = models.DecimalField(max_digits=20, decimal_places=16)
    speed = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'locations'
        indexes = [
            models.Index(fields=['vehicle', 'created_at']),
            models.Index(fields=['trip', 'created_at']),
        ]

    def __str__(self):
        return f"{self.vehicle.name} @ ({self.latitude}, {self.longitude})"


class VehicleTicketBooking(models.Model):
    """Ticket booking for a scheduled vehicle trip"""
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='vehicle_ticket_bookings')
    is_guest = models.BooleanField(default=False)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=100)
    vehicle_schedule = models.ForeignKey(VehicleSchedule, on_delete=models.CASCADE, related_name='ticket_bookings')
    ticket_id = models.CharField(max_length=100, unique=True, db_index=True)
    seat = models.JSONField(default=dict)  # list e.g. [{"side": "A", "number": 1}, ...] or legacy single dict
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    pnr = models.CharField(max_length=100, db_index=True)  # EYS{ticket_id}
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'vehicle_ticket_bookings'
        indexes = [
            models.Index(fields=['vehicle_schedule']),
            models.Index(fields=['user']),
            models.Index(fields=['pnr']),
        ]

    def __str__(self):
        return f"{self.pnr} - {self.name}"


class SeatBooking(models.Model):
    """Seat booking model"""
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='seat_bookings')
    is_guest = models.BooleanField(default=False)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='seat_bookings')
    vehicle_seat = models.ForeignKey(VehicleSeat, on_delete=models.CASCADE, related_name='bookings')
    trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, null=True, blank=True, related_name='seat_bookings')
    check_in_lat = models.DecimalField(max_digits=20, decimal_places=16)
    check_in_lng = models.DecimalField(max_digits=20, decimal_places=16)
    check_in_datetime = models.DateTimeField()
    check_in_address = models.TextField()
    check_out_lat = models.DecimalField(max_digits=20, decimal_places=16, null=True, blank=True)
    check_out_lng = models.DecimalField(max_digits=20, decimal_places=16, null=True, blank=True)
    check_out_datetime = models.DateTimeField(null=True, blank=True)
    check_out_address = models.TextField(blank=True, null=True)
    trip_distance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # in kilometers
    trip_duration = models.IntegerField(null=True, blank=True)  # in seconds
    trip_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')
    
    class Meta:
        db_table = 'seat_bookings'
        indexes = [
            models.Index(fields=['vehicle', 'vehicle_seat']),
            models.Index(fields=['user']),
            models.Index(fields=['is_guest']),
            models.Index(fields=['is_paid']),
            models.Index(fields=['check_in_datetime']),
            models.Index(fields=['vehicle_seat', 'check_out_datetime']),  # For finding active bookings
        ]
    
    def __str__(self):
        user_info = f"{self.user.name if self.user else 'Guest'}"
        return f"{self.vehicle.name} - {self.vehicle_seat.side}{self.vehicle_seat.number} - {user_info}"
