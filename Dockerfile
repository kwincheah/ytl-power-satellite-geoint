# Production Dockerfile for Google Cloud Run
# YTL Power (6742.KL) Satellite GEOINT Platform

FROM python:3.12-slim

# Prevent Python from writing .pyc and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    APP_HOME=/app

WORKDIR $APP_HOME

# Install essential system libraries for OpenCV and Rasterio/GDAL
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application codebase and static assets
COPY . .

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Run uvicorn on 0.0.0.0:8080
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]
