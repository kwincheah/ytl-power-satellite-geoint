# Google Cloud Deployment Script (PowerShell)
# Deploys YTL Power Satellite GEOINT to Google Cloud Run with Cloud Scheduler automation

param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [string]$Region = "asia-southeast1",
    [string]$ServiceName = "ytl-geoint-service"
)

# Token for admin-only endpoints (pipeline run, BigQuery commit, alerts, engine switch).
# Reuses $env:ADMIN_TOKEN if set, otherwise generates a new one.
$AdminToken = $env:ADMIN_TOKEN
if (-not $AdminToken) {
    $bytes = New-Object byte[] 24
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $AdminToken = -join ($bytes | ForEach-Object { $_.ToString("x2") })
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Google Cloud Platform Deployment: YTL Satellite GEOINT" -ForegroundColor Cyan
Write-Host " Project: $ProjectId | Region: $Region" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Set Active GCP Project
Write-Host "`n[1/5] Setting active project to $ProjectId..." -ForegroundColor Yellow
gcloud.cmd config set project $ProjectId

# 2. Enable Required GCP APIs
Write-Host "`n[2/5] Enabling Cloud Run, Cloud Build, Cloud Scheduler, and Artifact Registry APIs..." -ForegroundColor Yellow
gcloud.cmd services enable `
    run.googleapis.com `
    cloudbuild.googleapis.com `
    cloudscheduler.googleapis.com `
    artifactregistry.googleapis.com `
    bigquery.googleapis.com `
    storage.googleapis.com

# 3. Create Artifact Registry repository (if it doesn't already exist)
Write-Host "`n[3/5] Verifying Artifact Registry repository..." -ForegroundColor Yellow
gcloud.cmd artifacts repositories describe geoint-containers --location=$Region 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating Artifact Registry repository 'geoint-containers'..."
    gcloud.cmd artifacts repositories create geoint-containers `
        --repository-format=docker `
        --location=$Region `
        --description="YTL GEOINT Container Images"
}

# 4. Deploy directly from source to Cloud Run
Write-Host "`n[4/5] Building and Deploying to Google Cloud Run..." -ForegroundColor Yellow
gcloud.cmd run deploy $ServiceName `
    --source . `
    --region $Region `
    --platform managed `
    --allow-unauthenticated `
    --memory 1Gi `
    --cpu 1 `
    --set-env-vars "GCP_PROJECT_ID=$ProjectId,BIGQUERY_DATASET=traffic_analytics.ytl_satellite_telemetry,GCS_BUCKET_NAME=ytl-power-geoint-assets,ADMIN_TOKEN=$AdminToken"

# Fetch deployed service URL
$ServiceUrl = (gcloud.cmd run services describe $ServiceName --platform managed --region $Region --format 'value(status.url)').Trim()
Write-Host "`n[SUCCESS] Web Application Live on Cloud Run: $ServiceUrl" -ForegroundColor Green

# 5. Create / Update Google Cloud Scheduler Job for Automated Updating
Write-Host "`n[5/5] Configuring Google Cloud Scheduler for Automated Sentinel-2 Updates..." -ForegroundColor Yellow
$JobName = "ytl-satellite-update-job"
$UpdateUrl = "$ServiceUrl/api/pipeline/update"

gcloud.cmd scheduler jobs describe $JobName --location=$Region 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Updating existing Cloud Scheduler job $JobName..."
    gcloud.cmd scheduler jobs update http $JobName `
        --location=$Region `
        --schedule="0 2 * * 1" `
        --time-zone="Asia/Kuala_Lumpur" `
        --uri=$UpdateUrl `
        --http-method=POST `
        --update-headers="X-Admin-Token=$AdminToken"
} else {
    Write-Host "Creating new Cloud Scheduler job $JobName (Runs every Monday 02:00 MYT)..."
    gcloud.cmd scheduler jobs create http $JobName `
        --location=$Region `
        --schedule="0 2 * * 1" `
        --time-zone="Asia/Kuala_Lumpur" `
        --uri=$UpdateUrl `
        --http-method=POST `
        --headers="X-Admin-Token=$AdminToken" `
        --description="Triggers Sentinel-2 pass check, CV/YOLO re-segmentation, and BigQuery sync."
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host " Deployment Complete!" -ForegroundColor Green
Write-Host " Webapp URL:       $ServiceUrl" -ForegroundColor Green
Write-Host " Cloud Scheduler:  Runs weekly to update telemetry" -ForegroundColor Green
Write-Host " BigQuery Table:   traffic_analytics.ytl_satellite_telemetry" -ForegroundColor Green
Write-Host " Admin token:      $AdminToken  (keep it private; needed for admin actions)" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
