#!/bin/bash
# Script de lancement de l'application Streamlit
# Usage: ./run_streamlit.sh

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "🚀 Démarrage de TalentFlow Dashboard..."
echo ""

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 non trouvé"
    exit 1
fi

# Installer les dépendances si nécessaire
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activer l'environnement
source venv/bin/activate

# Installer les packages
echo "📥 Installation des dépendances..."
pip install -q streamlit plotly pandas elasticsearch redis minio python-dotenv loguru requests

# Charger les variables d'environnement
if [ -f ".env" ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

# Démarrer Streamlit
echo "✅ Démarrage du dashboard..."
echo ""
echo "📊 Dashboard disponible sur: http://localhost:8501"
echo ""

streamlit run app_streamlit.py --logger.level=info
