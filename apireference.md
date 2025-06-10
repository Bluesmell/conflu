## API Reference (High-Level Summary)

This document provides a manually-derived summary of known API endpoints, primarily based on frontend service analysis and backend code investigation.

**Primary Source of Truth**: For detailed and authoritative API specifications, please refer to the auto-generated documentation provided by `drf-spectacular`:
*   **Swagger UI**: `/api/v1/schema/swagger-ui/`
*   **ReDoc**: `/api/v1/schema/redoc/`

**Note:** Details regarding exact request/response schemas, all query parameters, comprehensive status codes, and nuances of authentication/authorization per endpoint are best found in the `drf-spectacular` schemas. This document aims to provide a quick reference and overview.

Base URL for all endpoints: `/api/v1` (proxied to the Django backend)

---

### Authentication (`dj-rest-auth`)

*   **Paths**:
    *   `/auth/` (e.g., login, logout, password change, user details)
    *   `/auth/registration/` (e.g., user registration)
*   **Description**: Standard authentication and registration endpoints provided by `dj-rest-auth` and `django-allauth`.
*   **Details**: Please refer to the `dj-rest-auth` and `django-allauth` documentation for specific endpoint paths (e.g., `/auth/login/`, `/auth/logout/`, `/auth/password/reset/`, `/auth/registration/verify-email/`, etc.), request/response schemas, and behavior.
*   **Permissions**: Vary by endpoint (e.g., public for registration/login, authenticated for logout/password change).

---

### Workspaces & Spaces

*   **Path**: `/workspaces/spaces/`
    *   *Note*: An older path ` /spaces/` might exist from frontend usage but `/workspaces/spaces/` is the one explicitly defined in `workspaces.urls.py` and should be preferred.
*   **View/ViewSet**: `workspaces.views.SpaceViewSet`
*   **Description**: Manages workspaces and spaces.
*   **Methods**: Standard ModelViewSet actions (GET list, POST create, GET retrieve, PUT update, PATCH partial_update, DELETE destroy).
*   **Lookup Field**: `key` (e.g., `/workspaces/spaces/{spaceKey}/`)
*   **Serializer**: `workspaces.serializers.SpaceSerializer`
*   **Permissions**: `core.permissions.DjangoObjectPermissionsOrAnonReadOnly`
*   **Notes**:
    *   `DELETE` operations perform a soft delete (marks the space as inactive).

---

### Space Permissions

*   **Base Path**: `/workspaces/spaces/{spaceKey}/permissions/`
    *   Path Parameter: `spaceKey` (string) - Key of the space to manage permissions for.

*   **`GET /`**
    *   **View**: `workspaces.views.ListSpacePermissionsView`
    *   **Description**: Lists all user and group permissions for the specified space.
    *   **Serializers**: `workspaces.serializers.SpaceUserPermissionSerializer`, `workspaces.serializers.SpaceGroupPermissionSerializer`
    *   **Permissions**: Requires `workspaces.admin_space` object permission on the space.

*   **`POST user/`**
    *   **View**: `workspaces.views.AssignUserSpacePermissionView`
    *   **Description**: Assigns specified permissions to a user for the space.
    *   **Request Serializer**: `workspaces.serializers.AssignUserPermissionSerializer` (e.g., `{ "user_id": <id>, "permission_codenames": ["codename1", "codename2"] }`)
    *   **Permissions**: Requires `workspaces.admin_space` object permission on the space.

*   **`POST group/`**
    *   **View**: `workspaces.views.AssignGroupSpacePermissionView`
    *   **Description**: Assigns specified permissions to a group for the space.
    *   **Request Serializer**: `workspaces.serializers.AssignGroupPermissionSerializer` (e.g., `{ "group_id": <id>, "permission_codenames": ["codename1", "codename2"] }`)
    *   **Permissions**: Requires `workspaces.admin_space` object permission on the space.

*   **`DELETE user/{userId}/`**
    *   **View**: `workspaces.views.RemoveUserSpacePermissionsView`
    *   **Description**: Removes all permissions for a specific user from the space.
    *   **Path Parameter**: `userId` (integer)
    *   **Permissions**: Requires `workspaces.admin_space` object permission on the space.

*   **`DELETE group/{groupId}/`**
    *   **View**: `workspaces.views.RemoveGroupSpacePermissionsView`
    *   **Description**: Removes all permissions for a specific group from the space.
    *   **Path Parameter**: `groupId` (integer)
    *   **Permissions**: Requires `workspaces.admin_space` object permission on the space.

---

### Content (Pages)

*   **Path**: `/content/pages/`
    *   *Note*: An older path `/pages/` might exist from frontend usage but `/content/pages/` is the one explicitly defined in `pages.urls.py` and should be preferred.
*   **View/ViewSet**: `pages.views.PageViewSet`
*   **Description**: Manages content pages.
*   **Methods**: Standard ModelViewSet actions (GET list, POST create, GET retrieve, PUT update, PATCH partial_update, DELETE destroy).
*   **Serializer**: `pages.serializers.PageSerializer`
*   **Permissions**: `core.permissions.ExtendedDjangoObjectPermissionsOrAnonReadOnly`
*   **Notes**:
    *   `DELETE` operations perform a hard delete.
*   **Custom Actions** (on detail route `/content/pages/{pk}/<action>/`):
    *   **`tags/` (POST)**
        *   Description: Adds a tag to the page.
        *   Request Body: `{ "tag": "name_or_id" }` (tag name or existing tag ID)
    *   **`tags/{tag_pk_or_name}/` (DELETE)**
        *   Description: Removes a tag from the page.
        *   Path Parameter: `tag_pk_or_name` (integer ID or string name of the tag)
    *   **`revert/{version_number_str}/` (POST)**
        *   Description: Reverts the page to a specific version.
        *   Path Parameter: `version_number_str` (string, e.g., "1", "2.1")
        *   Request Body: Optional `{ "commit_message": "Your reason for reverting" }`

---

### Page Versions

*   **Path**: `/pageversions/`
*   **View/ViewSet**: `pages.views.PageVersionViewSet` (registered in `api.urls`)
*   **Description**: Provides access to page version history.
*   **Methods**: ReadOnlyModelViewSet actions (GET list, GET retrieve).
*   **Serializer**: `pages.serializers.PageVersionSerializer`
*   **Permissions**: `rest_framework.permissions.IsAuthenticatedOrReadOnly`

---

### Tags

*   **Path**: `/tags/`
*   **View/ViewSet**: `pages.views.TagViewSet` (registered in `api.urls`)
*   **Description**: Manages tags that can be applied to pages.
*   **Methods**: Standard ModelViewSet actions.
*   **Serializer**: `pages.serializers.TagSerializer`
*   **Permissions**: `rest_framework.permissions.IsAuthenticatedOrReadOnly`

---

### Attachments

*   **Path**: `/attachments/`
*   **View/ViewSet**: `attachments.views.AttachmentViewSet` (registered in `api.urls`)
*   **Description**: Manages file attachments for pages.
*   **Methods**: Standard ModelViewSet actions.
*   **Serializer**: `attachments.serializers.AttachmentSerializer`
*   **Permissions**: `core.permissions.ExtendedDjangoObjectPermissionsOrAnonReadOnly`
*   **Query Parameters**:
    *   Can be filtered by `page` ID (e.g., `/attachments/?page=<page_id>`).
*   **Custom Actions** (on detail route `/attachments/{pk}/<action>/`):
    *   **`download/` (GET)**
        *   Description: Provides a secure download link/redirect for the attachment file. Checks scan status before allowing download.

---

### User Notifications

*   **Path**: `/notifications/`
*   **View/ViewSet**: `user_notifications.views.NotificationViewSet` (registered in `api.urls`)
*   **Description**: Manages notifications for the currently authenticated user.
*   **Methods**: GET list, GET retrieve, PUT update, PATCH partial_update, DELETE destroy. (Direct POST for creation is not typically exposed; notifications are usually system-generated).
*   **Queryset**: Automatically filtered to the notifications of the requesting user.
*   **Serializer**: `user_notifications.serializers.NotificationSerializer`
*   **Permissions**: `rest_framework.permissions.IsAuthenticated`
*   **Custom Actions**:
    *   **`mark-all-as-read/` (POST, list route)**: Marks all of the user's notifications as read.
    *   **`{pk}/mark-as-read/` (POST, detail route)**: Marks a specific notification as read.

---

### Activity Log

*   **Path**: `/activities/`
*   **View/ViewSet**: `core.views.ActivityViewSet` (registered in `api.urls`)
*   **Description**: Provides a read-only log of activities within the system.
*   **Methods**: ReadOnlyModelViewSet actions (GET list, GET retrieve).
*   **Serializer**: `core.serializers.ActivitySerializer`
*   **Permissions**: `rest_framework.permissions.IsAuthenticated`

---

### Identity (Users & Groups)

*   **Users Path**: `/identity/users/`
    *   **View**: `users.views.UserListView`
    *   **Description**: Lists users in the system.
    *   **Methods**: GET list.
    *   **Serializer**: `users.serializers.UserSimpleSerializer`
    *   **Permissions**: `rest_framework.permissions.IsAuthenticated`

*   **Groups Path**: `/identity/groups/`
    *   **View**: `users.views.GroupListView`
    *   **Description**: Lists groups in the system.
    *   **Methods**: GET list.
    *   **Serializer**: `users.serializers.GroupSerializer`
    *   **Permissions**: `rest_framework.permissions.IsAuthenticated`

---

### Importer (IO Operations)

*   **Base Path**: `/io/`

*   **Confluence Import**:
    *   **Path**: `import/confluence/`
    *   **View**: `importer.views.ConfluenceImportView`
    *   **Description**: Initiates a Confluence import process.
    *   **Methods**: POST.
    *   **Request Body**: `FormData` (`file`, `target_workspace_id?` (int), `target_space_id?` (int)).
    *   **Validation Serializer**: `importer.serializers.ConfluenceUploadSerializer` (used internally for validation of parameters).
    *   **Permissions**: `rest_framework.permissions.IsAuthenticated`

*   **Confluence Import Status**:
    *   **Path**: `import/confluence/status/{pk}/`
    *   **View**: `importer.views.ConfluenceUploadStatusView`
    *   **Description**: Gets the status of a specific Confluence import task.
    *   **Methods**: GET retrieve.
    *   **Path Parameter**: `pk` (integer ID of the ConfluenceUpload record).
    *   **Serializer**: `importer.serializers.ConfluenceUploadSerializer`
    *   **Permissions**: `rest_framework.permissions.IsAuthenticated`

*   **Fallback Macros**:
    *   **Path**: `fallback-macros/{pk}/`
    *   **View**: `importer.views.FallbackMacroDetailView`
    *   **Description**: Retrieves details of a specific fallback macro instance.
    *   **Methods**: GET retrieve.
    *   **Path Parameter**: `pk` (integer ID of the FallbackMacro record).
    *   **Serializer**: `importer.serializers.FallbackMacroSerializer`
    *   **Permissions**: `rest_framework.permissions.IsAuthenticated`

*   **Diagram Validation (Mermaid)**
    *   **Path**: `diagrams/validate/mermaid/`
    *   **View**: (Likely `importer.views.MermaidDiagramValidationView` - exact name to be confirmed if different)
    *   **Description**: Validates Mermaid diagram syntax.
    *   **Methods**: POST
    *   **Request Body**: `{ "syntax": "mermaid_diagram_string" }` (corresponds to `MermaidValidationRequest` in frontend)
    *   **Response Body**: `{ "is_valid": true/false, "error_message": "..." }` (corresponds to `MermaidValidationResponse` in frontend)
    *   **Permissions**: `rest_framework.permissions.IsAuthenticated`

---

### Page Search

*   **Path**: `/content/search/pages/` (defined in `pages.urls`)
*   **View**: `pages.views.PageSearchView`
*   **Description**: Searches for pages based on a query.
*   **Methods**: GET list.
*   **Query Parameters**:
    *   `q` (string): The search query.
    *   `space_key` (string, optional): Key of a space to limit search results.
*   **Serializer**: `pages.serializers.PageSearchSerializer`
*   **Permissions**: `rest_framework.permissions.IsAuthenticatedOrReadOnly`

---
