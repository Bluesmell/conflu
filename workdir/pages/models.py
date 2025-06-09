from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.text import slugify # Added for slug generation
import uuid # Added for ensuring unique slugs and FallbackMacro

# Assuming workspaces.models.Space is correctly importable
# It's better to put this in a try-except if there's any doubt,
# but models.py usually requires direct imports to be resolvable at load time.
from workspaces.models import Space

# For SearchVectorField and GIN index
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.search import SearchVector


User = get_user_model()

# Helper function to extract text from ProseMirror JSON
def prosemirror_json_to_text(json_content):
    if not isinstance(json_content, dict) or 'content' not in json_content:
        return ''

    text_parts = []

    def extract_text_recursive(nodes):
        for node in nodes:
            if node.get('type') == 'text' and 'text' in node:
                text_parts.append(node['text'])
            if 'content' in node and isinstance(node['content'], list):
                extract_text_recursive(node['content'])

    extract_text_recursive(json_content['content'])
    return ' '.join(text_parts)


class Page(models.Model):
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='pages') # Existing, seems correct and non-nullable
    title = models.CharField(max_length=255, db_index=True)
    search_vector = SearchVectorField(null=True, blank=True, editable=False) # Added SearchVectorField
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True, # Auto-generated, so can be blank in forms initially
        help_text="URL-friendly identifier for the page. Auto-generated from title if not provided."
    )
    content_json = models.JSONField(default=dict, null=True, blank=True, help_text="Page content in ProseMirror JSON format.")
    original_confluence_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text="Original ID from Confluence, if applicable."
    )
    imported_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='imported_pages',
        help_text="User who imported this page."
    )
    schema_version = models.IntegerField(default=1)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='authored_pages'
    )
    version = models.IntegerField(default=1) # Current version number
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        help_text="Parent page for hierarchy."
    )
    is_deleted = models.BooleanField(default=False, db_index=True) # Existing field
    deleted_at = models.DateTimeField(null=True, blank=True)    # Existing field
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']
        verbose_name = "Page"
        verbose_name_plural = "Pages"
        indexes = [
            GinIndex(fields=['search_vector']), # Added GIN index
        ]
        # If slugs need to be unique only within a space or under a parent:
        # unique_together = (('space', 'slug'), ('parent', 'slug'))
        # For now, global unique slug is fine as per unique=True on field.

    def __str__(self):
        return self.title

    def update_search_vector(self):
        """Updates the search_vector field for the current page instance."""
        # Ensure raw_content (content_json) is converted to plain text
        plain_content = prosemirror_json_to_text(self.content_json)

        # Using 'A', 'B', 'C', 'D' for weights. 'A' is highest.
        vector = SearchVector('title', weight='A') + \
                   SearchVector(models.Value(plain_content), weight='B')
                   # Use models.Value for plain_content as it's not a direct field name

        # To avoid recursion with save() if this is called in save() and then save() is called again.
        # We use update explicitly here. This is better handled by signals or a separate management command.
        Page.objects.filter(pk=self.pk).update(search_vector=vector)


    def _generate_unique_slug(self):
        """
        Generates a unique slug for the page. If a slug already exists or is provided,
        it ensures uniqueness by appending a counter. If no title is available to
        generate a base slug, it uses a short UUID.
        """
        if not self.title and not self.slug: # Cannot generate slug if no title and no existing slug
             # Use a short UUID as a fallback if title is empty.
             # This might happen if a page is created programmatically without a title.
            base_slug = uuid.uuid4().hex[:8]
        elif self.slug: # If slug is provided (e.g. user edit or already exists)
            base_slug = self.slug # Use existing/provided slug as base
        else: # Generate from title
            base_slug = slugify(self.title)
            if not base_slug: # slugify resulted in empty string (e.g. title was all special chars)
                base_slug = uuid.uuid4().hex[:8]

        slug = base_slug
        counter = 1
        # Check for uniqueness, excluding self if self.pk exists (i.e. updating an existing instance)
        qs = Page.objects.filter(slug=slug)
        if self.pk:
            qs = qs.exclude(pk=self.pk)

        while qs.exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
            # Update queryset for next iteration
            qs = Page.objects.filter(slug=slug)
            if self.pk:
                 qs = qs.exclude(pk=self.pk)
        return slug

    def save(self, *args, **kwargs):
        # Generate slug only if it's not set or if it's a new instance and slug is empty.
        # If an existing instance's slug is being explicitly changed by user, this won't auto-overwrite it here,
        # but the _generate_unique_slug could be used to ensure that user-provided slug is made unique if needed.
        # For typical auto-slug generation, this is usually done on pre_save or if slug is empty.

        is_new = self._state.adding # Check if this is a new instance being added

        if not self.slug or (is_new and not self.slug):
            self.slug = self._generate_unique_slug()
        else:
            # If slug exists (either user-provided on new instance, or it's an update):
            # Ensure it's unique if it might have been changed to something non-unique.
            # The unique=True on the field will raise IntegrityError at DB level if not unique.
            # This explicit check can provide a cleaner way to make it unique before DB error.
            # However, for this iteration, we'll rely on the initial generation for new/empty slugs
            # and DB constraint for user-provided ones.
            # If a user *changes* the slug on an existing page, we might want to re-run uniqueness check.
            # For simplicity now: only generate if empty. DB handles user-set duplicates.
            # To ensure uniqueness if slug was manually changed to an existing one:
            current_slug_in_db = None
            if not is_new:
                try:
                    current_slug_in_db = Page.objects.get(pk=self.pk).slug
                except Page.DoesNotExist:
                    pass # Should not happen if self.pk exists for a non-new object

            if self.slug != current_slug_in_db: # If slug has changed or is new
                 # Check if the new self.slug (potentially set by user) clashes with others
                 qs = Page.objects.filter(slug=self.slug)
                 if self.pk: # Exclude self if updating
                     qs = qs.exclude(pk=self.pk)
                 if qs.exists(): # The user-set slug clashes
                     # Option 1: Raise ValidationError (better in form/serializer)
                     # Option 2: Make it unique here
                     self.slug = self._generate_unique_slug() # Re-generate based on potentially conflicting user slug

        super().save(*args, **kwargs)

# Signal to update search_vector when a Page is saved
@receiver(post_save, sender=Page)
def page_post_save(sender, instance, created, **kwargs):
    # We only update the search vector if the title or content_json might have changed.
    # For simplicity, we can update it on every save, or be more selective.
    # If 'update_fields' is used in save(), check if title or content_json are in it.
    if kwargs.get('raw', False): # Don't run during fixture loading
        return

    # Check if update_fields is present and if our relevant fields are being updated
    update_fields = kwargs.get('update_fields')
    if update_fields is not None and not ('title' in update_fields or 'content_json' in update_fields or 'search_vector' in update_fields):
         # If update_fields is specified and doesn't include title/content_json/search_vector, skip update.
         # This check helps avoid recursion if search_vector itself is in update_fields for some reason.
         if 'search_vector' in update_fields and len(update_fields) == 1: # only search_vector is being updated
             return # We are likely inside update_search_vector itself or similar.

    # instance.update_search_vector()
    # To avoid issues with calling save() within a signal that itself calls save(),
    # it's often better to perform the update using a queryset update for the specific field,
    # or connect to pre_save and modify the instance before it's saved.
    # For now, let's do a direct update.
    # This can be further optimized.

    plain_content = prosemirror_json_to_text(instance.content_json)
    Page.objects.filter(pk=instance.pk).update(
        search_vector=SearchVector('title', weight='A') + SearchVector(models.Value(plain_content), weight='B')
    )


class PageVersion(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField()
    content_json = models.JSONField(default=dict, help_text="Page content in ProseMirror JSON format for this version.")
    schema_version = models.IntegerField(default=1)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='authored_versions')
    commit_message = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.page.title} - v{self.version_number}"
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Page Version"
        verbose_name_plural = "Page Versions"
        unique_together = ('page', 'version_number')

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, db_index=True)
    pages = models.ManyToManyField(Page, related_name='tags', blank=True)
    def __str__(self): return self.name
    class Meta:
        ordering = ['name']
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

class Attachment(models.Model):
    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name='page_specific_attachments',
        help_text="The page this attachment belongs to."
    )
    original_filename = models.CharField(
        max_length=255,
        help_text="Original filename of the attachment."
    )
    file = models.FileField(
        upload_to='page_attachments/%Y/%m/%d/',
        help_text="The actual attachment file."
    )
    mime_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="MIME type of the attachment."
    )
    imported_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
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

# FallbackMacro model was previously in importer/models.py
# If it's truly page-specific, it could live here, or stay in importer if it's importer-specific.
# For now, assuming it's correctly placed in importer/models.py based on previous context.
# If it needs to be moved here, that's a separate refactoring.
# The prompt does not ask to move FallbackMacro.
