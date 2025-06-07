from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from workspaces.views import SpaceViewSet
from pages.views import PageViewSet, PageVersionViewSet, TagViewSet # Added PageVersionViewSet
from users.views import UserRegistrationView

router = DefaultRouter()
router.register(r'spaces', SpaceViewSet, basename='space')
router.register(r'pages', PageViewSet, basename='page')
router.register(r'pageversions', PageVersionViewSet, basename='pageversion') # Added PageVersionViewSet
router.register(r'tags', TagViewSet, basename='tag')

auth_urlpatterns = [
    path('auth/register/', UserRegistrationView.as_view(), name='user_register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

urlpatterns = [
    path('', include(router.urls)),
    path('', include(auth_urlpatterns)),
]
