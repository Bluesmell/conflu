
from django.utils import timezone
from rest_framework import viewsets, permissions # Keep 'permissions' for SAFE_METHODS if needed later
from core.permissions import DjangoObjectPermissionsOrAnonReadOnly # Import shared class
from guardian.shortcuts import assign_perm
from .models import Space
from .serializers import SpaceSerializer

class SpaceViewSet(viewsets.ModelViewSet):
    queryset = Space.objects.filter(is_deleted=False)
    serializer_class = SpaceSerializer
    lookup_field = 'key'
    permission_classes = [DjangoObjectPermissionsOrAnonReadOnly] # Use shared class

    def perform_create(self, serializer):
        space = serializer.save(owner=self.request.user)
        user = self.request.user
        assign_perm('workspaces.view_space', user, space)
        assign_perm('workspaces.change_space', user, space)
        assign_perm('workspaces.delete_space', user, space)
        # print(f"Assigned view, change, delete permissions for space '{space.key}' to user '{user.username}'.")

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save()
