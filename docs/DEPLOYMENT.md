# Deployment Guide

This document outlines how to run the AI FUN Token Wheel application locally with Docker and deploy it to production using Google Cloud Run.

## Architecture

The application uses a **unifsied Docker architecture** where:

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

## Production Deployment with Google Cloud Run

Deploy to Google Cloud Run for a public, scalable URL that students can access.

### Prerequisites

- Google Cloud account ([Sign up here](https://cloud.google.com/))
- gcloud CLI installed ([Installation guide](https://cloud.google.com/sdk/docs/install))
- A Google Cloud project created

### Setup

1. **Authenticate with Google Cloud:**

   ```bash
   gcloud auth login
   ```

2. **Set your project:**

   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Enable required APIs:**

   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   ```

### Manual Deployment

From the project root directory:

```bash
gcloud run deploy ai-token-wheel \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --port 8000 \
  --timeout 300
```

After deployment, you'll see a URL like:

```url
https://ai-token-wheel-xxxxx-uc.a.run.app
```

**This is your public URL!** Share it with students.

### Deployment from GitHub Container Registry

If you've pushed images to GHCR via GitHub Actions:

```bash
gcloud run deploy ai-token-wheel \
  --image ghcr.io/YOUR_USERNAME/ai-fun-token-wheel:main \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --port 8000 \
  --timeout 300
```

### Automated Deployment from GitHub

The project includes GitHub Actions that automatically deploy to Cloud Run on every push to main.

**Setup:**

1. **Create a Google Cloud service account:**

   ```bash
   gcloud iam service-accounts create github-deploy \
     --display-name="GitHub Deploy Service Account"

   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:github-deploy@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/run.admin"

   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:github-deploy@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/iam.serviceAccountUser"

   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:github-deploy@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/storage.admin"
   ```

2. **Create and download a service account key:**

   ```bash
   gcloud iam service-accounts keys create key.json \
     --iam-account=github-deploy@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

3. **Add GitHub Repository Secrets:**

   Go to: Repository → Settings → Secrets and variables → Actions → New repository secret

   Add these secrets:
   - **Name:** `GCP_PROJECT_ID` | **Value:** Your Google Cloud project ID
   - **Name:** `GCP_SA_KEY` | **Value:** Contents of `key.json` (entire JSON)
   - **Name:** `GCP_REGION` | **Value:** `us-central1` (or preferred region)

4. **Push to main** - deployment happens automatically!

The workflow:

1. Builds unified Docker image (frontend + backend)
2. Pushes to GitHub Container Registry
3. Deploys to Cloud Run

### Cost Information

**Google Cloud Run Free Tier:**

- 2 million requests per month
- 360,000 GB-seconds of memory
- 180,000 vCPU-seconds
- 1 GB network egress per month

For a classroom tool with moderate usage (100-500 students), this typically **stays within the free tier**.

**Estimated monthly cost:**

- Light usage (free tier): $0
- Moderate usage: $5-10/month

## GitHub Container Registry

Docker images are automatically built and published to GHCR on every push to main.

### Using Pre-built Images

Pull and run without building locally:

```bash
# Pull the image
docker pull ghcr.io/YOUR_USERNAME/ai-fun-token-wheel:main

# Run locally
docker run -p 8000:8000 ghcr.io/YOUR_USERNAME/ai-fun-token-wheel:main
```

Access at <http://localhost:8000>

## Troubleshooting

### Models not loading

First run downloads GPT-2 (~500MB). Cloud Run may timeout on first startup. If this happens, trigger another request - the model will be cached.

### Port conflicts (Local)

If port 8000 is in use, modify `docker compose.yml`:

```yaml
ports:
  - "YOUR_PORT:8000"
```

### Memory issues (Local)

PyTorch and GPT-2 require ~2GB RAM. Ensure Docker Desktop has sufficient memory:
Docker Desktop → Settings → Resources → Memory

### Cloud Run cold starts

Cloud Run scales to zero when idle. First request after idle may take 10-30 seconds. Subsequent requests are fast.

For consistent performance, set minimum instances:

```bash
gcloud run services update ai-token-wheel --min-instances=1
```

**Note:** Minimum instances may incur charges beyond the free tier.

### Viewing logs

**Local Docker logs:**

```bash
docker compose logs
docker compose logs -f app  # Follow logs in real-time
```

**Cloud Run logs:**

```bash
# View recent logs
gcloud run logs read ai-token-wheel --limit=50

# Stream logs in real-time
gcloud run logs tail ai-token-wheel
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

### Update Cloud Run service

```bash
# Re-deploy with latest code
gcloud run deploy ai-token-wheel --source .
```

Or push to GitHub and let automated deployment handle it!

### Custom Docker build

Build manually:

```bash
docker build -t ai-fun-token-wheel .
docker run -p 8000:8000 ai-fun-token-wheel
```

### Using GHCR in docker compose

Modify `docker compose.yml` to use pre-built images:

```yaml
services:
  app:
    image: ghcr.io/YOUR_USERNAME/ai-fun-token-wheel:main
    # Remove the 'build' section
```

This is faster than building locally.

## GitHub Codespaces

This project is configured for GitHub Codespaces. Click "Code" → "Codespaces" → "Create codespace" to get a pre-configured development environment in your browser.

Once created:

```bash
docker compose up --build
```

The app will be available via Codespaces' port forwarding.
