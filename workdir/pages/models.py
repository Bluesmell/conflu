from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model # Added for imported_by
from workspaces.models import Space
import uuid # Required for Tag's default (though Tag doesn't have UUID here, PageVersion's FallbackMacro does, good to have for other models if needed)

User = get_user_model() # Define User

class Page(models.Model):
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='pages')
    title = models.CharField(max_length=255, db_index=True)

    # Renaming raw_content to content_json and adding help_text as per new model definition for clarity
    content_json = models.JSONField(default=dict, help_text="Page content in ProseMirror JSON format.")

    original_confluence_id = models.CharField(
        max_length=255,
        unique=True, # Ensures no duplicate Confluence pages are imported based on this ID
        null=True,
        blank=True, # Allow pages not originating from Confluence
        help_text="Original ID from Confluence, if applicable."
    )
    imported_by = models.ForeignKey(
        User, # Using User from get_user_model()
        on_delete=models.SET_NULL,
        null=True,
        blank=True, # Allow blank if not all pages are 'imported'
        related_name='imported_pages',
        help_text="User who imported this page."
    )

    schema_version = models.IntegerField(default=1)
    # Removed existing parent_page, will add new 'parent' field
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='authored_pages')
    version = models.IntegerField(default=1)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        help_text="Parent page for hierarchy."
    )
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self): return self.title # Kept simple

    class Meta:
        ordering = ['title']
        verbose_name = "Page"
        verbose_name_plural = "Pages"
class PageVersion(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField()
    # Assuming raw_content here should also be content_json or similar if we're standardizing
    # For now, leaving as is, as subtask focused on Page and new Attachment model
    content_json = models.JSONField(default=dict, help_text="Page content in ProseMirror JSON format for this version.") # Renamed for consistency
    schema_version = models.IntegerField(default=1)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='authored_versions') # Remains settings.AUTH_USER_MODEL
    commit_message = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.page.title} - v{self.version_number}" # Page.title comes from the modified Page model
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Page Version"
        verbose_name_plural = "Page Versions"
        unique_together = ('page', 'version_number')
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, db_index=True)
    pages = models.ManyToManyField(Page, related_name='tags', blank=True) # Page refers to the modified Page model
    def __str__(self): return self.name
    class Meta:
        ordering = ['name']
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

# New Attachment model
class Attachment(models.Model):
    page = models.ForeignKey(
        Page, # Refers to the modified Page model above
        on_delete=models.CASCADE,
        related_name='page_specific_attachments', # Changed to avoid clash
        help_text="The page this attachment belongs to."
    )
    original_filename = models.CharField(
        max_length=255,
        help_text="Original filename of the attachment."
    )
    file = models.FileField(
        upload_to='page_attachments/%Y/%m/%d/', # Structured upload path
        help_text="The actual attachment file."
    )
    mime_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="MIME type of the attachment."
    )

    imported_by = models.ForeignKey(
        User, # Using User from get_user_model()
        on_delete=models.SET_NULL,
        null=True,
        blank=True, # Allow blank if not all attachments are 'imported'
        related_name='imported_attachments',
        help_text="User who imported this attachment."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['original_filename']
        verbose_name = "Attachment"
        verbose_name_plural = "Attachments"

    def __str__(self):
        return self.original_filename
