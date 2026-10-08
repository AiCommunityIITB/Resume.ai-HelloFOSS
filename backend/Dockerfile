# Use Python 3.12 slim image with specific version for reproducibility
FROM python:3.12.3-slim

# Set working directory
WORKDIR /app

# Create non-root user early with specific UID/GID for consistency
RUN groupadd -r -g 1001 myuser && useradd -r -u 1001 -g myuser myuser

# Install system dependencies including ODBC 18 and security updates
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    unzip \
    gcc \
    libssl-dev \
    libpq-dev \
    poppler-utils \
    tesseract-ocr \
    curl \
    gnupg \
    unixodbc-dev \
    ca-certificates \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg \
    && echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first and install dependencies as root
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Supply reviewed classifier assets at runtime; no private archive is downloaded.
# Copy application code
COPY . .

# Create directories for logs and uploads with proper permissions
RUN mkdir -p /app/logs /app/uploads \
    && chown -R myuser:myuser /app \
    && chmod 750 /app/logs /app/uploads

# Switch to non-root user permanently for security
USER myuser

# Expose port
EXPOSE 8000

# Health check with improved error handling
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use uvicorn to run the app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "12"]
