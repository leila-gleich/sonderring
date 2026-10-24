from django.urls import path
from . import oauth_views

app_name = 'oauth'

urlpatterns = [
    path('google/login/', oauth_views.google_login_view, name='google_login'),
    path('google/callback/', oauth_views.google_callback_view, name='google_callback'),
    path('google/dev-callback/', oauth_views.google_dev_callback_view, name='google_dev_callback'),
    path('google/unlink/', oauth_views.unlink_google_view, name='google_unlink'),
]
