# Local Deployment Guide for Confluence Importer

This guide provides instructions on how to set up and run the Confluence Importer project on your local system for development and testing.

## 1. Prerequisites

Ensure you have the following installed on your system:

*   **Git**: For cloning the repository.
*   **Python**: Version 3.10 or higher is recommended.
*   **pip**: Python package installer (usually comes with Python).
*   **Virtual Environment Tool**: Python's built-in `venv` module or `virtualenv`.
    *   To install `virtualenv`: `pip install virtualenv`
*   **Redis**: As a message broker for Celery.
    *   **macOS**: `brew install redis` then `brew services start redis`
    *   **Linux (Debian/Ubuntu)**: `sudo apt update && sudo apt install redis-server` then `sudo systemctl enable --now redis-server`
    *   **Windows**: Download from [Redis on Windows](https://github.com/microsoftarchive/redis/releases) or use WSL.

## 2. Project Setup

1.  **Clone the Repository**:
    ```bash
    git clone <your_repository_url_here>
    cd <repository_name> # e.g., cd workdir, or the actual repo root directory
    ```
    *(Note: For this environment, assume the user is already in the `workdir` which is the project root).*

2.  **Create and Activate Virtual Environment**:
    From the project root directory (`workdir`):
    ```bash
    python -m venv venv
    # On macOS/Linux:
    source venv/bin/activate
    # On Windows (cmd.exe):
    # venv\Scripts\activate.bat
    # On Windows (PowerShell):
    # venv\Scripts\Activate.ps1
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**:
    Copy the example environment file and customize it:
    ```bash
    cp .env.example .env
    ```
    Open the `.env` file and set the following variables:
    *   `SECRET_KEY`: Generate a new secret key. You can use Django's `get_random_secret_key()` utility or an online generator. For example: `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
    *   `DEBUG=True` (for local development)
    *   `DATABASE_URL=sqlite:///./db.sqlite3` (Default, uses SQLite in the project root)
    *   `CELERY_BROKER_URL=redis://localhost:6379/0` (Default Redis URL)
    *   `MEDIA_URL=/media/` (Default)
    *   `MEDIA_ROOT=mediafiles/` (Default, relative to project root. Ensure this directory exists or will be created by Django when files are uploaded.)

5.  **Apply Database Migrations**:
    ```bash
    python manage.py migrate
    ```

6.  **Create a Superuser Account**:
    This will allow you to access the Django admin interface and make authenticated API requests.
    ```bash
    python manage.py createsuperuser
    ```
    Follow the prompts to set a username, email, and password.

## 3. Running the Application Locally

You'll need to run three main components in separate terminal windows/tabs:

1.  **Start the Message Broker (Redis)**:
    Ensure your Redis server is running (it should be if you started it via `brew services` or `systemctl`). If not, start it manually (e.g., `redis-server` in a new terminal if installed manually).

2.  **Start the Celery Worker**:
    Open a new terminal in the project root (`workdir`), activate the virtual environment, and run:
    ```bash
    celery -A conflu_project_root_config.celery worker -l info
    ```
    *(The project name `conflu_project_root_config.celery` refers to where the Celery app instance is defined, typically in `conflu_project_root_config/celery.py`)*

3.  **Start the Django Development Server**:
    Open another terminal in the project root (`workdir`), activate the virtual environment, and run:
    ```bash
    python manage.py runserver
    ```
    By default, the server will be accessible at `http://127.0.0.1:8000/`.

## 4. Testing the Confluence Importer

1.  **Log In**:
    *   Open your browser and go to the Django admin interface: `http://127.0.0.1:8000/admin/`
    *   Log in with the superuser credentials you created. This sets up an authenticated session.

2.  **Prepare a Test ZIP File**:
    Create a ZIP file (e.g., `test_export.zip`) with the following structure and content:

    *   `entities.xml` (at the root of the ZIP):
        ```xml
        <hibernate-generic>
            <object class="Page">
                <property name="id"><long>101</long></property>
                <property name="title"><string>My Test Page</string></property>
            </object>
            <object class="Page">
                <property name="id"><long>102</long></property>
                <property name="title"><string>Child of Test Page</string></property>
                <property name="parent"><id>101</id></property>
            </object>
        </hibernate-generic>
        ```
    *   `My_Test_Page_101.html` (at the root of the ZIP, filename should allow ID extraction if title matching fails, but title matching is primary):
        ```html
        <html><head><title>My Test Page</title></head>
        <body><div id="main-content"><p>Content for my test page.</p> <img src="attachments/sample.png" alt="Sample Image"/></div></body></html>
        ```
    *   `Child_of_Test_Page_102.html` (at the root of the ZIP):
        ```html
        <html><head><title>Child of Test Page</title></head>
        <body><div id="main-content"><p>Content for the child page.</p></div></body></html>
        ```
    *   `attachments/` (folder at the root of the ZIP)
        *   `sample.png` (a small dummy PNG image file)

    *Note: The importer now primarily uses titles from `entities.xml` to match with titles parsed from HTML files. Ensure these titles are consistent. The filenames can also include IDs as a fallback or for human readability (e.g., `Title_ID.html`).*

3.  **Make the API Request**:
    You can use tools like `curl` or Postman, or a browser-based API client. Since you're logged into the admin, your browser session is authenticated.
    *   **Endpoint**: `POST /api/v1/io/import/confluence/` (Full URL: `http://127.0.0.1:8000/api/v1/io/import/confluence/`)
    *   **Method**: `POST`
    *   **Body Type**: `multipart/form-data`
    *   **Fields**:
        *   `file`: Select your `test_export.zip` file.
    *   **Headers**: If using `curl` or Postman, you'll need to handle authentication. The easiest way for local testing is often to grab the `csrftoken` and `sessionid` cookies after logging into the admin via your browser and include them in your request.
        *   For `curl` (example, replace placeholders):
            ```bash
            curl -X POST \
                 -H "X-CSRFToken: <your_csrftoken_here>" \
                 -H "Cookie: csrftoken=<your_csrftoken_here>; sessionid=<your_sessionid_here>" \
                 -F "file=@/path/to/your/test_export.zip" \
                 http://127.0.0.1:8000/api/v1/io/import/confluence/
            ```

4.  **Check Results**:
    *   The API should return a `202 ACCEPTED` response if the task is initiated.
    *   Check the Celery worker terminal for logs about the import process.
    *   Check the Django admin to see if `ConfluenceUpload` records are created and their status updates.
    *   Verify that `Page` and `Attachment` objects are created in the database.

## 5. Running Automated Tests

To run the project's automated test suite:

```bash
python manage.py test
```

To run tests for a specific app (e.g., the `importer` app):

```bash
python manage.py test workdir.importer
# Or just: python manage.py test importer
```
