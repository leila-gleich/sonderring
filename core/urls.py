from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Server-rendered pages
    path('', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('trips/<uuid:trip_id>/', views.trip_workspace_view, name='trip_workspace'),

    # REST API endpoints
    path('api/trips/', views.TripListCreateAPIView.as_view(), name='api_trips'),
    path('api/trips/<uuid:trip_id>/stays/', views.StayListCreateAPIView.as_view(), name='api_stays'),
]
