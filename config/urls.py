"""
URL configuration for Sonderring v0 project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage

urlpatterns = [
    # Silently respond to Chrome DevTools automatic workspace probe
    path('.well-known/appspecific/com.chrome.devtools.json', lambda r: HttpResponse('{}', content_type='application/json')),
    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('images/favicon.png'), permanent=False)),
    path('admin/', admin.site.urls),
    path('oauth/', include('core.oauth_urls')),
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
