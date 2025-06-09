from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('accounts/', include('allauth.urls')), # Corrected: removed extra \n from previous script
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')), # General API, auth etc.
    path('api/v1/identity/', include('users.urls')), # Added users app URLs (for user/group lists)
    path('api/v1/workspaces/', include('workspaces.urls')),
    path('api/v1/content/', include('pages.urls')),
    path('debug/', include('core.urls')),
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
