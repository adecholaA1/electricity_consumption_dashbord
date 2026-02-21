#!/bin/bash

# Activer l'environnement
source /home/ubuntu/electricity_consumption_dashbord/venv/bin/activate

# Tuer l'ancien processus FastAPI s'il existe
echo "Arrêt de l'ancien processus FastAPI (port 8000)..."
pkill -f "uvicorn scripts.predict_api:app" && echo " Ancien processus arrêté." || echo "Aucun processus existant."

# Attendre 2 secondes pour libérer le port
sleep 2

# Démarrer FastAPI
echo "Démarrage de FastAPI..."
cd /home/ubuntu/electricity_consumption_dashbord
uvicorn scripts.predict_api:app --host 0.0.0.0 --port 8000
