from django.contrib import admin
from .models import Place, Route, RouteStopPoint, Vehicle, VehicleSeat, VehicleImage, VehicleSchedule, Trip, Location, VehicleTicketBooking, SeatBooking


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    """Place admin"""
    list_display = ('id', 'name', 'code', 'latitude', 'longitude', 'address', 'created_at', 'updated_at')
    list_filter = ('code', 'created_at', 'updated_at')
    search_fields = ('name', 'code', 'address')
    list_editable = ('name', 'code', 'latitude', 'longitude')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


class RouteStopPointInline(admin.StackedInline):
    """Inline for RouteStopPoint in Route admin"""
    model = RouteStopPoint
    extra = 1
    fields = ('place', 'order')
    raw_id_fields = ('place',)


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    """Route admin"""
    list_display = ('id', 'name', 'is_bidirectional', 'start_point', 'end_point', 'created_at', 'updated_at')
    list_filter = ('is_bidirectional', 'created_at', 'updated_at')
    search_fields = ('name', 'start_point__name', 'end_point__name')
    list_editable = ('name', 'is_bidirectional')
    raw_id_fields = ('start_point', 'end_point')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [RouteStopPointInline]
    date_hierarchy = 'created_at'


@admin.register(RouteStopPoint)
class RouteStopPointAdmin(admin.ModelAdmin):
    """RouteStopPoint admin"""
    list_display = ('id', 'route', 'place', 'order', 'created_at', 'updated_at')
    list_filter = ('route', 'created_at', 'updated_at')
    search_fields = ('route__name', 'place__name')
    list_editable = ('order',)
    raw_id_fields = ('route', 'place')
    readonly_fields = ('created_at', 'updated_at')


class VehicleSeatInline(admin.StackedInline):
    """Inline for VehicleSeat in Vehicle admin"""
    model = VehicleSeat
    extra = 1
    fields = ('side', 'number', 'status')


class VehicleImageInline(admin.StackedInline):
    """Inline for VehicleImage in Vehicle admin"""
    model = VehicleImage
    extra = 1
    fields = ('title', 'description', 'image')


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    """Vehicle admin"""
    list_display = ('id', 'name', 'vehicle_no', 'vehicle_type', 'imei', 'odometer', 'overspeed_limit', 'bill_book_expiry_date', 'insurance_expiry_date', 'road_permit_expiry_date', 'is_active', 'active_driver', 'active_route', 'created_at', 'updated_at')
    list_filter = ('vehicle_type', 'is_active', 'created_at', 'updated_at')
    search_fields = ('name', 'vehicle_no', 'imei')
    list_editable = ('name', 'vehicle_type', 'odometer', 'overspeed_limit', 'is_active')
    raw_id_fields = ('active_driver', 'active_route')
    filter_horizontal = ('drivers', 'routes')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [VehicleSeatInline, VehicleImageInline]
    date_hierarchy = 'created_at'


@admin.register(VehicleSeat)
class VehicleSeatAdmin(admin.ModelAdmin):
    """VehicleSeat admin"""
    list_display = ('id', 'vehicle', 'side', 'number', 'status', 'created_at', 'updated_at')
    list_filter = ('side', 'status', 'vehicle', 'created_at', 'updated_at')
    search_fields = ('vehicle__name', 'vehicle__vehicle_no')
    list_editable = ('status',)
    raw_id_fields = ('vehicle',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(VehicleImage)
class VehicleImageAdmin(admin.ModelAdmin):
    """VehicleImage admin"""
    list_display = ('id', 'vehicle', 'title', 'image', 'created_at', 'updated_at')
    list_filter = ('vehicle', 'created_at', 'updated_at')
    search_fields = ('vehicle__name', 'vehicle__vehicle_no', 'title')
    raw_id_fields = ('vehicle',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(VehicleSchedule)
class VehicleScheduleAdmin(admin.ModelAdmin):
    """VehicleSchedule admin"""
    list_display = ('id', 'vehicle', 'route', 'date', 'time', 'price', 'created_at', 'updated_at')
    list_filter = ('date', 'vehicle', 'route', 'created_at', 'updated_at')
    search_fields = ('vehicle__name', 'vehicle__vehicle_no', 'route__name')
    raw_id_fields = ('vehicle', 'route')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'date'


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    """Trip admin"""
    list_display = ('id', 'trip_id', 'vehicle', 'driver', 'route', 'start_time', 'end_time', 'is_scheduled', 'created_at', 'updated_at')
    list_filter = ('is_scheduled', 'vehicle', 'created_at', 'updated_at')
    search_fields = ('trip_id', 'vehicle__name', 'vehicle__vehicle_no', 'driver__name', 'driver__phone', 'route__name')
    raw_id_fields = ('vehicle', 'driver', 'route', 'vehicle_schedule')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    """Location admin"""
    list_display = ('id', 'vehicle', 'trip', 'latitude', 'longitude', 'speed', 'created_at', 'updated_at')
    list_filter = ('vehicle', 'created_at', 'updated_at')
    search_fields = ('vehicle__name', 'vehicle__vehicle_no')
    raw_id_fields = ('vehicle', 'trip')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(VehicleTicketBooking)
class VehicleTicketBookingAdmin(admin.ModelAdmin):
    """VehicleTicketBooking admin"""
    list_display = ('id', 'pnr', 'ticket_id', 'vehicle_schedule', 'user', 'name', 'phone', 'price', 'is_paid', 'created_at', 'updated_at')
    list_filter = ('is_guest', 'is_paid', 'created_at', 'updated_at')
    search_fields = ('pnr', 'ticket_id', 'name', 'phone', 'vehicle_schedule__vehicle__name')
    raw_id_fields = ('user', 'vehicle_schedule')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(SeatBooking)
class SeatBookingAdmin(admin.ModelAdmin):
    """SeatBooking admin"""
    list_display = ('id', 'vehicle', 'vehicle_seat', 'trip', 'user', 'is_guest', 'check_in_datetime', 'check_out_datetime', 'trip_amount', 'is_paid', 'created_at', 'updated_at')
    list_filter = ('is_guest', 'is_paid', 'vehicle', 'created_at', 'updated_at', 'check_in_datetime')
    search_fields = ('vehicle__name', 'vehicle__vehicle_no', 'user__name', 'user__phone', 'vehicle_seat__side', 'vehicle_seat__number')
    list_editable = ('is_paid',)
    raw_id_fields = ('user', 'vehicle', 'vehicle_seat', 'trip')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'check_in_datetime'
