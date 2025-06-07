# core/permissions.py
from rest_framework import permissions

class DjangoObjectPermissionsOrAnonReadOnly(permissions.DjangoObjectPermissions):
    """
    Similar to DjangoObjectPermissions, but allows anonymous users SAFE_METHODS
    access. Authenticated users still need object permissions for unsafe methods
    on detail views and model permissions for unsafe methods on list views.
    """
    authenticated_users_only = False

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return super().has_permission(request, view)

class ExtendedDjangoObjectPermissionsOrAnonReadOnly(DjangoObjectPermissionsOrAnonReadOnly):
    """
    Extends DjangoObjectPermissionsOrAnonReadOnly to:
    1. Correctly map POST requests on detail routes (custom actions) to
       'change_<model_name>' object permission.
    2. Require 'view_<model_name>' object permission for GET requests on detail routes.
    """
    def get_required_object_permissions(self, method, model_cls):
        # Customized for POST on detail (custom actions)
        if method == 'POST':
            return [f'{model_cls._meta.app_label}.change_{model_cls._meta.model_name}']

        # Customized for GET on detail (retrieve actions)
        if method == 'GET' or method == 'HEAD' or method == 'OPTIONS': # Explicitly require view for GET/HEAD/OPTIONS
            # Note: DjangoObjectPermissions usually returns [] for these, relying on queryset.
            # We are making it stricter by requiring explicit 'view' object perm.
            return [f'{model_cls._meta.app_label}.view_{model_cls._meta.model_name}']

        # For other methods (PUT, PATCH, DELETE), rely on the standard mapping from DjangoObjectPermissions.
        # super().get_required_object_permissions will correctly use perms_map for these.
        # However, since DjangoObjectPermissions.perms_map is an instance variable and not easily
        # modifiable for only POST/GET, we explicitly list them or call super for default.
        # The original perms_map is:
        # perms_map = {
        #     'GET': [], 'OPTIONS': [], 'HEAD': [],
        #     'POST': ['%(app_label)s.add_%(model_name)s'],      # This is for list views (create)
        #     'PUT': ['%(app_label)s.change_%(model_name)s'],
        #     'PATCH': ['%(app_label)s.change_%(model_name)s'],
        #     'DELETE': ['%(app_label)s.delete_%(model_name)s'],
        # }
        # Our override for POST handles detail view POSTs.
        # Our override for GET/HEAD/OPTIONS requires view perm for detail views.
        # For PUT, PATCH, DELETE, the superclass method is fine.

        # Fallback to super for PUT, PATCH, DELETE which are correctly handled by DjangoObjectPermissions
        if method in ['PUT', 'PATCH', 'DELETE']:
             return super().get_required_object_permissions(method, model_cls)

        return [] # Default to no specific object permissions if method not covered above (should not happen for standard methods)
