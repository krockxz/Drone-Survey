# ===================================================================
# Multi-stage Docker build for Drone Survey Management System
# Optimized for production deployment with security and performance
# ===================================================================

# ===================================================================
# Stage 1: Frontend Build
# ===================================================================
FROM node:18-alpine AS frontend-builder

LABEL stage="frontend-builder"
LABEL maintainer="FlytBase Assignment"

# Set working directory
WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies with production optimizations
RUN npm ci --only=production --silent

# Copy frontend source
COPY frontend/ ./

# Build optimized production bundle
ENV NODE_ENV=production
RUN npm run build

# ===================================================================
# Stage 2: Backend Dependencies
# ===================================================================
FROM python:3.11-slim AS backend-deps

LABEL stage="backend-deps"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libgdal-dev \
    gdal-bin \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt ./

# Create virtual environment and install Python dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip wheel setuptools
RUN pip install --no-cache-dir -r requirements.txt

# ===================================================================
# Stage 3: Production Image
# ===================================================================
FROM python:3.11-slim AS production

LABEL maintainer="FlytBase Assignment"
LABEL version="1.0.0"
LABEL description="AI-Powered Drone Survey Management System"

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    libgdal32 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy virtual environment from deps stage
COPY --from=backend-deps /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy backend application
COPY backend/ ./backend/

# Copy built frontend assets
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist/

# Create necessary directories
RUN mkdir -p /app/logs /app/uploads /app/models /app/config

# Copy configuration files
COPY .env.production /app/.env
COPY docker-compose.yml /app/

# Set ownership to app user
RUN chown -R appuser:appuser /app

# Switch to app user
USER appuser

# Environment variables
ENV FLASK_ENV=production
ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1
ENV WORKERS=4
ENV WORKER_CLASS=eventlet
ENV WORKER_CONNECTIONS=1000
ENV TIMEOUT=120

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Expose port
EXPOSE 5000

# Start command
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--worker-class", "eventlet", \
     "--worker-connections", "1000", \
     "--timeout", "120", \
     "--keep-alive", "2", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--preload", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "backend.run:app"]

# ===================================================================
# Development Image (optional target)
# ===================================================================
FROM production AS development

LABEL stage="development"

# Switch back to root for development tools
USER root

# Install development dependencies
RUN pip install flask-debugtoolbar ipython pytest

# Development environment variables
ENV FLASK_ENV=development
ENV DEBUG=true

# Switch back to app user
USER appuser

# Development command
CMD ["python", "backend/run.py"]