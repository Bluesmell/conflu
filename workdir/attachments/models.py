from django.db import models
from django.conf import settings
from pages.models import Page
class Attachment(models.Model):
    SCAN_STATUS_CHOICES = [('pending', 'Pending Scan'), ('clean', 'Scan Clean'), ('infected', 'Scan Infected'), ('error', 'Scan Error'), ('skipped', 'Scan Skipped')]
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='attachments')
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_attachments')
    file_name = models.CharField(max_length=255)
    file = models.FileField(upload_to='attachments/%Y/%m/%d/')
    mime_type = models.CharField(max_length=100)
    size_bytes = models.BigIntegerField()
    scan_status = models.CharField(max_length=20, choices=SCAN_STATUS_CHOICES, default='pending', db_index=True)
    scanned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.file_name
    class Meta: ordering = ['-created_at']; verbose_name = "Attachment"; verbose_name_plural = "Attachments"
