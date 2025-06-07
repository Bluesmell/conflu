

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

## Confluence Importer (Initial Setup)
The `importer` app has been initialized to handle Confluence space imports.

Current capabilities (Proof of Concept):
- Basic API endpoint stub at `/api/v1/io/import/confluence/` to trigger an import.
- A Celery task `import_confluence_space` is defined to handle the import asynchronously.
- Utility functions in `importer.utils` can extract HTML files and potential metadata files
  (e.g., `entities.xml`) from an uploaded Confluence ZIP export.
- Initial HTML parsing logic in `importer.parser` can extract basic elements
  (title, H1s, paragraph samples) from HTML files using BeautifulSoup4 and lxml.
- The Celery task can currently use these utilities to extract and parse a few sample
  HTML files from a test ZIP, logging basic extracted info.
- Basic unit tests for the ZIP utilities and HTML parser have been added.

Next steps will involve developing the HTML-to-ProseMirror JSON conversion,
handling page hierarchy, processing attachments, and saving imported content
to the database.
