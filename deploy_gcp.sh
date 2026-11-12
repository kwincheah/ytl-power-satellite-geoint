#!/usr/bin/env bash
# Google Cloud Deployment Script (Bash)
# Deploys YTL Power Satellite GEOINT to Google Cloud Run with Cloud Scheduler automation

set -e

PROJECT_ID=${1:?"Usage: ./deploy_gcp.sh <GCP_PROJECT_ID> [REGION]"}
REGION=${2:-"asia-southeast1"}
SERVICE_NAME="ytl-geoint-service"
# Token for admin-only endpoints (pipeline run, BigQuery commit, alerts, engine switch).
# Reuses $ADMIN_TOKEN if set, otherwise generates a new one.
ADMIN_TOKEN=${ADMIN_TOKEN:-$(openssl rand -hex 24)}

echo "=========================================================="
echo " Google Cloud Platform Deployment: YTL Satellite GEOINT"
echo " Project: $PROJECT_ID | Region: $REGION"
echo "=========================================================="

# 1. Set Active GCP Project
echo "[1/5] Setting active project to $PROJECT_ID..."
gcloud config set project "$PROJECT_ID"

# 2. Enable Required GCP APIs
echo "[2/5] Enabling Cloud Run, Cloud Build, Cloud Scheduler, and Artifact Registry APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    cloudscheduler.googleapis.com \
    artifactregistry.googleapis.com \
    bigquery.googleapis.com \
    storage.googleapis.com

# 3. Create Artifact Registry repository if not present
echo "[3/5] Verifying Artifact Registry repository..."
if ! gcloud artifacts repositories describe geoint-containers --location="$REGION" &>/dev/null; then
    echo "Creating Artifact Registry repository 'geoint-containers'..."
    gcloud artifacts repositories create geoint-containers \
        --repository-format=docker \
        --location="$REGION" \
        --description="YTL GEOINT Container Images"
fi

# 4. Deploy directly from source to Cloud Run
echo "[4/5] Building and Deploying to Google Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,BIGQUERY_DATASET=traffic_analytics.ytl_satellite_telemetry,GCS_BUCKET_NAME=ytl-power-geoint-assets,ADMIN_TOKEN=$ADMIN_TOKEN"

SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --platform managed --region "$REGION" --format 'value(status.url)')
echo "[SUCCESS] Web Application Live on Cloud Run: $SERVICE_URL"

# 5. Configure Cloud Scheduler Job
echo "[5/5] Configuring Google Cloud Scheduler for Automated Sentinel-2 Updates..."
JOB_NAME="ytl-satellite-update-job"
UPDATE_URL="$SERVICE_URL/api/pipeline/update"

if gcloud scheduler jobs describe "$JOB_NAME" --location="$REGION" &>/dev/null; then
    gcloud scheduler jobs update http "$JOB_NAME" \
        --location="$REGION" \
        --schedule="0 2 * * 1" \
        --time-zone="Asia/Kuala_Lumpur" \
        --uri="$UPDATE_URL" \
        --http-method=POST \
        --update-headers="X-Admin-Token=$ADMIN_TOKEN"
else
    gcloud scheduler jobs create http "$JOB_NAME" \
        --location="$REGION" \
        --schedule="0 2 * * 1" \
        --time-zone="Asia/Kuala_Lumpur" \
        --uri="$UPDATE_URL" \
        --http-method=POST \
        --headers="X-Admin-Token=$ADMIN_TOKEN" \
        --description="Triggers Sentinel-2 pass check, CV/YOLO re-segmentation, and BigQuery sync."
fi

echo "=========================================================="
echo " Deployment Complete!"
echo " Webapp URL:       $SERVICE_URL"
echo " Cloud Scheduler:  Runs weekly (Monday 02:00 MYT)"
echo " BigQuery Table:   traffic_analytics.ytl_satellite_telemetry"
echo " Admin token:      $ADMIN_TOKEN  (keep it private; needed for admin actions)"
echo "=========================================================="
