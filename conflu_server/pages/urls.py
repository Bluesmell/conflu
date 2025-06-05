from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SpaceViewSet, PageViewSet # PageVersionViewSet might be added later

router = DefaultRouter()
router.register(r'spaces', SpaceViewSet, basename='space')
router.register(r'pages', PageViewSet, basename='page')
# router.register(r'pageversions', PageVersionViewSet, basename='pageversion') # If PageVersionViewSet is activated

urlpatterns = [
    path('', include(router.urls)),
]
