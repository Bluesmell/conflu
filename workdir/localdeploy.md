# Local Deployment and Setup Guide

This guide explains how to set up the Confluence Clone project locally for development, testing, and provides considerations for production deployment.

## 1. Prerequisites

Ensure you have the following software installed on your system:

*   **Git:** For cloning the repository.
*   **Docker:** For running containerized services.
*   **Docker Compose:** For orchestrating multi-container Docker applications.
*   **Python:** (e.g., 3.10+) If you plan to run backend services outside Docker or for certain helper scripts.
*   **Node.js & npm:** (e.g., Node.js LTS version) For managing and running the `conflu_frontend` React application.

## 2. Getting Started

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url> # Replace <repository_url> with the actual URL
    cd <repository_directory_name> # Navigate into the cloned project root
    ```

2.  **Navigate to Working Directory:**
    Most backend configurations and Docker setups are managed from the `workdir/` directory.
    ```bash
    cd workdir
    ```

## 3. Local Development & Testing (Using Docker Compose)

The `workdir/docker-compose.yml` file is configured to set up the backend services (Django web server, PostgreSQL database, Redis, Celery workers).

1.  **Configure Environment Variables:**
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Open the `.env` file and customize the variables. Key variables for local setup:
        *   `DJANGO_SECRET_KEY`: Set this to a unique, random string. The default in `.env.example` is insecure.
        *   `DJANGO_DEBUG`: Set to `True` for development.
        *   `DATABASE_URL`: Defaults to SQLite (`sqlite:///./db.sqlite3`). For PostgreSQL via Docker Compose, it's typically `postgres://conflu_user:conflu_password@db:5432/conflu_db` (matching services in `docker-compose.yml`).
        *   `CC_REDIS_URL`: Defaults to `redis://redis:6379/0` for Docker Compose.
        *   `CC_LLM_PROVIDER`: Choose `ollama_http` or `llama_cpp`.
            *   If `ollama_http`: Set `CC_OLLAMA_API_BASE_URL` (e.g., `http://host.docker.internal:11434` if Ollama runs on your host machine, or the service name if Ollama is another Docker container).
            *   If `llama_cpp`: Set `CC_LLM_MODEL_PATH` to the path *inside the web container* where the model will be mounted or copied. See LLM Configuration section.
        *   `DEFAULT_FILE_STORAGE_BACKEND`: Set to `local` for local filesystem storage for attachments. `MEDIA_ROOT` will be used.
        *   Review other variables in `.env.example` and adjust as needed.

2.  **Build and Run Services:**
    From the `workdir/` directory:
    ```bash
    docker-compose build
    docker-compose up -d
    ```
        This will build the Docker images for services like `backend`, `celeryworker`, and `flower` (if not already built or if their Dockerfile/context has changed) and start all services defined in `docker-compose.yml` in detached mode.

3.  **Run Database Migrations:**
    Once the services are running, apply database migrations:
    ```bash
    docker-compose exec web python manage.py migrate
    ```

4.  **Create a Superuser (Optional but Recommended):**
    To access the Django admin interface and manage users:
    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```
    Follow the prompts to create an admin account.

5.  **Accessing Services:**
    *   **Backend API:** Typically available at `http://localhost:8000/api/v1/` (or the port mapped in `docker-compose.yml`). The Django admin interface is at `http://localhost:8000/admin/`.
    *   **PostgreSQL Database:** Port `5432` is usually exposed to the host as `5433` (check `docker-compose.yml`).
    *   **Redis:** Port `6379` is usually exposed (check `docker-compose.yml`).
    *   **Flower (Celery Monitoring):** Accessible at `http://localhost:5555`. The Flower service is used to monitor Celery tasks and workers. It is now built using the project's main `Dockerfile` (the same one used for the `backend` and `celeryworker` services), and the `flower` package has been added to `requirements.txt`. Its command and environment are configured in `docker-compose.yml`.

6.  **Running Backend Tests:**
    To run the Django backend tests:
    ```bash
    docker-compose exec web pytest
    ```
    Or, if `pytest` is not the default test runner:
    ```bash
    docker-compose exec web python manage.py test
    ```

## 4. Setting up `conflu_frontend`

The `conflu_frontend` React application is located in the `conflu_frontend/` directory at the project root.

1.  **Navigate to Frontend Directory:**
    From the project root:
    ```bash
    cd conflu_frontend
    ```
    (If you were in `workdir/`, you'd do `cd .. && cd conflu_frontend`)

2.  **Install Dependencies:**
    ```bash
    npm install
    ```
    If you have pulled recent changes or are setting up for the first time, ensure you run this command to install all required dependencies as defined in `package.json`.

3.  **Run Development Server:**
    ```bash
    npm run dev
    ```
    This will typically start the Vite development server, often at `http://localhost:5173` (check your terminal output).

4.  **API Proxy Configuration:**
    The `conflu_frontend/vite.config.ts` file should be configured with a proxy to the backend API. Requests from the frontend to `/api` (or `/api/v1`) will be forwarded to your Django backend (e.g., `http://localhost:8000`). Ensure this matches your backend setup.

    Example proxy snippet in `vite.config.ts`:
    ```typescript
    // ...
    server: {
      proxy: {
        '/api': {
          target: 'http://localhost:8000', // Your Django backend URL
          changeOrigin: true,
        },
      },
    },
    // ...
    ```

## 5. LLM Configuration Details

The application supports local Large Language Models via `llama-cpp-python` or Ollama.

*   **Using `llama-cpp-python` (Direct GGUF model loading):**
    1.  **Download a GGUF Model:** Obtain a GGUF-quantized LLM (e.g., from Hugging Face). Models like Mistral 7B, Llama2 7B, or CodeLlama are good starting points.
    2.  **Make Model Accessible to Docker:**
        *   Place the downloaded `.gguf` file in a directory on your host machine (e.g., `./models` at the project root).
        *   Modify `workdir/docker-compose.yml` to mount this directory as a volume into the `web` service. For example:
            ```yaml
            # In workdir/docker-compose.yml, under services.web:
            volumes:
              - .:/app          # Mounts workdir to /app
              - ../models:/app/models # Mounts project_root/models to /app/models in container
            ```
    3.  **Configure `.env` (in `workdir/`):**
        *   Set `CC_LLM_PROVIDER=llama_cpp`
        *   Set `CC_LLM_MODEL_PATH=/app/models/your_model_name.gguf` (this is the path *inside* the container).
        *   Adjust `CC_LLM_N_GPU_LAYERS` if you have a compatible GPU and want to offload layers (0 for CPU only).

*   **Using Ollama:**
    1.  **Install and Run Ollama:** Follow the official Ollama documentation to install it on your host system and run an LLM (e.g., `ollama run mistral`).
    2.  **Configure `.env` (in `workdir/`):**
        *   Set `CC_LLM_PROVIDER=ollama_http`
        *   Set `CC_OLLAMA_API_BASE_URL` to your Ollama server's address.
            *   If Ollama runs directly on your host OS (not in Docker): `http://host.docker.internal:11434` (on Docker Desktop for Mac/Windows) or `http://<your_host_ip>:11434` (on Linux, replace `<your_host_ip>` with your machine's IP address on the Docker bridge network, often `172.17.0.1`).
            *   If Ollama runs as another Docker container on the same Docker network as `workdir` services, use its service name: `http://ollama_service_name:11434`.
    3.  Ensure the model you want to use (e.g., `mistral`) is available in your Ollama instance. You can set `CC_LLM_DEFAULT_MODEL_ALIAS` in `.env` to the Ollama model name.

## 6. Production Setup Considerations (High-Level)

The Docker Compose setup described above is primarily intended for local development and testing. For a production deployment, consider the following:

*   **Database:** Use a robust, managed PostgreSQL instance instead of the Dockerized one for better performance, reliability, and backup management. Update `DATABASE_URL` accordingly.
*   **Security:**
    *   Set `DJANGO_DEBUG=False`.
    *   Configure `DJANGO_ALLOWED_HOSTS` to your production domain(s).
    *   Ensure `DJANGO_SECRET_KEY` is a strong, unique secret managed securely (e.g., via environment variables injected by your hosting platform).
    *   Implement HTTPS for all traffic (e.g., using Nginx or Traefik as a reverse proxy with Let's Encrypt certificates).
*   **Static and Media Files:**
    *   Run `docker-compose exec web python manage.py collectstatic` (or equivalent in your deployment).
    *   Configure a web server like Nginx to serve static files (`STATIC_ROOT`) and media files (`MEDIA_ROOT`) directly for better performance. If using S3 for media, ensure `DEFAULT_FILE_STORAGE_BACKEND` (or equivalent like `STORAGES['default']['BACKEND']` for Django 4.2+) is set to `s3` and S3 credentials are correctly configured.
*   **Celery Workers & Beat:**
    *   Ensure Celery workers (and Celery Beat, if scheduled tasks are used beyond on-demand imports) are configured to run reliably in production (e.g., using a process manager like Supervisor or systemd within the container, or managed by your container orchestration platform).
*   **Resource Allocation:** Allocate sufficient CPU, RAM, and disk space for all services, especially the database, LLM services (if self-hosted), and Celery workers.
*   **Logging & Monitoring:** Set up centralized logging (e.g., ELK stack, Grafana Loki) and monitoring (e.g., Prometheus, Grafana, Sentry for error tracking) for your production instance.
*   **Backups:** Implement regular, automated backups for your database and any persistent storage (media files, Redis AOF/RDB if critical). Refer to the main project `README.md` or specific documentation on backup strategies.
*   **Secrets Management:** Use a secure method for managing secrets in production (e.g., HashiCorp Vault, AWS Secrets Manager, Kubernetes Secrets, or platform-specific environment variable injection).

For more detailed production guidelines, refer to the comprehensive project `README.md` or dedicated deployment documentation if available.
