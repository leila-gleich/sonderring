from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Auth & Profiles
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('switch-user/', views.switch_user_view, name='switch_user'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.update_profile_view, name='update_profile'),

    # Dashboard & Trip CRUD
    path('', views.dashboard_view, name='dashboard'),
    path('trips/create/', views.create_trip_view, name='create_trip'),
    path('trips/<uuid:trip_id>/', views.trip_workspace_view, name='trip_workspace'),
    path('trips/<uuid:trip_id>/edit/', views.edit_trip_view, name='edit_trip'),
    path('trips/<uuid:trip_id>/delete/', views.delete_trip_view, name='delete_trip'),

    # Stays CRUD
    path('trips/<uuid:trip_id>/stays/add/', views.add_stay_view, name='add_stay'),
    path('trips/<uuid:trip_id>/stays/<uuid:stay_id>/edit/', views.edit_stay_view, name='edit_stay'),
    path('trips/<uuid:trip_id>/stays/<uuid:stay_id>/delete/', views.delete_stay_view, name='delete_stay'),

    # Navs CRUD
    path('trips/<uuid:trip_id>/navs/add/', views.add_nav_view, name='add_nav'),
    path('trips/<uuid:trip_id>/navs/<uuid:nav_id>/edit/', views.edit_nav_view, name='edit_nav'),
    path('trips/<uuid:trip_id>/navs/<uuid:nav_id>/delete/', views.delete_nav_view, name='delete_nav'),

    # Dos CRUD
    path('trips/<uuid:trip_id>/dos/add/', views.add_do_view, name='add_do'),
    path('trips/<uuid:trip_id>/dos/<uuid:do_id>/edit/', views.edit_do_view, name='edit_do'),
    path('trips/<uuid:trip_id>/dos/<uuid:do_id>/delete/', views.delete_do_view, name='delete_do'),

    # Recs CRUD
    path('trips/<uuid:trip_id>/recs/add/', views.add_rec_view, name='add_rec'),
    path('trips/<uuid:trip_id>/recs/<uuid:rec_id>/edit/', views.edit_rec_view, name='edit_rec'),
    path('trips/<uuid:trip_id>/recs/<uuid:rec_id>/delete/', views.delete_rec_view, name='delete_rec'),
    path('trips/<uuid:trip_id>/recs/<uuid:rec_id>/promote/', views.promote_rec_view, name='promote_rec'),

    # Membership Management
    path('trips/<uuid:trip_id>/members/invite/', views.invite_member_view, name='invite_member'),
    path('trips/<uuid:trip_id>/members/<uuid:member_id>/update-role/', views.update_member_role_view, name='update_member_role'),
    path('trips/<uuid:trip_id>/members/<uuid:member_id>/remove/', views.remove_member_view, name='remove_member'),

    # Vault Attachments
    path('trips/<uuid:trip_id>/vault/upload/', views.upload_attachment_view, name='upload_attachment'),
    path('trips/<uuid:trip_id>/vault/<uuid:attachment_id>/delete/', views.delete_attachment_view, name='delete_attachment'),

    # Interactive AJAX Endpoints
    path('items/<str:item_type>/<uuid:item_id>/toggle-status/', views.toggle_item_status_view, name='toggle_status'),
    path('items/<str:item_type>/<uuid:item_id>/reveal-code/', views.reveal_confirmation_code_view, name='reveal_code'),
]
