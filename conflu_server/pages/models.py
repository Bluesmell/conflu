from django.db import models
from django.contrib.auth.models import User # Or your custom user if you create one in users.models
import uuid

# Forward declaration for self-references if needed, or use 'self' as string
# class Space(models.Model): ... (defined in workspaces.models) - Decided to define here for now
# class Page(models.Model): ...

class Space(models.Model):
    key = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_spaces')
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.key})"

class Page(models.Model):
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='pages')
    title = models.CharField(max_length=255, db_index=True)
    raw_content = models.JSONField(default=dict, help_text="ProseMirror JSON representation of page content.")
    schema_version = models.IntegerField(default=1, help_text="Version of appSchema used for raw_content.")
    parent_page = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='child_pages')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='authored_pages')
    version = models.IntegerField(default=1, help_text="Current active version number.")
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class PageVersion(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField()
    raw_content = models.JSONField(default=dict)
    schema_version = models.IntegerField(default=1)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='authored_versions')
    commit_message = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.page.title} - v{self.version_number}"

class Attachment(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='attachments')
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_attachments')
    file_name = models.CharField(max_length=255)
    # file field will use Django's FileField, which works with django-storages
    file = models.FileField(upload_to='attachments/%Y/%m/%d/')
    mime_type = models.CharField(max_length=100)
    size_bytes = models.BigIntegerField()
    scan_status_choices = [
        ('pending', 'Pending Scan'),
        ('clean', 'Scan Clean'),
        ('infected', 'Scan Infected'),
        ('error', 'Scan Error'),
        ('skipped', 'Scan Skipped'),
    ]
    scan_status = models.CharField(max_length=20, choices=scan_status_choices, default='pending', db_index=True)
    scanned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name

class FallbackMacro(models.Model):
    # Assuming PageVersion is the correct link as per README, not Page
    page_version = models.ForeignKey(PageVersion, on_delete=models.CASCADE, related_name='fallback_macros')
    macro_name = models.CharField(max_length=100)
    raw_macro_content = models.TextField()
    import_notes = models.TextField(blank=True, null=True)
    # placeholder_id_in_content is UUIDField, ensure it's imported: import uuid
    # from uuid import uuid4 # at the top
    # placeholder_id_in_content = models.UUIDField(null=True, blank=True, unique=True, default=uuid.uuid4) # if default is needed
    placeholder_id_in_content = models.UUIDField(null=True, blank=True, unique=True)


    def __str__(self):
        return f"Fallback: {self.macro_name} for PageVersion {self.page_version_id}"

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, db_index=True)
    pages = models.ManyToManyField(Page, related_name='tags', blank=True)

    def __str__(self):
        return self.name
