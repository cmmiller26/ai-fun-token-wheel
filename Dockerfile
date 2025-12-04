# ============================================================================
# Multi-stage Dockerfile for AI FUN Token Wheel
# Builds frontend and serves it from the FastAPI backend
# ============================================================================

# ----------------------------------------------------------------------------
# Stage 1: Build Frontend (React + Vite)
# ----------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install frontend dependencies
RUN npm install

# Copy frontend source code
COPY frontend/ ./

# Build the frontend for production
# We use a relative path since backend will serve at root
RUN npm run build


# ----------------------------------------------------------------------------
# Stage 2: Download Models (Platform-Independent)
# This stage downloads the model files which are the same across all platforms
# ----------------------------------------------------------------------------
FROM python:3.11-slim AS model-downloader

WORKDIR /app

# Install minimal dependencies needed for downloading models
RUN pip install --no-cache-dir transformers huggingface_hub torch --extra-index-url https://download.pytorch.org/whl/cpu

# Copy ONLY the download script (isolate from other backend changes)
COPY backend/download_models.py /tmp/download_models.py

# Download models - this layer will be cached unless download_models.py changes
RUN python /tmp/download_models.py


# ----------------------------------------------------------------------------
# Stage 3: Build Backend Dependencies (Python + PyTorch - Platform-Specific)
# ----------------------------------------------------------------------------
FROM python:3.11-slim AS backend-builder

WORKDIR /app

# Create and activate a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy backend requirements
COPY backend/requirements.txt .

# Install Python dependencies with CPU-only PyTorch to reduce image size
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu


# ----------------------------------------------------------------------------
# Stage 4: Final Production Image
# ----------------------------------------------------------------------------
FROM python:3.11-slim

WORKDIR /app

# Copy the virtual environment from backend builder (platform-specific binaries)
COPY --from=backend-builder /opt/venv /opt/venv

# Activate the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Copy backend application code
COPY backend/ /app/

# Create a non-root user before copying files that need to be owned by it
RUN useradd -m -u 1000 appuser

# Copy HuggingFace cache from model-downloader stage (platform-independent models)
COPY --from=model-downloader --chown=appuser:appuser /root/.cache/huggingface /home/appuser/.cache/huggingface

# Copy built frontend static files to a subdirectory
COPY --from=frontend-builder /frontend/dist ./static

# Ensure the entrypoint script is executable and owned by appuser
RUN chmod +x /app/run.sh && chown -R appuser:appuser /app

# Set HuggingFace cache directory to the user-owned location
# Using HF_HOME (TRANSFORMERS_CACHE is deprecated in transformers v5)
ENV HF_HOME=/home/appuser/.cache/huggingface

# Expose the port the app will run on. Cloud Run provides this via the PORT env var.
# Defaulting to 8080 for local testing.
ENV PORT=8080
# Switch to non-root user
USER appuser

# Run the application using the entrypoint script
ENTRYPOINT ["/app/run.sh"]
