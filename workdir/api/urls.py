
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# App specific viewset imports
from workspaces.views import SpaceViewSet
from pages.views import PageViewSet, PageVersionViewSet, TagViewSet
from attachments.views import AttachmentViewSet
from users.views import UserRegistrationView
from user_notifications.views import NotificationViewSet, ActivityViewSet
# User Notifications views will be added below

router = DefaultRouter()

# App specific router registrations
router.register(r'spaces', SpaceViewSet, basename='space')
router.register(r'pages', PageViewSet, basename='page')
router.register(r'pageversions', PageVersionViewSet, basename='pageversion')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'attachments', AttachmentViewSet, basename='attachment')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'activities', ActivityViewSet, basename='activity')
# User Notifications routes will be added below

# Auth routes (typically not part of the main router for custom paths)
auth_urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user_register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'), # Changed from token_obtain to login
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

urlpatterns = [
    path('', include(router.urls)), # Includes all registered ViewSets
    path('auth/', include(auth_urlpatterns)), # Auth routes typically under /api/v1/auth/
]
