
from django.utils import timezone
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes as drf_permission_classes # Renamed to avoid clash
from rest_framework.permissions import IsAuthenticated # For permission management views

from guardian.shortcuts import assign_perm, remove_perm, get_users_with_perms, get_groups_with_perms
from django.contrib.auth.models import User, Group # Direct import for User and Group
from django.shortcuts import get_object_or_404

from core.permissions import DjangoObjectPermissionsOrAnonReadOnly
from .models import Space
from .serializers import (
    SpaceSerializer,
    SpaceUserPermissionSerializer,
    SpaceGroupPermissionSerializer,
    AssignUserPermissionSerializer,
    AssignGroupPermissionSerializer
)


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

# --- APIViews for Space Permissions Management ---

class SpacePermissionBaseView(generics.GenericAPIView):
    """Base view for space permission operations, handles space retrieval and admin permission check."""
    permission_classes = [IsAuthenticated] # Must be authenticated

    def get_space_object(self):
        space_key = self.kwargs.get('space_key')
        space = get_object_or_404(Space, key=space_key, is_deleted=False)

        # Check if the requesting user has 'admin_space' permission on this specific space object
        if not self.request.user.has_perm('workspaces.admin_space', space):
            self.permission_denied(
                self.request, message="You do not have admin permissions for this space."
            )
        return space

class ListSpacePermissionsView(SpacePermissionBaseView):
    """
    GET /api/v1/spaces/{space_key}/permissions/
    Lists users and groups with their explicit permissions on a specific space.
    Requires 'admin_space' permission on the space.
    """
    def get(self, request, *args, **kwargs):
        space = self.get_space_object() # This also performs the permission check

        users_perms = get_users_with_perms(space, attach_perms=True, with_group_users=False)
        groups_perms = get_groups_with_perms(space, attach_perms=True)

        user_serializer = SpaceUserPermissionSerializer([
            {'user': user, 'permissions': sorted(list(perms))} for user, perms in users_perms.items() if perms # Only if perms exist
        ], many=True)

        group_serializer = SpaceGroupPermissionSerializer([
            {'group': group, 'permissions': sorted(list(perms))} for group, perms in groups_perms.items() if perms
        ], many=True)

        return Response({
            "space_key": space.key,
            "space_name": space.name,
            "users": user_serializer.data,
            "groups": group_serializer.data
        })

class AssignUserSpacePermissionView(SpacePermissionBaseView):
    """
    POST /api/v1/spaces/{space_key}/permissions/user/
    Assigns specified permissions for a user on a space.
    Requires 'admin_space' permission on the space.
    Payload: { "user_id": <user_id>, "permission_codenames": ["perm1", "perm2"] }
    """
    serializer_class = AssignUserPermissionSerializer

    def post(self, request, *args, **kwargs):
        space = self.get_space_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data['user_id']
        permission_codenames = serializer.validated_data['permission_codenames']

        try:
            user_to_assign = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": f"User with ID {user_id} not found."}, status=status.HTTP_404_NOT_FOUND)

        # Optional: Clear existing direct permissions for this user on this space first
        # This makes the operation a "set" rather than "add".
        # for perm in get_users_with_perms(space, attach_perms=True, with_group_users=False).get(user_to_assign, []):
        #    remove_perm(perm, user_to_assign, space)
        # For now, let's assume an additive approach or that client handles removal if "set" is desired.
        # A more robust approach might be a PUT to replace all permissions.

        for perm_codename in permission_codenames:
            assign_perm(f"workspaces.{perm_codename}", user_to_assign, space) # Assuming perms are app-prefixed if not custom
            # If codenames are exactly as in Meta (e.g. "view_space"), then "workspaces." might not be needed if model is Space
            # assign_perm(perm_codename, user_to_assign, space) # Use this if codenames are direct

        return Response({
            "message": f"Permissions {permission_codenames} assigned to user {user_to_assign.username} for space {space.key}."
        }, status=status.HTTP_200_OK)


class AssignGroupSpacePermissionView(SpacePermissionBaseView):
    """
    POST /api/v1/spaces/{space_key}/permissions/group/
    Assigns specified permissions for a group on a space.
    Requires 'admin_space' permission on the space.
    Payload: { "group_id": <group_id>, "permission_codenames": ["perm1", "perm2"] }
    """
    serializer_class = AssignGroupPermissionSerializer

    def post(self, request, *args, **kwargs):
        space = self.get_space_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_id = serializer.validated_data['group_id']
        permission_codenames = serializer.validated_data['permission_codenames']

        try:
            group_to_assign = Group.objects.get(pk=group_id)
        except Group.DoesNotExist:
            return Response({"error": f"Group with ID {group_id} not found."}, status=status.HTTP_404_NOT_FOUND)

        for perm_codename in permission_codenames:
            assign_perm(f"workspaces.{perm_codename}", group_to_assign, space)
            # assign_perm(perm_codename, group_to_assign, space) # if codenames are direct

        return Response({
            "message": f"Permissions {permission_codenames} assigned to group {group_to_assign.name} for space {space.key}."
        }, status=status.HTTP_200_OK)


class RemoveUserSpacePermissionsView(SpacePermissionBaseView):
    """
    DELETE /api/v1/spaces/{space_key}/permissions/user/{user_id}/
    Removes ALL direct permissions for a specific user from a space.
    Requires 'admin_space' permission on the space.
    """
    def delete(self, request, *args, **kwargs):
        space = self.get_space_object()
        user_id_to_remove = self.kwargs.get('user_id')

        try:
            user_to_remove = User.objects.get(pk=user_id_to_remove)
        except User.DoesNotExist:
            return Response({"error": f"User with ID {user_id_to_remove} not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get all permissions for the Space model to remove them comprehensively
        content_type = ContentType.objects.get_for_model(Space)
        space_permissions = Permission.objects.filter(content_type=content_type)

        removed_any = False
        for perm in space_permissions:
            if user_to_remove.has_perm(perm.codename, space) or user_to_remove.has_perm(f"{perm.content_type.app_label}.{perm.codename}", space):
                 # remove_perm expects codename without app_label for object perms usually
                remove_perm(perm.codename, user_to_remove, space)
                removed_any = True

        # A more direct way if you know all possible perms:
        # for perm_codename in ["view_space", "edit_space_content", "admin_space", "delete_space", "change_space", "add_space"]: # etc.
        #    remove_perm(perm_codename, user_to_remove, space)
        # This requires knowing all relevant codenames including built-ins.

        if removed_any:
            return Response({"message": f"All direct permissions for user {user_to_remove.username} on space {space.key} removed."}, status=status.HTTP_200_OK)
        else:
            return Response({"message": f"User {user_to_remove.username} had no direct permissions on space {space.key} to remove."}, status=status.HTTP_200_OK)


class RemoveGroupSpacePermissionsView(SpacePermissionBaseView):
    """
    DELETE /api/v1/spaces/{space_key}/permissions/group/{group_id}/
    Removes ALL permissions for a specific group from a space.
    Requires 'admin_space' permission on the space.
    """
    def delete(self, request, *args, **kwargs):
        space = self.get_space_object()
        group_id_to_remove = self.kwargs.get('group_id')

        try:
            group_to_remove = Group.objects.get(pk=group_id_to_remove)
        except Group.DoesNotExist:
            return Response({"error": f"Group with ID {group_id_to_remove} not found."}, status=status.HTTP_404_NOT_FOUND)

        content_type = ContentType.objects.get_for_model(Space)
        space_permissions = Permission.objects.filter(content_type=content_type)

        removed_any = False
        for perm in space_permissions:
            # Check and remove. Guardian's remove_perm for groups.
            # Group object perms are checked directly.
            if group_to_remove.permissions.filter(codename=perm.codename, content_type=content_type).exists(): # This checks global perms, not obj perms for group
                 # This check is not quite right for object permissions.
                 # Guardian handles group object permissions differently.
                 # The most straightforward way is to remove specific known permissions.
                 pass # Placeholder for correct group object permission removal logic

        # Corrected approach for removing all *object* permissions for a group from an object:
        # Iterate through known relevant permissions and remove them.
        known_perms_codenames = [p[0] for p in Space._meta.permissions] # Custom perms
        # Add built-in perms that might have been assigned (view_space, change_space, delete_space)
        # Note: Django Guardian stores group object permissions.
        # Need to iterate relevant permissions and call remove_perm for each.

        # Fetch all permissions assigned to the group for this specific space object
        obj_perms = get_perms(group_to_remove, space) # Get perms group has on object
        if obj_perms:
            for perm_codename in list(obj_perms): # list() to avoid issues if collection changes
                remove_perm(perm_codename, group_to_remove, space)
                removed_any = True

        if removed_any:
            return Response({"message": f"All permissions for group {group_to_remove.name} on space {space.key} removed."}, status=status.HTTP_200_OK)
        else:
            return Response({"message": f"Group {group_to_remove.name} had no permissions on space {space.key} to remove."}, status=status.HTTP_200_OK)

# Need to import ContentType and Permission for the delete views if not already imported
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from guardian.shortcuts import get_perms # For RemoveGroupSpacePermissionsView
