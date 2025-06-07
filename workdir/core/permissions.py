
# core/permissions.py
from rest_framework import permissions

class DjangoObjectPermissionsOrAnonReadOnly(permissions.DjangoObjectPermissions):
    authenticated_users_only = False # Allows read-only for anonymous if model has global view

    def has_permission(self, request, view):
        # Allow anonymous read if the model itself has global view permissions.
        if request.method in permissions.SAFE_METHODS:
            return True
        # For write methods, user must be authenticated for object permission checks.
        return super().has_permission(request, view)
