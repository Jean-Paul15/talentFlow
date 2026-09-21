FROM python:3.11-slim

WORKDIR /app
ENV FASTEMBED_CACHE_PATH=/tmp/fastembed
ENV PYTHONPATH=/app

# Dependances systeme
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code source
COPY . .

# Port API
EXPOSE 8002

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Demarrage
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
