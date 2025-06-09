from django.urls import path
from .views import ConfluenceImportView, ConfluenceUploadStatusView # Added ConfluenceUploadStatusView

app_name = 'importer'

urlpatterns = [
    path("import/confluence/", ConfluenceImportView.as_view(), name="confluence-import"),
    # New URL for status endpoint:
    path('import/confluence/status/<int:pk>/', ConfluenceUploadStatusView.as_view(), name='confluence-upload-status'),
]
