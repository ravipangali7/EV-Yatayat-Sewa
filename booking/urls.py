from django.urls import path
from .views import (
    place_views,
    route_views,
    vehicle_views,
    seat_booking_views,
    trip_views,
    location_views,
    vehicle_schedule_views,
    vehicle_ticket_booking_views,
)

urlpatterns = [
    # Place endpoints
    path('places/', place_views.place_list_get_view, name='place-list-get'),
    path('places/create/', place_views.place_list_post_view, name='place-list-post'),
    path('places/<int:pk>/', place_views.place_detail_get_view, name='place-detail-get'),
    path('places/<int:pk>/edit/', place_views.place_detail_post_view, name='place-detail-post'),
    path('places/<int:pk>/delete/', place_views.place_delete_get_view, name='place-delete'),
    
    # Route endpoints
    path('routes/', route_views.route_list_get_view, name='route-list-get'),
    path('routes/create/', route_views.route_list_post_view, name='route-list-post'),
    path('routes/<int:pk>/', route_views.route_detail_get_view, name='route-detail-get'),
    path('routes/<int:pk>/edit/', route_views.route_detail_post_view, name='route-detail-post'),
    path('routes/<int:pk>/delete/', route_views.route_delete_get_view, name='route-delete'),
    
    # Route Stop Point endpoints
    path('routes/<int:route_id>/stop-points/', route_views.route_stop_point_list_get_view, name='route-stop-point-list-get'),
    path('routes/<int:route_id>/stop-points/create/', route_views.route_stop_point_list_post_view, name='route-stop-point-list-post'),
    path('routes/<int:route_id>/stop-points/<int:pk>/', route_views.route_stop_point_detail_get_view, name='route-stop-point-detail-get'),
    path('routes/<int:route_id>/stop-points/<int:pk>/edit/', route_views.route_stop_point_detail_post_view, name='route-stop-point-detail-post'),
    path('routes/<int:route_id>/stop-points/<int:pk>/delete/', route_views.route_stop_point_delete_get_view, name='route-stop-point-delete'),
    
    # Vehicle endpoints
    path('vehicles/', vehicle_views.vehicle_list_get_view, name='vehicle-list-get'),
    path('vehicles/create/', vehicle_views.vehicle_list_post_view, name='vehicle-list-post'),
    path('vehicles/connect/', vehicle_views.vehicle_connect_view, name='vehicle-connect'),
    path('vehicles/my-active-vehicle/', vehicle_views.vehicle_my_active_get_view, name='vehicle-my-active'),
    path('vehicles/<int:pk>/', vehicle_views.vehicle_detail_get_view, name='vehicle-detail-get'),
    path('vehicles/<int:pk>/edit/', vehicle_views.vehicle_detail_post_view, name='vehicle-detail-post'),
    path('vehicles/<int:pk>/delete/', vehicle_views.vehicle_delete_get_view, name='vehicle-delete'),
    
    # Vehicle Seat endpoints
    path('vehicles/<int:vehicle_id>/seats/', vehicle_views.vehicle_seat_list_get_view, name='vehicle-seat-list-get'),
    path('vehicles/<int:vehicle_id>/seats/create/', vehicle_views.vehicle_seat_list_post_view, name='vehicle-seat-list-post'),
    path('vehicles/<int:vehicle_id>/seats/<int:pk>/', vehicle_views.vehicle_seat_detail_get_view, name='vehicle-seat-detail-get'),
    path('vehicles/<int:vehicle_id>/seats/<int:pk>/edit/', vehicle_views.vehicle_seat_detail_post_view, name='vehicle-seat-detail-post'),
    path('vehicles/<int:vehicle_id>/seats/<int:pk>/delete/', vehicle_views.vehicle_seat_delete_get_view, name='vehicle-seat-delete'),
    
    # Vehicle Image endpoints
    path('vehicles/<int:vehicle_id>/images/', vehicle_views.vehicle_image_list_get_view, name='vehicle-image-list-get'),
    path('vehicles/<int:vehicle_id>/images/create/', vehicle_views.vehicle_image_list_post_view, name='vehicle-image-list-post'),
    path('vehicles/<int:vehicle_id>/images/<int:pk>/', vehicle_views.vehicle_image_detail_get_view, name='vehicle-image-detail-get'),
    path('vehicles/<int:vehicle_id>/images/<int:pk>/edit/', vehicle_views.vehicle_image_detail_post_view, name='vehicle-image-detail-post'),
    path('vehicles/<int:vehicle_id>/images/<int:pk>/delete/', vehicle_views.vehicle_image_delete_get_view, name='vehicle-image-delete'),
    
    # Seat Booking endpoints
    path('seat-bookings/', seat_booking_views.seat_booking_list_get_view, name='seat-booking-list-get'),
    path('seat-bookings/create/', seat_booking_views.seat_booking_list_post_view, name='seat-booking-list-post'),
    path('seat-bookings/<int:pk>/', seat_booking_views.seat_booking_detail_get_view, name='seat-booking-detail-get'),
    path('seat-bookings/<int:pk>/edit/', seat_booking_views.seat_booking_detail_post_view, name='seat-booking-detail-post'),
    path('seat-bookings/<int:pk>/delete/', seat_booking_views.seat_booking_delete_get_view, name='seat-booking-delete'),
    
    # Seat Booking special endpoints
    path('seat-bookings/book/', seat_booking_views.seat_booking_create_view, name='seat-booking-create'),
    path('seat-bookings/switch/', seat_booking_views.seat_booking_switch_view, name='seat-booking-switch'),
    path('seat-bookings/checkout/', seat_booking_views.seat_booking_checkout_view, name='seat-booking-checkout'),
    # Trip endpoints
    path('trips/start/', trip_views.trip_start_view, name='trip-start'),
    path('trips/', trip_views.trip_list_get_view, name='trip-list-get'),
    path('trips/<int:pk>/', trip_views.trip_detail_get_view, name='trip-detail-get'),
    path('trips/<int:pk>/edit/', trip_views.trip_detail_post_view, name='trip-detail-post'),
    path('trips/<int:pk>/end/', trip_views.trip_end_view, name='trip-end'),
    path('trips/<int:pk>/delete/', trip_views.trip_delete_get_view, name='trip-delete'),
    # Location endpoints
    path('locations/', location_views.location_list_get_view, name='location-list-get'),
    path('locations/create/', location_views.location_list_post_view, name='location-list-post'),
    # Vehicle Schedule endpoints
    path('vehicle-schedules/', vehicle_schedule_views.vehicle_schedule_list_get_view, name='vehicle-schedule-list-get'),
    path('vehicle-schedules/start-places/', vehicle_schedule_views.vehicle_schedule_start_places_view, name='vehicle-schedule-start-places'),
    path('vehicle-schedules/end-places/', vehicle_schedule_views.vehicle_schedule_end_places_view, name='vehicle-schedule-end-places'),
    path('vehicle-schedules/create/', vehicle_schedule_views.vehicle_schedule_list_post_view, name='vehicle-schedule-list-post'),
    path('vehicle-schedules/<int:pk>/', vehicle_schedule_views.vehicle_schedule_detail_get_view, name='vehicle-schedule-detail-get'),
    path('vehicle-schedules/<int:pk>/edit/', vehicle_schedule_views.vehicle_schedule_detail_post_view, name='vehicle-schedule-detail-post'),
    path('vehicle-schedules/<int:pk>/delete/', vehicle_schedule_views.vehicle_schedule_delete_get_view, name='vehicle-schedule-delete'),
    # Vehicle Ticket Booking endpoints
    path('vehicle-ticket-bookings/', vehicle_ticket_booking_views.vehicle_ticket_booking_list_get_view, name='vehicle-ticket-booking-list-get'),
    path('vehicle-ticket-bookings/create/', vehicle_ticket_booking_views.vehicle_ticket_booking_list_post_view, name='vehicle-ticket-booking-list-post'),
    path('vehicle-ticket-bookings/<int:pk>/', vehicle_ticket_booking_views.vehicle_ticket_booking_detail_get_view, name='vehicle-ticket-booking-detail-get'),
    path('vehicle-ticket-bookings/<int:pk>/edit/', vehicle_ticket_booking_views.vehicle_ticket_booking_detail_post_view, name='vehicle-ticket-booking-detail-post'),
    path('vehicle-ticket-bookings/<int:pk>/delete/', vehicle_ticket_booking_views.vehicle_ticket_booking_delete_get_view, name='vehicle-ticket-booking-delete'),
    path('vehicle-ticket-bookings/<int:pk>/ticket-pdf/', vehicle_ticket_booking_views.vehicle_ticket_booking_ticket_pdf_view, name='vehicle-ticket-booking-ticket-pdf'),
]
