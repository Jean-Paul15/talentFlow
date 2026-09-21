FROM python:3.11-slim

WORKDIR /app
ENV FASTEMBED_CACHE_DIR=/opt/fastembed-cache

# Dependances systeme
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Dependances Python
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

# Code source
COPY . .

# Dossier uploads
RUN mkdir -p uploads ${FASTEMBED_CACHE_DIR}
RUN python -c "import os; from fastembed import TextEmbedding; TextEmbedding(model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', cache_dir=os.environ['FASTEMBED_CACHE_DIR'])"

# Port API
EXPOSE 8001

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Demarrage
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
