from django.urls import path
from .views import (
    ConfluenceImportView,
    ConfluenceUploadStatusView,
    FallbackMacroDetailView # Import the new view
)

app_name = 'importer'

urlpatterns = [
    path("import/confluence/", ConfluenceImportView.as_view(), name="confluence-import"),
    path('import/confluence/status/<int:pk>/', ConfluenceUploadStatusView.as_view(), name='confluence-upload-status'),
    path('fallback-macros/<int:pk>/', FallbackMacroDetailView.as_view(), name='fallbackmacro-detail'),
]
