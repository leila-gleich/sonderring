from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Auth & Profiles
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('switch-user/', views.switch_user_view, name='switch_user'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.update_profile_view, name='update_profile'),
    path('profile/password/', views.change_password_view, name='change_password'),

    # Dashboard & Trip CRUD
    path('', views.dashboard_view, name='dashboard'),
    path('trips/create/', views.create_trip_view, name='create_trip'),
    path('trips/<uuid:trip_id>/', views.trip_workspace_view, name='trip_workspace'),
    path('trips/<uuid:trip_id>/edit/', views.edit_trip_view, name='edit_trip'),
    path('trips/<uuid:trip_id>/status/', views.update_trip_status_view, name='update_trip_status'),
    path('trips/<uuid:trip_id>/delete/', views.delete_trip_view, name='delete_trip'),

    # Move CRUD
    path('trips/<uuid:trip_id>/moves/add/', views.add_move_view, name='add_move'),
    path('trips/<uuid:trip_id>/moves/<uuid:move_id>/edit/', views.edit_move_view, name='edit_move'),
    path('trips/<uuid:trip_id>/moves/<uuid:move_id>/delete/', views.delete_move_view, name='delete_move'),

    # Stays CRUD
    path('trips/<uuid:trip_id>/stays/add/', views.add_stay_view, name='add_stay'),
    path('trips/<uuid:trip_id>/stays/<uuid:stay_id>/edit/', views.edit_stay_view, name='edit_stay'),
    path('trips/<uuid:trip_id>/stays/<uuid:stay_id>/delete/', views.delete_stay_view, name='delete_stay'),

    # Taste CRUD (Food & Drink)
    path('trips/<uuid:trip_id>/tastes/add/', views.add_taste_view, name='add_taste'),
    path('trips/<uuid:trip_id>/tastes/<uuid:taste_id>/edit/', views.edit_taste_view, name='edit_taste'),
    path('trips/<uuid:trip_id>/tastes/<uuid:taste_id>/delete/', views.delete_taste_view, name='delete_taste'),

    # Play CRUD (Activities, Sights, Experiences)
    path('trips/<uuid:trip_id>/plays/add/', views.add_play_view, name='add_play'),
    path('trips/<uuid:trip_id>/plays/<uuid:play_id>/edit/', views.edit_play_view, name='edit_play'),
    path('trips/<uuid:trip_id>/plays/<uuid:play_id>/delete/', views.delete_play_view, name='delete_play'),

    # Legacy Navs, Dos, Recs Routes (Aliases for backward compatibility)
    path('trips/<uuid:trip_id>/navs/add/', views.add_move_view, name='add_nav'),
    path('trips/<uuid:trip_id>/navs/<uuid:nav_id>/edit/', views.edit_move_view, name='edit_nav'),
    path('trips/<uuid:trip_id>/navs/<uuid:nav_id>/delete/', views.delete_move_view, name='delete_nav'),
    path('trips/<uuid:trip_id>/dos/add/', views.add_play_view, name='add_do'),
    path('trips/<uuid:trip_id>/dos/<uuid:do_id>/edit/', views.edit_play_view, name='edit_do'),
    path('trips/<uuid:trip_id>/dos/<uuid:do_id>/delete/', views.delete_play_view, name='delete_do'),
    path('trips/<uuid:trip_id>/recs/add/', views.add_taste_view, name='add_rec'),
    path('trips/<uuid:trip_id>/recs/<uuid:rec_id>/edit/', views.edit_taste_view, name='edit_rec'),
    path('trips/<uuid:trip_id>/recs/<uuid:rec_id>/delete/', views.delete_taste_view, name='delete_rec'),
    path('trips/<uuid:trip_id>/recs/<uuid:rec_id>/promote/', views.promote_rec_view, name='promote_rec'),
    path('trips/recommend/<str:rec_token>/', views.public_recommend_view, name='public_recommend'),

    # Membership Management
    path('trips/<uuid:trip_id>/members/invite/', views.invite_member_view, name='invite_member'),
    path('trips/<uuid:trip_id>/members/<uuid:member_id>/update-role/', views.update_member_role_view, name='update_member_role'),
    path('trips/<uuid:trip_id>/members/<uuid:member_id>/remove/', views.remove_member_view, name='remove_member'),

    # Vault Attachments
    path('trips/<uuid:trip_id>/vault/upload/', views.upload_attachment_view, name='upload_attachment'),
    path('trips/<uuid:trip_id>/vault/<uuid:attachment_id>/download/', views.download_attachment_view, name='download_attachment'),
    path('trips/<uuid:trip_id>/vault/<uuid:attachment_id>/delete/', views.delete_attachment_view, name='delete_attachment'),

    # Interactive AJAX Endpoints
    path('items/<str:item_type>/<uuid:item_id>/toggle-status/', views.toggle_item_status_view, name='toggle_status'),
    path('items/<str:item_type>/<uuid:item_id>/reveal-code/', views.reveal_confirmation_code_view, name='reveal_code'),
]
