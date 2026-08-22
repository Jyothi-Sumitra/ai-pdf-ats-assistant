#!/usr/bin/env bash
set -euo pipefail

if [ -z "${PROJECT_ID:-}" ]; then
  echo "Please set PROJECT_ID environment variable (your GCP project id)."
  exit 1
fi

IMAGE=gcr.io/${PROJECT_ID}/ai-pdf-assistant:latest

echo "Building and submitting to Cloud Build: $IMAGE"
gcloud builds submit --tag "$IMAGE"

echo "Deploying to Cloud Run"
gcloud run deploy ai-pdf-assistant \
  --image "$IMAGE" \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --project "$PROJECT_ID" \
  --set-env-vars "GROQ_API_KEY=${GROQ_API_KEY}","GOOGLE_API_KEY=${GOOGLE_API_KEY}","TAVILY_API_KEY=${TAVILY_API_KEY}"

echo "Deployed. Use 'gcloud run services describe ai-pdf-assistant --platform managed --region us-central1 --project $PROJECT_ID' to get the URL."
