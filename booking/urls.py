from django.urls import path
from .views import (
    place_views,
    route_views,
    vehicle_views
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
]
