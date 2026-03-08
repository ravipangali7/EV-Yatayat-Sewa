from django.urls import path
from . import views

urlpatterns = [
    path('walkietalkie/groups/', views.group_list_view),
    path('walkietalkie/drivers/', views.drivers_list_view),
    path('walkietalkie/admins/', views.admins_list_view),
    path('walkietalkie/groups/<int:pk>/members/', views.group_members_view),
    path('walkietalkie/validate-token/', views.validate_token_view),
    path('walkietalkie/recordings/', views.recording_list_create_view),
    path('walkietalkie/recordings/<int:pk>/play/', views.recording_play_view),
    path('walkietalkie/direct-messages/', views.direct_message_list_create_view),
    path('walkietalkie/direct-messages/<int:pk>/play/', views.direct_message_play_view),
    path('walkietalkie/direct-messages/<int:pk>/', views.direct_message_partial_update_view),
]
