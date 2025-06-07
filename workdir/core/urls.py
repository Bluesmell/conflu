from django.urls import path
from .views import sentry_test_view

urlpatterns = [
    path('sentry-debug/', sentry_test_view, name='sentry-debug'),
]
