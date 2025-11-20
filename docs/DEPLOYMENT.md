# Deployment Guide

This document outlines how to run the AI FUN Token Wheel application locally with Docker and deploy it using Docker containers.

## Architecture

The application uses a **unified Docker architecture** where:

- A single Docker image contains both frontend (React) and backend (FastAPI)
- The FastAPI backend serves the React frontend as static files
- One container, one port (8000), one deployment

## Local Development with Docker

Run the application on your local machine using Docker Compose.

### Prerequisites

- Docker Desktop installed ([Download here](https://www.docker.com/products/docker-desktop))
- At least 4GB RAM allocated to Docker

### Quick Start

1. **Build and Start the Application:**

   From the project root directory:

   ```bash
   docker compose up --build
   ```

   To run in the background:

   ```bash
   docker compose up -d --build
   ```

2. **Access the Application:**

   Once running, access at:

   - **Application (Frontend + Backend):** <http://localhost:8000>
   - **API Documentation:** <http://localhost:8000/docs>

### Stop the Application

To stop the running application:

```bash
docker compose down
```

To stop and remove the Hugging Face model cache:

```bash
docker compose down -v
```

### Development Mode (Without Docker)

For local development with hot-reloading:

**Terminal 1 - Backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Terminal 2 - Frontend:**

```bash
cd frontend
npm install
npm run dev
```

When running this way:

- Frontend runs at <http://localhost:5173> (Vite dev server)
- Backend runs at <http://localhost:8000>
- Vite proxies `/api` requests to the backend

## GitHub Container Registry

Docker images are automatically built and published to GitHub Container Registry (GHCR) on every push to main.

### Automated Publishing

The project includes a GitHub Actions workflow that automatically:

1. Builds the unified Docker image (frontend + backend)
2. Pushes it to GitHub Container Registry with tags for both the commit SHA and `main`

This happens on every push to the main branch.

### Using Pre-built Images

Pull and run without building locally:

```bash
# Pull the latest image
docker pull ghcr.io/YOUR_USERNAME/ai-fun-token-wheel:main

# Run locally
docker run -p 8000:8000 ghcr.io/YOUR_USERNAME/ai-fun-token-wheel:main
```

Access at <http://localhost:8000>

### Using GHCR in docker compose

Modify `docker-compose.yml` to use pre-built images:

```yaml
services:
  app:
    image: ghcr.io/YOUR_USERNAME/ai-fun-token-wheel:main
    # Remove the 'build' section
```

This is faster than building locally.

## Production Deployment

### Deploy to Any Docker Host

Since the application is containerized, you can deploy it to any platform that supports Docker:

**Docker-based platforms:**

- Digital Ocean App Platform
- Railway
- Render
- Fly.io
- AWS ECS/Fargate
- Azure Container Instances
- Your own server with Docker

**General deployment steps:**

1. Pull the image from GHCR:

   ```bash
   docker pull ghcr.io/YOUR_USERNAME/ai-fun-token-wheel:main
   ```

2. Run the container:

   ```bash
   docker run -p 8000:8000 ghcr.io/YOUR_USERNAME/ai-fun-token-wheel:main
   ```

3. Ensure the container has at least 2GB of RAM available

**Note:** First run will download GPT-2 model (~500MB), which may take a moment. Subsequent runs use the cached model.

## Troubleshooting

### Models not loading

First run downloads GPT-2 (~500MB). This may take time on the initial startup. The model will be cached for subsequent runs.

### Port conflicts (Local)

If port 8000 is in use, modify `docker-compose.yml`:

```yaml
ports:
  - "YOUR_PORT:8000"
```

### Memory issues (Local)

PyTorch and GPT-2 require ~2GB RAM. Ensure Docker Desktop has sufficient memory:
Docker Desktop → Settings → Resources → Memory

### Viewing logs

**Local Docker logs:**

```bash
docker compose logs
docker compose logs -f app  # Follow logs in real-time
```

**Container logs (when running with docker run):**

```bash
docker logs <container_id>
docker logs -f <container_id>  # Follow logs in real-time
```

### Frontend not loading

If you see API responses but no UI:

- Check that `static/` directory exists in container
- Verify: `docker run -it ai-fun-token-wheel ls -la static/`

## Advanced Usage

### Inspect running container

```bash
docker compose ps
docker compose exec app bash
```

### Clean up everything

```bash
# Remove containers, networks, and volumes
docker compose down -v

# Remove all unused Docker objects
docker system prune -a
```

### Custom Docker build

Build manually:

```bash
docker build -t ai-fun-token-wheel .
docker run -p 8000:8000 ai-fun-token-wheel
```

## GitHub Codespaces

This project is configured for GitHub Codespaces. Click "Code" → "Codespaces" → "Create codespace" to get a pre-configured development environment in your browser.

Once created:

```bash
docker compose up --build
```

The app will be available via Codespaces' port forwarding.
