#!/bin/sh
set -e

# Use the PORT environment variable if it's set, otherwise default to 8000
UVICORN_PORT=${PORT:-8000}

# Start uvicorn using exec to pass signals correctly
exec uvicorn main:app --host 0.0.0.0 --port "$UVICORN_PORT"