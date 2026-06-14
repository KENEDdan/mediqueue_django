from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/',        admin.site.urls),
    path('',              include('apps.accounts.urls')),
    path('clinics/',      include('apps.clinics.urls')),
    path('appointments/', include('apps.appointments.urls')),
    path('doctors/',      include('apps.doctors.urls')),
    path('superadmin/',   include('apps.superadmin.urls')),
    path('records/',      include('apps.records.urls')),
    path('finance/', include('apps.finance.urls')),
    path('api/', include('apps.api.urls')),
    path('notifications/', include('apps.notifications.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)