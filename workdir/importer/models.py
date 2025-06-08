from django.db import models
import uuid
from pages.models import PageVersion
from django.contrib.auth import get_user_model # Added
import os # Added

User = get_user_model() # Added

class FallbackMacro(models.Model):
    page_version = models.ForeignKey(PageVersion, on_delete=models.CASCADE, related_name='fallback_macros')
    macro_name = models.CharField(max_length=100)
    raw_macro_content = models.TextField()
    import_notes = models.TextField(blank=True, null=True)
    placeholder_id_in_content = models.UUIDField(null=True, blank=True, default=uuid.uuid4)
    def __str__(self): return f"Fallback for {self.macro_name}" # Simplified __str__
    class Meta: verbose_name = "Fallback Macro"; verbose_name_plural = "Fallback Macros"

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

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Confluence Upload"
        verbose_name_plural = "Confluence Uploads"

    def __str__(self):
        username = self.user.get_username() if self.user else 'Anonymous'
        file_name = os.path.basename(self.file.name) if self.file and self.file.name else "No file"
        return f"Import ID {self.pk or 'Unsaved'} ({file_name}) by {username} - Status: {self.get_status_display()}"
