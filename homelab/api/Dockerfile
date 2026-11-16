FROM python:3.12-slim

# Prevent Python from writing pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app

# Copy application source, migrations, and entrypoint
COPY --chown=appuser:appuser ./app /app/app
COPY --chown=appuser:appuser ./migrations /app/migrations
COPY --chown=appuser:appuser ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
