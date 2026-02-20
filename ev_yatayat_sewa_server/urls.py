"""
URL configuration for ev_yatayat_sewa_server project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from core.views.media_views import serve_media

urlpatterns = [
    # Media files - must be before admin URLs to bypass authentication
    re_path(r'^media/(?P<path>.*)$', serve_media, name='media'),
    # Booking first so /api/trips/current-stop/ etc. are matched; then core (auth, users, wallets)
    path('api/', include('booking.urls')),
    path('api/', include('core.urls')),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    path('', admin.site.urls),
]