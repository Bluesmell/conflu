from django.db import models
from django.conf import settings
from workspaces.models import Space
import uuid # Required for Tag's default (though Tag doesn't have UUID here, PageVersion's FallbackMacro does, good to have for other models if needed)
class Page(models.Model):
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='pages')
    title = models.CharField(max_length=255, db_index=True)
    raw_content = models.JSONField(default=dict)
    schema_version = models.IntegerField(default=1)
    parent_page = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='child_pages')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='authored_pages')
    version = models.IntegerField(default=1)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return self.title
    class Meta: ordering = ['title']; verbose_name = "Page"; verbose_name_plural = "Pages"
class PageVersion(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField()
    raw_content = models.JSONField(default=dict)
    schema_version = models.IntegerField(default=1)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='authored_versions')
    commit_message = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.page.title} - v{self.version_number}"
    class Meta: ordering = ['-created_at']; verbose_name = "Page Version"; verbose_name_plural = "Page Versions"; unique_together = ('page', 'version_number')
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, db_index=True)
    pages = models.ManyToManyField(Page, related_name='tags', blank=True)
    def __str__(self): return self.name
    class Meta: ordering = ['name']; verbose_name = "Tag"; verbose_name_plural = "Tags"
