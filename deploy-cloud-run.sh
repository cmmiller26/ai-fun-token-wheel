#!/bin/bash

# Deploy AI FUN Token Wheel to Google Cloud Run
# Usage: ./deploy-cloud-run.sh YOUR_PROJECT_ID [REGION]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if project ID is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Project ID is required${NC}"
    echo "Usage: ./deploy-cloud-run.sh YOUR_PROJECT_ID [REGION]"
    exit 1
fi

PROJECT_ID=$1
REGION=${2:-us-central1}
SERVICE_NAME="ai-fun-token-wheel"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AI FUN Token Wheel - Cloud Run Deploy${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Project ID: ${YELLOW}${PROJECT_ID}${NC}"
echo -e "Region: ${YELLOW}${REGION}${NC}"
echo -e "Service: ${YELLOW}${SERVICE_NAME}${NC}"
echo ""

# Set the project
echo -e "${YELLOW}Setting Google Cloud project...${NC}"
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo -e "${YELLOW}Enabling required APIs...${NC}"
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Building and Deploying Application${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Deploy unified service
echo -e "${YELLOW}Building and deploying unified application (frontend + backend)...${NC}"
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 1 \
    --port 8000 \
    --timeout 300 \
    --quiet

# Get service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region "$REGION" \
    --format 'value(status.url)')

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}✓ Application deployed successfully!${NC}"
echo ""
echo -e "Your application is now live at:"
echo ""
echo -e "  Application (share this URL): ${YELLOW}${SERVICE_URL}${NC}"
echo -e "  API Documentation: ${YELLOW}${SERVICE_URL}/docs${NC}"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "  - Visit the application URL to test it"
echo "  - Share the URL with your students"
echo "  - Monitor logs with: gcloud run logs tail ${SERVICE_NAME}"
echo "  - View in console: https://console.cloud.google.com/run/detail/${REGION}/${SERVICE_NAME}"
echo ""
