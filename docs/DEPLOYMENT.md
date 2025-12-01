# Deployment Guide

This document outlines how to run the AI FUN Token Wheel application locally with Docker and deploy it using Docker containers.

## Architecture

The application uses a **unified Docker architecture** where:

- A single Docker image contains both frontend (React) and backend (FastAPI)
- The FastAPI backend loads language models (GPT-2 and Llama 3.2 1B) via Hugging Face Transformers and serves the React frontend as static files
- Both models are pre-loaded in the Docker image for instant availability
- One container, one port (8000), one deployment

## Local Development with Docker

Run the application on your local machine using Docker Compose.

### Prerequisites

- Docker Desktop installed ([Download here](https://www.docker.com/products/docker-desktop))
- At least 4GB RAM allocated to Docker (for GPT-2)
- 8GB+ RAM recommended (to support both GPT-2 and Llama 3.2 1B)
- 10GB free disk space (for Docker image with pre-loaded models)

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

   **Note on models**:

   - Both GPT-2 and Llama 3.2 1B are pre-loaded in the Docker image
   - No download wait - models available immediately
   - First build takes longer (~10-15 minutes) due to model downloads
   - Subsequent runs start in seconds
   - Docker image size: ~7-8 GB

## Model Information

The application includes two pre-loaded language models, selectable via the UI:

### GPT-2 (Default)

- **Parameters**: 124M
- **RAM Required**: 2GB
- **Download Size**: ~500MB
- **Status**: Pre-loaded in Docker image
- **Authentication**: None required
- **Best For**: All students, basic laptops, guaranteed compatibility

### Llama 3.2 1B (Alternative)

- **Parameters**: 1.2B
- **RAM Required**: 6GB
- **Download Size**: ~5GB
- **Status**: Pre-loaded in Docker image
- **Authentication**: May require Hugging Face token (see below)
- **Best For**: Students with sufficient RAM who want to explore a modern model

### Hugging Face Authentication (Llama 3.2)

Llama models require Hugging Face authentication:

**Local Development (with .env file):**

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your token
# HF_TOKEN=your_token_here

# Start backend (will auto-load .env)
cd backend
uvicorn main:app --reload
```

**Docker Build (with build argument):**

```bash
# Pass token during build
docker build --build-arg HF_TOKEN=your_token_here -t ai-fun-token-wheel .

# Or using docker compose with environment variable
export HF_TOKEN="your_token_here"
docker compose build
```

**How to get a token:**

1. Create account at <https://huggingface.co>
2. Accept the Llama 3.2 1B license at <https://huggingface.co/meta-llama/Llama-3.2-1B>
3. Generate token at <https://huggingface.co/settings/tokens>
4. Use token in `.env` file (local) or as build arg (Docker)

**Without HF_TOKEN:**

- Build succeeds but only includes GPT-2
- Llama 3.2 1B shows as "Unavailable" in the UI dropdown
- All functionality works with GPT-2 alone

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

# Optional: Configure HF_TOKEN for Llama support
# cp ../.env.example ../.env
# Edit .env and add your token

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
2. Uses the `HF_TOKEN` repository secret to include both GPT-2 and Llama 3.2 1B
3. Pushes it to GitHub Container Registry with tags for both the commit SHA and `main`

This happens on every push to the main branch.

**Setting up HF_TOKEN for GitHub Actions:**

1. Get your HuggingFace token from <https://huggingface.co/settings/tokens>
2. Accept the Llama 3.2 1B license at <https://huggingface.co/meta-llama/Llama-3.2-1B>
3. Go to your repository → Settings → Secrets and variables → Actions
4. Click "New repository secret"
5. Name: `HF_TOKEN`
6. Value: Your HuggingFace token
7. Click "Add secret"

The workflow will automatically use this secret during Docker builds to include both models.

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
   # Basic run (both models pre-loaded in image)
   docker run -p 8000:8000 ghcr.io/YOUR_USERNAME/ai-fun-token-wheel:main

   # Or expose on different port
   docker run -p 8080:8080 -e PORT=8080 ghcr.io/YOUR_USERNAME/ai-fun-token-wheel:main
   ```

3. Ensure the container has sufficient RAM available (see Model Configuration below)

**Note**: If the image was built with `HF_TOKEN` in GitHub Actions, both models are included. Users can select between GPT-2 and Llama 3.2 1B via the UI dropdown.

### Model Configuration for Production

Both models are pre-loaded in the Docker image:

- GPT-2 (124M): Always included, works for all users
- Llama 3.2 1B: Included if HF token provided during build

**Memory planning**:

- Container needs minimum 8GB RAM to support both models
- Users can switch between models via UI
- GPT-2 will work on smaller instances (4GB RAM)
- Consider RAM limits when choosing Azure container size

**Azure Container Instances sizing**:

- **Small (4GB RAM, 2 vCPU)**: GPT-2 only - $35/month
- **Medium (8GB RAM, 2 vCPU)**: Both models - $70/month
- **Recommended**: Medium for full experience

**Build considerations**:

- **With HF_TOKEN**: Docker image is ~7-8GB (both models included)
- **Without HF_TOKEN**: Docker image is ~2GB (GPT-2 only)
- GitHub Actions workflow uses repository secret `HF_TOKEN` if available
- Set up secret: Repository Settings → Secrets and variables → Actions → New repository secret
- Users can switch between models via the UI dropdown (if both available)

## Troubleshooting

### Models not loading or unavailable

**Symptoms**:

- Application starts but only shows GPT-2 option
- Llama 3.2 1B shows as "Unavailable" in dropdown
- Error messages about missing models
- "Model not found" errors in logs

**GPT-2 issues**:

- GPT-2 should always work (no authentication needed)
- If failing, check Docker has internet access during build
- Verify Hugging Face is accessible: `curl -I https://huggingface.co`

**Llama 3.2 issues**:

- Llama requires authentication token during build
- If missing token, build succeeds but only includes GPT-2
- UI will show Llama as "Unavailable" - this is expected behavior

**Local development (adding Llama after initial setup)**:

  ```bash
  # Create .env file with your token
  cp .env.example .env
  # Edit .env and add: HF_TOKEN=your_token_here

  # Restart backend
  cd backend
  source venv/bin/activate
  uvicorn main:app --reload
  ```

**Docker (adding Llama after initial build)**:

  ```bash
  export HF_TOKEN="your_token_here"
  docker compose down
  docker compose build --no-cache
  docker compose up
  ```

**Verify you have access**:

1. Accept the license: <https://huggingface.co/meta-llama/Llama-3.2-1B>
2. Generate token: <https://huggingface.co/settings/tokens>
3. Test API call: `curl -H "Authorization: Bearer YOUR_TOKEN" https://huggingface.co/api/models/meta-llama/Llama-3.2-1B`

**Check which models are loaded at runtime**:

```bash
# View startup logs to see which models loaded
docker compose logs app | grep "Loading"

# Expected output with both models:
# Loading GPT-2 (124M)...
# ✓ GPT-2 (124M) ready
# Loading Llama 3.2 1B...
# ✓ Llama 3.2 1B ready

# Or check via API
curl http://localhost:8000/api/models
```

**Check which models are in the Docker image**:

```bash
docker compose exec app ls -la /home/appuser/.cache/huggingface/hub/
```

You should see:

- `models--gpt2` (always present)
- `models--meta-llama--Llama-3.2-1B` (if HF_TOKEN was provided during build)

### Memory issues

**Symptoms**:

- Application crashes when switching to Llama 3.2 1B
- "Killed" messages in logs
- Out of memory errors
- System becomes unresponsive

**Model RAM requirements**:

- **GPT-2**: ~2GB RAM needed (safe for 4GB systems)
- **Llama 3.2 1B**: ~6GB RAM needed (requires 8GB+ total system RAM)

**Solutions**:

1. **Check Docker memory allocation**:

   - Docker Desktop → Settings → Resources → Memory
   - For GPT-2 only: Allocate at least 4GB
   - For both models: Allocate at least 8GB
   - Apply & Restart Docker

2. **Stick to GPT-2 if you have limited RAM**:

   - The application will work fine with just GPT-2
   - All educational objectives met with default model
   - Llama 3.2 is an enhancement, not a requirement

3. **Close other applications**:

   - Free up system RAM before running Llama
   - Close browsers, IDEs, other memory-intensive apps

4. **Check actual memory usage**:

   ```bash
   # From inside container
   docker compose exec app python -c "import torch; print(torch.cuda.memory_allocated())"

   # From host system
   docker stats
   ```

**Educational note**: This memory limitation is an excellent teaching moment about the real-world costs of running AI models locally vs. using cloud APIs.

### Port conflicts (Local)

If port 8000 is in use, modify `docker-compose.yml`:

```yaml
ports:
  - "YOUR_PORT:8000"
```

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

## Dockerfile Model Pre-loading

The Dockerfile pre-downloads both models during build:

```dockerfile
# Pre-download GPT-2 (always included)
RUN python -c "from transformers import AutoModelForCausalLM, AutoTokenizer; \
    print('Downloading GPT-2...'); \
    AutoModelForCausalLM.from_pretrained('gpt2'); \
    AutoTokenizer.from_pretrained('gpt2'); \
    print('✓ GPT-2 ready')"

# Pre-download Llama 3.2 1B (if HF_TOKEN available)
ARG HF_TOKEN
RUN if [ -n "$HF_TOKEN" ]; then \
    python -c "from transformers import AutoModelForCausalLM, AutoTokenizer; \
    print('Downloading Llama 3.2 1B...'); \
    AutoModelForCausalLM.from_pretrained('meta-llama/Llama-3.2-1B', token='${HF_TOKEN}'); \
    AutoTokenizer.from_pretrained('meta-llama/Llama-3.2-1B', token='${HF_TOKEN}'); \
    print('✓ Llama 3.2 1B ready')"; \
else \
    echo "⚠ HF_TOKEN not provided, skipping Llama 3.2 1B"; \
fi
```

This approach:

- Downloads models once during build
- Caches in Docker layer for fast rebuilds
- Makes runtime startup instant
- Increases image size but improves user experience

## Advanced Usage

### Verify models in container

Check which models are available:

```bash
docker compose exec app ls -la /root/.cache/huggingface/hub/
```

Expected output:

```bash
models--gpt2                          # Always present
models--meta-llama--Llama-3.2-1B      # If auth successful
```

### Test model loading

Verify both models can be loaded:

```bash
docker compose exec app python -c "
from transformers import AutoModelForCausalLM, AutoTokenizer
print('Testing GPT-2...')
AutoModelForCausalLM.from_pretrained('gpt2')
print('✓ GPT-2 works')
print('Testing Llama 3.2 1B...')
AutoModelForCausalLM.from_pretrained('meta-llama/Llama-3.2-1B')
print('✓ Llama 3.2 1B works')
"
```

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
# GPT-2 only (no token required)
docker build -t ai-fun-token-wheel .
docker run -p 8000:8000 ai-fun-token-wheel

# Both models (with HF_TOKEN)
docker build --build-arg HF_TOKEN=your_token_here -t ai-fun-token-wheel .
docker run -p 8000:8000 ai-fun-token-wheel
```

**First build**: The initial build downloads models and may take 10-15 minutes depending on your internet connection and which models are included. Subsequent builds reuse cached layers and are much faster.

**Build time estimates**:

- First build with GPT-2 only: 5-7 minutes
- First build with both models: 10-15 minutes
- Rebuild with code changes only: 1-2 minutes
- Rebuild with dependency changes: 3-5 minutes

**Image size**:

- GPT-2 only: ~2GB
- Both models: ~7-8GB

## GitHub Codespaces

This project is configured for GitHub Codespaces. Click "Code" → "Codespaces" → "Create codespace" to get a pre-configured development environment in your browser.

Once created:

```bash
# GPT-2 only
docker compose up --build

# Or with both models (set HF_TOKEN in Codespaces secrets)
export HF_TOKEN="your_token_here"
docker compose up --build
```

The app will be available via Codespaces' port forwarding.

**Setting HF_TOKEN in Codespaces:**

1. Go to GitHub Settings → Codespaces → Secrets
2. Add new secret: `HF_TOKEN`
3. Set repository access to your project
4. The secret will be available as an environment variable in your codespace
