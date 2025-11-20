#!/bin/sh
set -e

# Default to port 8080 if PORT is not set
PORT=${PORT:-8080}

# Start the uvicorn server
exec uvicorn main:app --host 0.0.0.0 --port "$PORT"