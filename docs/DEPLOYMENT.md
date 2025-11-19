# Deployment Guide

This document outlines how to run the AI FUN Token Wheel application using Docker Compose for local development and GitHub Codespaces for cloud-based development and deployment.

## GitHub Codespaces (Recommended)

The easiest way to run this application is with GitHub Codespaces. Everything is pre-configured and ready to go.

### Quick Start with Codespaces

1. **Open in Codespaces:**
   - Navigate to this repository on GitHub
   - Click the green "Code" button
   - Select the "Codespaces" tab
   - Click "Create codespace on main"

2. **Wait for Setup:**
   - GitHub will automatically build and start both the frontend and backend services
   - This takes 2-3 minutes on first launch (subsequent launches are faster)

3. **Access the Application:**
   - Once ready, you'll see port forwarding notifications
   - Click on the "Ports" tab in the VS Code terminal panel
   - **Frontend:** Click the globe icon next to port 3000 to open the application
   - **Backend API Docs:** Click the globe icon next to port 8000, then add `/docs` to the URL

### Codespaces Tips

- **Free Tier:** GitHub provides 60 hours/month free for all users (180 hours/month for students with GitHub Education)
- **Stopping:** Codespaces automatically stop after 30 minutes of inactivity
- **Restarting:** Just reopen your codespace - all your work is saved
- **Sharing:** You can make ports public to share your running app with others

## Local Development with Docker Compose

Run both the frontend and backend services on your local machine using Docker Compose.

### Prerequisites

- Docker Desktop installed ([Download here](https://www.docker.com/products/docker-desktop))
- At least 4GB RAM allocated to Docker

### Quick Start

1. **Build and Start Services:**

   From the project root directory, execute:

   ```bash
   docker-compose up --build
   ```

   This command builds the Docker images for both the frontend and backend, and then starts them.
   If you want to run them in the background:

   ```bash
   docker-compose up -d --build
   ```

2. **Access the Application:**

   Once the services are running, you can access the application:
   - **Frontend:** http://localhost:3000
   - **Backend API:** http://localhost:8000
   - **API Docs:** http://localhost:8000/docs

### Stop Services

To stop the running services:

```bash
docker-compose down
```

To stop services and remove associated volumes (including the Hugging Face model cache):

```bash
docker-compose down -v
```

### Development Mode

- **Backend:** The `docker-compose.yml` mounts the backend code into the container, so changes to Python files will be reflected (you may need to restart the backend service for changes to take effect).

- **Frontend:** For live development with hot-reloading, it's recommended to run the Vite development server directly on your host machine:

  ```bash
  cd frontend
  npm install
  npm run dev
  ```

  When running the frontend locally this way, it will automatically proxy `/api` requests to the backend running at `http://localhost:8000`.

## GitHub Container Registry

Docker images for this project are automatically built and published to GitHub Container Registry (GHCR) on every push to the main branch.

### Using Pre-built Images

You can pull and run the pre-built images without building them locally:

```bash
# Pull images
docker pull ghcr.io/YOUR_USERNAME/ai-fun-token-wheel-backend:latest
docker pull ghcr.io/YOUR_USERNAME/ai-fun-token-wheel-frontend:latest

# Run backend
docker run -p 8000:8000 ghcr.io/YOUR_USERNAME/ai-fun-token-wheel-backend:latest

# Run frontend (in another terminal)
docker run -p 3000:3000 ghcr.io/YOUR_USERNAME/ai-fun-token-wheel-frontend:latest
```

Replace `YOUR_USERNAME` with the GitHub username or organization name.

### Deploying to Other Platforms

The Docker images in GHCR can be deployed to various platforms:

- **Google Cloud Run:** Deploy directly from GHCR with one click
- **Azure Container Apps:** Import images from GHCR
- **AWS App Runner:** Pull from GHCR and deploy
- **Any server with Docker:** Use `docker-compose` with GHCR images

## Troubleshooting

### Models not loading

The first time the backend runs, it will download the GPT-2 model (~500MB). This is cached in the `huggingface-cache` volume locally. Be patient on first startup.

### Port conflicts (Local)

If ports 3000 or 8000 are in use on your local machine, modify the `ports` mappings in `docker-compose.yml`:

```yaml
ports:
  - "YOUR_PORT:3000"  # for frontend
  - "YOUR_PORT:8000"  # for backend
```

### Memory issues

PyTorch and the GPT-2 model require ~2GB RAM. Ensure Docker Desktop has sufficient memory allocated in its settings (Preferences → Resources → Memory).

### Viewing logs

For local Docker Compose logs:

```bash
docker-compose logs
docker-compose logs -f backend  # Follow backend logs
docker-compose logs -f frontend # Follow frontend logs
```

For GitHub Codespaces logs:

Check the Terminal panel in VS Code and look at the running services.

## Advanced Usage (Local Docker)

### Custom build arguments

You can pass custom build arguments to your Docker Compose build:

```bash
docker-compose build --build-arg PYTHON_VERSION=3.11
```

### Inspect running containers

```bash
docker-compose ps
docker-compose exec backend bash
docker-compose exec frontend sh
```

### Clean up everything

```bash
# Remove all Docker Compose containers, networks, and volumes
docker-compose down -v

# Remove all unused Docker objects (images, containers, volumes, networks)
docker system prune -a
```

### Using GHCR images in docker-compose

You can modify `docker-compose.yml` to use pre-built images from GHCR instead of building locally:

```yaml
services:
  backend:
    image: ghcr.io/YOUR_USERNAME/ai-fun-token-wheel-backend:latest
    # Remove the 'build' section

  frontend:
    image: ghcr.io/YOUR_USERNAME/ai-fun-token-wheel-frontend:latest
    # Remove the 'build' section
```

This is faster if images are already built and published.
