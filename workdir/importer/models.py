from django.db import models
import uuid
from pages.models import PageVersion # FallbackMacro depends on this
from django.contrib.auth import get_user_model
import os

User = get_user_model()

try:
    from workspaces.models import Workspace, Space
except ImportError:
    # These should ideally always be available due to app dependencies.
    # If not, Django will fail at a higher level (e.g., startup or when resolving relations).
    Workspace = None
    Space = None
    print("CRITICAL WARNING: importer/models.py - Workspace/Space models from workspaces.models not found. This will likely cause errors.")


class FallbackMacro(models.Model): # Existing model, ensure it's preserved
    page_version = models.ForeignKey(PageVersion, on_delete=models.CASCADE, related_name='fallback_macros')
    macro_name = models.CharField(max_length=100)
    raw_macro_content = models.TextField()
    import_notes = models.TextField(blank=True, null=True)
    placeholder_id_in_content = models.UUIDField(null=True, blank=True, default=uuid.uuid4)
    def __str__(self): return f"Fallback for {self.macro_name}"
    class Meta:
        verbose_name = "Fallback Macro"
        verbose_name_plural = "Fallback Macros"
        app_label = 'importer'


class ConfluenceUpload(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_PROCESSING = 'PROCESSING'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_FAILED = 'FAILED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confluence_uploads'
    )
    file = models.FileField(
        upload_to='confluence_imports/%Y/%m/%d/',
        help_text="Uploaded Confluence ZIP export file."
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the file was uploaded."
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        help_text="Current status of the import process."
    )
    task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Celery task ID for the import process."
    )

    # Target fields - defined directly assuming Workspace and Space are available
    target_workspace = models.ForeignKey(
        Workspace if Workspace else 'workspaces.Workspace', # String reference if Workspace is None at this point
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confluence_uploads_as_target_ws', # Unique related_name
        help_text="Optional: The specific workspace to import content into."
    )

    target_space = models.ForeignKey(
        Space if Space else 'workspaces.Space', # String reference if Space is None
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confluence_uploads_as_target_sp', # Unique related_name
        help_text="Optional: The specific space to import content into. Must belong to target_workspace if set."
    )

    # New fields for progress tracking:
    pages_succeeded_count = models.IntegerField(default=0, help_text="Number of pages successfully imported.")
    pages_failed_count = models.IntegerField(default=0, help_text="Number of pages that failed to import.")
    attachments_succeeded_count = models.IntegerField(default=0, help_text="Number of attachments successfully processed.")

    progress_message = models.CharField(max_length=255, null=True, blank=True, help_text="Current stage or progress message of the import.")
    error_details = models.TextField(null=True, blank=True, help_text="Summary of errors encountered during import.")

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Confluence Upload"
        verbose_name_plural = "Confluence Uploads"
        app_label = 'importer'

    def __str__(self):
        username = self.user.get_username() if self.user else 'Anonymous'
        file_name = os.path.basename(self.file.name) if self.file and self.file.name else "No file"
        return f"Import ID {self.pk or 'Unsaved'} ({file_name}) by {username} - Status: {self.get_status_display()}"
