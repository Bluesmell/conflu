
from django.urls import path
from .views import ConfluenceImportView

urlpatterns = [
    path('confluence/', ConfluenceImportView.as_view(), name='confluence-import'),
]
