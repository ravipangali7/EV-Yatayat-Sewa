from django.urls import path
from . import views

urlpatterns = [
    path('walkietalkie/groups/', views.group_list_view),
    path('walkietalkie/drivers/', views.drivers_list_view),
    path('walkietalkie/groups/<int:pk>/members/', views.group_members_view),
    path('walkietalkie/validate-token/', views.validate_token_view),
    path('walkietalkie/recordings/', views.recording_list_create_view),
    path('walkietalkie/recordings/<int:pk>/play/', views.recording_play_view),
]
