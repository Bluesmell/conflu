## API Reference (High-Level)

This document provides a basic overview of known API endpoints.
**Note:** Details regarding exact request/response schemas, all query parameters, specific authentication nuances per endpoint, and comprehensive status codes are not included here and would typically be found in a Swagger/OpenAPI specification.

---

### Spaces

*   **`GET /spaces/`**
    *   Description: Fetches a list of all spaces.
    *   Frontend Usage: `fetchSpaces()`
    *   Request Body: None
    *   Response Body: Array of Space objects (e.g., `[{ id, key, name, description }, ...]`)
    *   Permissions: Likely requires authentication.

*   **`GET /spaces/{spaceKey}/`**
    *   Description: Fetches details for a specific space.
    *   Frontend Usage: `fetchSpaceDetails(spaceKey)`
    *   Path Parameters: `spaceKey` (string)
    *   Request Body: None
    *   Response Body: Space object.
    *   Permissions: Likely requires authentication, possibly space-specific view permission.

---

### Pages

*   **`GET /spaces/{spaceKey}/pages/`**
    *   Description: Fetches a list of pages within a specific space.
    *   Frontend Usage: `fetchPagesInSpace(spaceKey)`
    *   Path Parameters: `spaceKey` (string)
    *   Request Body: None
    *   Response Body: Array of Page objects.
    *   Permissions: Likely requires authentication, space-specific view permission.

*   **`GET /pages/{pageId}/`**
    *   Description: Fetches details for a specific page.
    *   Frontend Usage: `fetchPageDetails(pageId)`
    *   Path Parameters: `pageId` (string or number)
    *   Request Body: None
    *   Response Body: Page object.
    *   Permissions: Likely requires authentication, page/space view permission.

*   **`POST /pages/`**
    *   Description: Creates a new page.
    *   Frontend Usage: `createPage(spaceKey, title, rawContent, parentPageId?)`
    *   Request Body: `PageCreatePayload` (e.g., `{ title, raw_content, space_key, parent_page_id? }`)
    *   Response Body: Created Page object.
    *   Permissions: Likely requires authentication, space-specific create page permission.

*   **`PUT /pages/{pageId}/`**
    *   Description: Updates an existing page.
    *   Frontend Usage: `updatePage(pageId, title, rawContent)`
    *   Path Parameters: `pageId` (string or number)
    *   Request Body: `PageUpdatePayload` (e.g., `{ title, raw_content }`)
    *   Response Body: Updated Page object.
    *   Permissions: Likely requires authentication, page/space edit permission.


---

### Importer (Confluence)

*   **`GET /io/import/confluence/status/{uploadId}/`**
    *   Description: Gets the status of a Confluence import task.
    *   Frontend Usage: `getConfluenceImportStatus(uploadId)`
    *   Path Parameters: `uploadId` (string or number)
    *   Response Body: `ConfluenceUpload` object (details from `importerModels.ts`).
    *   Permissions: Likely requires authentication.

*   **`POST /io/import/confluence/`**
    *   Description: Initiates a Confluence import.
    *   Frontend Usage: `initiateConfluenceImport(file, targetWorkspaceId?, targetSpaceId?)`
    *   Request Body: `FormData` containing the file and optional `target_workspace_id`, `target_space_id`.
    *   Content-Type: `multipart/form-data`
    *   Response Body: `ConfluenceUpload` object.
    *   Permissions: Likely requires authentication and import permissions.

---

### Search

*   **`GET /search/pages/`**
    *   Description: Searches for pages.
    *   Frontend Usage: `searchPages(params)`
    *   Query Parameters: `q` (string, search query), `space_key` (optional string). Potentially others for pagination.
    *   Response Body: Array of `PageSearchSerializer` objects.
    *   Permissions: Likely requires authentication.

---

### Workspace & Space Permissions

*   **`GET /workspaces/spaces/{spaceKey}/permissions/`**
    *   Description: Gets permissions for a specific space.
    *   Frontend Usage: `getSpacePermissions(spaceKey)`
    *   Path Parameters: `spaceKey` (string)
    *   Response Body: `SpacePermissionData` object.
    *   Permissions: Requires auth, likely space admin or specific permission to view permissions.

*   **`POST /workspaces/spaces/{spaceKey}/permissions/user/`**
    *   Description: Assigns space permissions to a user.
    *   Frontend Usage: `assignUserSpacePermission(spaceKey, userId, permissions)`
    *   Path Parameters: `spaceKey` (string)
    *   Request Body: `AssignPermissionPayload` (e.g., `{ user_id, permission_codenames }`)
    *   Response Body: Success message or updated permission data.
    *   Permissions: Requires auth, likely space admin.

*   **`POST /workspaces/spaces/{spaceKey}/permissions/group/`**
    *   Description: Assigns space permissions to a group.
    *   Frontend Usage: `assignGroupSpacePermission(spaceKey, groupId, permissions)`
    *   Path Parameters: `spaceKey` (string)
    *   Request Body: `AssignPermissionPayload` (e.g., `{ group_id, permission_codenames }`)
    *   Response Body: Success message or updated permission data.
    *   Permissions: Requires auth, likely space admin.

*   **`DELETE /workspaces/spaces/{spaceKey}/permissions/user/{userId}/`**
    *   Description: Removes a user's permissions from a space.
    *   Frontend Usage: `removeUserFromSpacePermissions(spaceKey, userId)`
    *   Path Parameters: `spaceKey` (string), `userId` (number)
    *   Response Body: Success message.
    *   Permissions: Requires auth, likely space admin.

*   **`DELETE /workspaces/spaces/{spaceKey}/permissions/group/{groupId}/`**
    *   Description: Removes a group's permissions from a space.
    *   Frontend Usage: `removeGroupFromSpacePermissions(spaceKey, groupId)`
    *   Path Parameters: `spaceKey` (string), `groupId` (number)
    *   Response Body: Success message.
    *   Permissions: Requires auth, likely space admin.

---

### Identity (Users & Groups)

*   **`GET /identity/users/`**
    *   Description: Lists users in the system.
    *   Frontend Usage: `listUsers()`
    *   Response Body: Array of User objects.
    *   Permissions: Requires auth, possibly admin/specific permission.

*   **`GET /identity/groups/`**
    *   Description: Lists groups in the system.
    *   Frontend Usage: `listGroups()`
    *   Response Body: Array of Group objects.
    *   Permissions: Requires auth, possibly admin/specific permission.

---

### Fallback Macros

*   **`GET /io/fallback-macros/{macroId}/`**
    *   Description: Gets details for a specific fallback macro.
    *   Frontend Usage: `getFallbackMacroDetails(macroId)`
    *   Path Parameters: `macroId` (number)
    *   Response Body: `FallbackMacro` object.
    *   Permissions: Requires auth.

---

### Diagram Validation

*   **`POST /io/diagrams/validate/mermaid/`**
    *   Description: Validates Mermaid diagram syntax.
    *   Frontend Usage: `validateMermaidSyntax(syntax)`
    *   Request Body: `MermaidValidationRequest` (e.g., `{ syntax }`)
    *   Response Body: `MermaidValidationResponse` object (e.g., `{ is_valid, error_message }`).
    *   Permissions: Requires auth.
