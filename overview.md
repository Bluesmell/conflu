# Project Overview

This document provides a high-level overview of the project structure, technologies used, and general strategies for code analysis.

## Backend (Python/Django - primarily in `workdir/`)

*   **Framework**: Django
*   **API**: Django REST Framework (assumed)
*   **Database**: PostgreSQL (primary), SQLite (dev/fallback)
*   **Task Queue**: Celery with Redis broker (for background tasks like Confluence imports)
*   **Monitoring**: Flower (for Celery tasks)
*   **LLM Integration**:
    *   `llama-cpp-python` (direct GGUF model loading)
    *   Ollama (via HTTP)
*   **Key Django Apps/Modules Observed**:
    *   `api`: General API endpoints.
    *   `attachments`: File attachment handling.
    *   `conflu_project_root_config`: Main Django project settings, Celery config.
    *   `core`: Core models, permissions, utilities.
    *   `importer`: Data import functionality (e.g., Confluence).
    *   `llm_integrations`: Large Language Model interactions.
    *   `notifications`: System notifications.
    *   `pages`: Content page management.
    *   `user_notifications`: User-specific notifications.
    *   `users`: User authentication and management.
    *   `workspaces`: Workspace and space organization.
*   **Deployment**: Docker and Docker Compose for local development and service orchestration.
*   **Dependencies**: Managed via `workdir/requirements.txt`.

## Frontend (TypeScript/React - primarily in `conflu_frontend/`)

*   **Framework/Library**: React
*   **Build Tool**: Vite
*   **Language**: TypeScript (`.tsx`)
*   **Editor**: Tiptap rich text editor, with extensions for:
    *   Basic formatting (StarterKit)
    *   Links, Images, Tables
    *   Code blocks with syntax highlighting (`lowlight`, `highlight.js`)
    *   Custom extensions (e.g., `FallbackMacroPlaceholderExtension`, `MermaidDiagramExtension`, `DrawioDiagramExtension`).
*   **HTTP Client**: `axios`
*   **Routing**: `react-router-dom` (assumed)
*   **Styling**: CSS (custom stylesheets, e.g., `TiptapEditor.css`)
*   **Key Components/Modules Observed**:
    *   `TiptapEditor.tsx`: Rich text editor.
    *   `RenderedPageContent.tsx`: Displays saved Tiptap content.
    *   `api.ts`: Backend API communication service.
    *   `apiModels.ts`, `importerModels.ts`: TypeScript interfaces for API data.
*   **Dependencies**: Managed via `conflu_frontend/package.json`.

## General Strategies for Identifying Unused Code/Components

1.  **Backend (Django):**
    *   **Coverage Tools**: `coverage.py` (identifies code executed during tests).
    *   **Static Analysis**: Linters like PyLint/Flake8 (unused imports/variables). `django-extensions` for specific Django checks.
    *   **Manual Review**: Check `urls.py` for unmapped views, models not used by views/serializers, uncalled helper functions, and inactive Celery tasks.

2.  **Frontend (React/TypeScript):**
    *   **Linters**: ESLint/TSLint (unused variables/imports).
    *   **IDE Features**: Highlighting of unused code.
    *   **Manual Review**: Trace component usage from main `App.tsx`/router. Look for unimported components, utilities, or types.
    *   **Specialized Tools**: `ts-prune` (unused TypeScript exports), `depcheck` (unused `package.json` dependencies).

### Important Considerations Before Removing Code:
*   **Test Coverage**: Ensure robust tests. Passing tests after removal is a good sign.
*   **Version Control (Git)**: Commit removals separately for easy reverts.
*   **Future Plans**: Consult with the team about code potentially reserved for upcoming features.
*   **Dynamic Usage**: Be cautious with code used dynamically (e.g., via reflection, signals) that static analysis might miss.
