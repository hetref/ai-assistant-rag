# Use Python 3.11 slim image for better performance and smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PATH="/app/venv/bin:$PATH"

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /app/venv

# Activate virtual environment and upgrade pip
RUN pip install --upgrade pip

# Copy requirements files first for better Docker layer caching
COPY requirements.txt .
COPY ui/requirements.txt ui/requirements.txt

# Install Python dependencies in virtual environment
RUN pip install -r requirements.txt && \
    pip install -r ui/requirements.txt

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p data/businesses && \
    mkdir -p Cache && \
    chmod -R 755 data Cache

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Expose ports
EXPOSE 8000 8001 8501

# Default command - runs the main application
CMD ["python", "app.py"]
