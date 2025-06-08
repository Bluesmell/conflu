

## User Account Management Update
User account management is now handled by `django-allauth` for core logic
(email verification, password reset flows, etc.) and `dj-rest-auth` for
providing API endpoints for these features (registration, login, logout,
password reset, email confirmation).

Key functionalities include:
- User registration with mandatory email verification.
- Login via username or email.
- Password reset via email.
- API endpoints under `/api/v1/auth/` and `/api/v1/auth/registration/`.

The previous custom registration view has been disabled.

## Confluence Importer

The `importer` app provides robust functionality to import content from Confluence space exports (ZIP files). It aims to preserve page structure, hierarchy, rich content, and attachments.

### Core Capabilities:

*   **Metadata-Driven Processing**: The importer primarily relies on the `entities.xml` (or similar metadata file) found in the Confluence export. This file is used as the source of truth for page IDs, titles, and hierarchy, ensuring data integrity.
*   **Asynchronous Import**: Imports are handled by a Celery task (`import_confluence_space`), allowing for background processing of potentially large exports without blocking the main application.
*   **Hierarchical Page Reconstruction**: Parent-child relationships between pages are accurately reconstructed based on the metadata.
*   **Rich Content Conversion**:
    *   HTML content from Confluence pages is parsed and converted into ProseMirror JSON format, suitable for modern editors.
    *   Supported HTML elements include:
        *   Paragraphs, headings (H1-H6)
        *   Bold, italic, links
        *   Unordered, ordered, and task lists (checkboxes based on `data-task-status`)
        *   Tables (including headers, `colspan`/`rowspan`)
        *   Code blocks (`<pre>`, with language detection from classes like `language-python` or `brush: lang;`)
        *   Blockquotes
        *   Horizontal rules (`<hr>`)
        *   Confluence panels (Info, Note, Warning, Tip - converted to blockquotes with a `panelType` attribute)
*   **Attachment Handling**:
    *   Extracts file attachments linked from pages.
    *   Stores these attachments using Django's file storage system.
    *   Links `Attachment` records to the corresponding imported `Page` records.
*   **Embedded Image Support**:
    *   `<img>` tags within page content are converted to ProseMirror `image` nodes.
    *   The `src` attributes of these image nodes are resolved to point to the URLs of the corresponding stored `Attachment` files.
*   **User-Selectable Import Target**:
    *   Users can specify a target Workspace and/or Space when initiating an import via the API.
    *   The importer task will place imported pages into the selected destination. Fallback logic exists if no target is specified.
*   **Comprehensive Test Suite**: The importer module is backed by extensive unit and integration tests to ensure reliability and maintainability.

### API Endpoint:

*   `POST /api/v1/io/import/confluence/`: Accepts a `multipart/form-data` request with a `file` field (the Confluence ZIP export) and optional `target_workspace_id` and `target_space_id` parameters to specify the import destination.

### Current Known Issues/Limitations:

*   The language detection for code blocks with `brush: language;` syntax might not cover all edge cases (see `test_code_block_with_brush_class`).
*   Mapping of original Confluence page IDs to HTML content files currently uses page titles parsed from HTML to match against titles from the metadata file. This could be made more robust if HTML files directly contained original page IDs (e.g., in comments or meta tags).

### Next Steps for the Importer:

*   **Enhanced ID Mapping**: Improve the linkage between page entries in `entities.xml` and their corresponding HTML content files, potentially by parsing IDs directly from HTML file content if available.
*   **Advanced Converter Features**:
    *   Support for more Confluence-specific macros (e.g., user mentions, dates, complex layouts).
    *   More nuanced whitespace and newline handling in the converter if specific issues are found.
*   **User Experience**:
    *   Implement detailed progress reporting for imports.
    *   Provide better error feedback and logging for users.
*   **Broader Project Goals**: For the overall Confluence clone, next steps would involve developing frontend capabilities for rendering pages, a ProseMirror-based editor, space/workspace management UIs, search, and user permissions.
