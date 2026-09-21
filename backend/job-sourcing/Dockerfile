# Dockerfile pour le service de scraping des offres d'emploi
FROM python:3.11-slim
ARG INSTALL_PLAYWRIGHT=0

# Definition du repertoire de travail
WORKDIR /app

# Installation des dependances systeme necessaires
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copie des fichiers de dependances
COPY requirements.txt .
COPY requirements-playwright.txt .

# Installation des dependances Python
RUN pip install --no-cache-dir -r requirements.txt

# Optionnel: support JS/SPA via Playwright (Wiijob, autres sites SPA)
# Activer au build avec: --build-arg INSTALL_PLAYWRIGHT=1
RUN if [ "$INSTALL_PLAYWRIGHT" = "1" ]; then \
      pip install --no-cache-dir -r requirements-playwright.txt && \
      python -m playwright install --with-deps chromium ; \
    fi

# Copie du code source
COPY . .

# Creation des repertoires necessaires
RUN mkdir -p /app/logs /app/data/raw

# Exposition du port API
EXPOSE 8000

# Point d'entree : API FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
