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
# Stage 2: Build Backend Dependencies (Python + PyTorch)
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
# Stage 3: Final Production Image
# ----------------------------------------------------------------------------
FROM python:3.11-slim

WORKDIR /app

# Copy the virtual environment from backend builder
COPY --from=backend-builder /opt/venv /opt/venv

# Activate the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Copy backend application code
COPY backend/ /app/

# Copy built frontend static files to a subdirectory
COPY --from=frontend-builder /frontend/dist ./static

# Create a non-root user for better security
RUN chmod +x /app/run.sh && \
    useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Expose the port the app will run on. Cloud Run provides this via the PORT env var.
# Defaulting to 8080 for local testing.
ENV PORT=8080
# Switch to non-root user
USER appuser

# Run the application using the entrypoint script
ENTRYPOINT ["/app/run.sh"]
