# AI Impact Analysis - Docker Image
# This image provides a zero-installation way to use the AI Impact Analysis tool

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY impactlens/ ./impactlens/
COPY config/ ./config/

# Create default config files from templates (if they don't exist)
RUN cp config/jira_report_config.yaml.example config/jira_report_config.yaml && \
    cp config/pr_report_config.yaml.example config/pr_report_config.yaml

# Install the package in editable mode to enable CLI
RUN pip install -e .

# Create reports directory
RUN mkdir -p /app/reports

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command shows help
CMD ["impactlens", "--help"]
