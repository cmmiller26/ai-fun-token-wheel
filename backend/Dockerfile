# Stage 1: Build stage with dependencies
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Create and activate a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies, forcing CPU-only version of PyTorch
# This is the key optimization to reduce image size.
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Copy application code into the venv directory as well, for simplicity in the next stage
COPY . .


# Stage 2: Final production stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application code from the builder stage
COPY --from=builder /app .

# Activate the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Expose port
EXPOSE 8000

# Run the FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]