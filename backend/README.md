# Backend - Electricity Trading Dashboard

## Installation
```bash
# Python dependencies
pip install -r requirements.txt

# Node dependencies
npm install
```

## Configuration

Copy `.env.example` to `.env` and fill in your credentials.

## Scripts automatisés

- `fetch_rte_data.py`: Récupère les données J-1 (cron: 2h00)
- `fetch_rte_forecast.py`: Récupère les prévisions RTE (cron: 20h00)
- `our_predictions_day_ahead.py`: Génère prédictions J+1 (cron: 20h30)

## Démarrage
```bash
npm start
```