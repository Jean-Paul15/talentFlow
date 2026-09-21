# Dockerfile pour le dashboard Streamlit
FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier les requirements
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

# Copier l'application (architecture modulaire)
COPY app_streamlit.py .
COPY config.py .
COPY constants.py .
COPY utils.py .
COPY services/ ./services/
COPY views/ ./views/

# Configuration Streamlit
RUN mkdir -p ~/.streamlit && \
    printf '[client]\nshowSidebarNavigation = false\n\n[server]\nheadless = true\nport = 8501\nenableXsrfProtection = false\nallowRunOnSave = true\n\n[logger]\nlevel = "info"\n' > ~/.streamlit/config.toml

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Point d'entrée
EXPOSE 8501

CMD ["streamlit", "run", "app_streamlit.py", "--logger.level=info"]
