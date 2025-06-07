from django.urls import path, include
from rest_framework.routers import DefaultRouter
# from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView # Not directly used, dj_rest_auth handles
# from users.views import UserRegistrationView # Already Commented out, allauth/dj-rest-auth handles registration

# App specific viewset imports
from workspaces.views import SpaceViewSet
from pages.views import PageViewSet, PageVersionViewSet, TagViewSet
from attachments.views import AttachmentViewSet
from user_notifications.views import NotificationViewSet, ActivityViewSet

router = DefaultRouter()

# App specific router registrations
router.register(r'spaces', SpaceViewSet, basename='space')
router.register(r'pages', PageViewSet, basename='page')
router.register(r'pageversions', PageVersionViewSet, basename='pageversion')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'attachments', AttachmentViewSet, basename='attachment')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'activities', ActivityViewSet, basename='activity')

# dj-rest-auth URLs will provide:
# /auth/login/
# /auth/logout/
# /auth/password/reset/
# /auth/password/reset/confirm/
# /auth/password/change/
# /auth/user/ (User details)
# /auth/token/verify/ (if JWT is used)
# /auth/token/refresh/ (if JWT is used and refresh tokens are enabled)
# dj-rest-auth.registration URLs will provide:
# /auth/registration/ (uses django-allauth for registration)
# /auth/registration/verify-email/
# /auth/registration/resend-email/
# /auth/registration/account-confirm-email/[key]/

urlpatterns = [
    path('io/import/', include('importer.urls')),
    path('', include(router.urls)), # Includes all registered ViewSets
    path('auth/', include('dj_rest_auth.urls')),
    path('auth/registration/', include('dj_rest_auth.registration.urls')),
]
