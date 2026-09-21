# Dockerfile pour le service de nettoyage
FROM python:3.11-slim

WORKDIR /app

# Dependencies systeme
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Dependencies Python - torch CPU d'abord (version legere sans CUDA)
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1000 \
    --index-url https://download.pytorch.org/whl/cpu \
    "torch>=2.1.0,<3.0.0" \
    && pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

# Code source
COPY . .

# Repertoire logs
RUN mkdir -p logs

# Exposition du port API
EXPOSE 8000

# Point d'entree : API FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
