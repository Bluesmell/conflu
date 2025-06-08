from django.db import models
from django.conf import settings

class Workspace(models.Model):
    name = models.CharField(max_length=200, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_workspaces' # User.owned_workspaces -> lists Workspaces
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Workspace"
        verbose_name_plural = "Workspaces"

    def __str__(self):
        return self.name

class Space(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='spaces', # Workspace.spaces -> lists Spaces
        null=True, # Temporarily nullable for migration ease
        blank=True
    )
    key = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='owned_spaces_direct' # Changed to avoid clash with Workspace.owner
    )
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        ws_name = self.workspace.name if self.workspace else "Unassigned"
        return f"{self.name} ({self.key}) - Workspace: {ws_name}"

    class Meta:
        ordering = ['workspace__name', 'name'] # Order by workspace name then space name
        verbose_name = "Space"
        verbose_name_plural = "Spaces"
