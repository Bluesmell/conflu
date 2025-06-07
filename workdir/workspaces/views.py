
from django.utils import timezone
from rest_framework import viewsets
from guardian.shortcuts import assign_perm
from core.permissions import DjangoObjectPermissionsOrAnonReadOnly # Corrected import
from .models import Space
from .serializers import SpaceSerializer

class SpaceViewSet(viewsets.ModelViewSet):
    # Docstring updated here
    """
    ViewSet for managing Spaces.
    Provides CRUD operations for spaces.
    Object-level permissions (e.g., 'workspaces.view_space', 'workspaces.change_space',
    'workspaces.delete_space') are enforced using django-guardian. These are typically
    assigned to the space owner upon creation.
    Read access (list/retrieve) is generally allowed for anonymous users.
    """
    queryset = Space.objects.filter(is_deleted=False)
    serializer_class = SpaceSerializer
    lookup_field = 'key'
    permission_classes = [DjangoObjectPermissionsOrAnonReadOnly]

    def perform_create(self, serializer):
        # Docstring for method
        """Sets the owner of the space and assigns object permissions to the owner."""
        space = serializer.save(owner=self.request.user)
        user = self.request.user
        assign_perm('workspaces.view_space', user, space)
        assign_perm('workspaces.change_space', user, space)
        assign_perm('workspaces.delete_space', user, space)
        # print(f"Assigned view, change, delete permissions for space '{space.key}' to user '{user.username}'.")

    def perform_destroy(self, instance):
        # Docstring for method
        """Soft deletes a space (sets is_deleted=True and records deletion time)."""
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save()
