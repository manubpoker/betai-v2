FROM python:3.11-slim

WORKDIR /app

# Install minimal system dependencies first
RUN apt-get update && apt-get install -y \
    gcc \
    wget \
    gnupg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install Python deps
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Use Playwright's official install-deps command (installs ALL system deps)
# Then install the chromium browser
RUN playwright install-deps chromium && playwright install chromium

# Copy backend code
COPY backend/ ./

# Set default port
ENV PORT=8080

# Expose port
EXPOSE 8080

# Run with gunicorn - use shell form to expand $PORT
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT} --workers 1 --timeout 300"]
# Trigger rebuild
