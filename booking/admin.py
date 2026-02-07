from django.contrib import admin
from .models import Place, Route, RouteStopPoint, Vehicle, VehicleSeat, VehicleImage, SeatBooking


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
    list_display = ('id', 'name', 'vehicle_no', 'vehicle_type', 'imei', 'odometer', 'overspeed_limit', 'is_active', 'active_driver', 'active_route', 'created_at', 'updated_at')
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


@admin.register(SeatBooking)
class SeatBookingAdmin(admin.ModelAdmin):
    """SeatBooking admin"""
    list_display = ('id', 'vehicle', 'vehicle_seat', 'user', 'is_guest', 'check_in_datetime', 'check_out_datetime', 'trip_amount', 'is_paid', 'created_at', 'updated_at')
    list_filter = ('is_guest', 'is_paid', 'vehicle', 'created_at', 'updated_at', 'check_in_datetime')
    search_fields = ('vehicle__name', 'vehicle__vehicle_no', 'user__name', 'user__phone', 'vehicle_seat__side', 'vehicle_seat__number')
    list_editable = ('is_paid',)
    raw_id_fields = ('user', 'vehicle', 'vehicle_seat')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'check_in_datetime'
