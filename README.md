# ⚡ Electricity Consumption Dashboard

English version below

---


> Ce projet est né d'une conviction simple : pour trader efficacement sur le marché de l'électricité, il faut anticiper. La consommation électrique influence directement le prix spot de l'énergie — comprendre et prévoir sa trajectoire, c'est se donner un avantage décisif.
>
> Ce dashboard a été conçu pour centraliser, visualiser et prédire la consommation électrique française en temps quasi réel. Il combine des données officielles de RTE France avec un modèle de prévision de pointe (Chronos, développé par Amazon Research), fine-tuné spécifiquement sur les données de consommation française.
>
> Le résultat : un outil autonome, entièrement automatisé, capable de générer chaque jour des prévisions J+1 et de les comparer aux prévisions officielles de RTE — le tout accessible depuis un dashboard interactif.

### 🎯 Présentation

Le dashboard affiche et compare en temps réel :
- **La consommation réelle** issue de l'API RTE France (mise à jour quotidienne à 2h du matin)
- **Les prévisions officielles RTE** pour le jour J (mises à jour quotidiennement à 20h)
- **Nos prévisions** générées par le modèle de fondation Chronos fine-tuné via FastAPI (mises à jour quotidiennement à 10h)

### 🏗️ Architecture du projet
```
electricity_project/
│
├── backend/                        # API REST Express.js
│   ├── node_modules/
│   ├── index.js                    # Serveur principal (6 routes)
│   ├── package.json
│   └── .gitignore
│
├── frontend/                       # Dashboard React.js
│   ├── node_modules/
│   ├── public/
│   ├── src/
│   │   ├── components/             # Composants shadcn/ui
│   │   ├── lib/                    # Fonctions utilitaires
│   │   ├── assets/
│   │   ├── curves.tsx              # Composant graphique principal
│   │   ├── App.tsx                 # Composant racine
│   │   ├── App.css
│   │   ├── main.tsx                # Point d'entrée
│   │   └── index.css
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── scripts/                        # Scripts Python d'automatisation
│   ├── fetch_rte_data.py           # Récupère la conso réelle (cron : 2h du matin)
│   ├── fetch_rte_forecast.py       # Récupère les prévisions RTE jour J (cron : 20h)
│   ├── our_predictions_day_ahead.py # Génère nos prévisions via FastAPI (cron : 10h)
│   ├── predict_api.py              # Serveur FastAPI exposant le modèle Chronos
│   └── start_api.sh                # Démarre/redémarre le serveur FastAPI
│
├── models/                         # Modèle Chronos fine-tuné (Git LFS)
│   └── run-0/                      # Poids et configuration du modèle
│
├── .env.example                    # Template des variables d'environnement
├── .gitignore
├── requirements.txt                # Dépendances Python
└── README.md
```

### 🔄 Flux de données
```
API RTE France
      │
      ▼
fetch_rte_data.py (2h)              ──► PostgreSQL (historical_data)
fetch_rte_forecast.py (20h)         ──► PostgreSQL (rte_forecasts)
      │
      ▼
our_predictions_day_ahead.py (10h)
      │
      ├── lit historical_data depuis PostgreSQL (504h)
      ├── lit rte_forecasts depuis PostgreSQL (24h)
      ├── POST http://localhost:8000/predict → FastAPI (predict_api.py)
      │         │
      │         └── Modèle Chronos chargé en mémoire
      └── écrit les 24 prévisions dans PostgreSQL (predictions)
            │
            ▼
      API Express.js (port 3001)
            │
            ▼
      Dashboard React (port 5173)
```

### 🖥️ Aperçu du Dashboard
```
┌─────────────────────────────────────────────────────────┐
│  ⚡ Electricity Consumption Dashboard          [🌙/☀️]  │
├─────────────────────────────────────────────────────────┤
│  France — Actual vs RTE Forecasts vs Our Forecasts      │
│                                        [Last 3 months ▼]│
│                                                         │
│  80k ┤                                                  │
│      │  ━━━━━━  Consommation réelle                     │
│  60k ┤  ──────  Prévisions RTE                          │
│      │  ──────  Nos prévisions (Chronos)                │
│  40k ┤                                                  │
│      └──────────────────────────────────────────────    │
│      01 Déc       01 Jan        01 Fév                  │
│                                                         │
│  La conso réelle du jour D est disponible le D+1 à 2h   │
│  Les prévisions RTE pour J sont générées à 20h          │
│  Nos prévisions pour J+1 sont générées à 10h            │
│                                                         │
│  © Données issues de l'API RTE France                   │
└─────────────────────────────────────────────────────────┘
```

### 🛠️ Stack technique

| Couche | Technologie | Version |
|--------|-------------|---------|
| Frontend | React.js | 19.x |
| Frontend | Vite | 7.x |
| Frontend | Recharts | 2.x |
| Frontend | shadcn/ui + Tailwind CSS | 4.x |
| Backend API | Express.js | 5.x |
| Backend API | Node.js + pg | 8.x |
| Modèle ML | Chronos (Amazon, fine-tuné) | - |
| API Modèle | FastAPI + Uvicorn | 0.129.x |
| Base de données | PostgreSQL (Docker) | 15 |
| Source de données | API RTE France (OAuth2) | - |
| Automatisation | Cron jobs | - |

### ⚙️ Installation & Configuration

#### Prérequis
- Node.js >= 18
- Python >= 3.10
- Docker

#### 1. Cloner le dépôt
```bash
git clone https://github.com/adecholaA1/electricity_consumption_dashbord.git
cd electricity_consumption_dashbord
```

#### 2. Configurer les variables d'environnement
```bash
cp .env.example .env
# Remplir .env avec vos identifiants API RTE et les paramètres PostgreSQL
```

#### 3. Démarrer la base de données
```bash
docker run --name trading_pg_db \
  -e POSTGRES_DB=trading_data \
  -e POSTGRES_USER=dev_user \
  -e POSTGRES_PASSWORD=your_password \
  -v pg_data:/var/lib/postgresql/data \
  -p 5432:5432 \
  -d postgres:15-alpine
```

#### 4. Installer les dépendances Python
```bash
pip install -r requirements.txt
```

#### 5. Donner les permissions d'exécution au script FastAPI
```bash
chmod +x scripts/start_api.sh
```

#### 6. Démarrer l'API du modèle ML
```bash
bash scripts/start_api.sh
```

#### 7. Démarrer le backend
```bash
cd backend
npm install
node index.js
```

#### 8. Démarrer le frontend
```bash
cd frontend
npm install
npm run dev
```

#### 9. Configurer les cron jobs
```bash
crontab -e
```
Ajouter les lignes suivantes :
```bash
# Démarrer FastAPI au démarrage du système
@reboot /bin/bash /chemin/vers/electricity_project/scripts/start_api.sh >> /chemin/vers/electricity_project/logs/fastapi.log 2>&1

# Récupérer les données historiques RTE de J-1 tous les J à 02h00
0 2 * * * cd /chemin/vers/electricity_project && /opt/anaconda3/envs/electricity_env/bin/python scripts/fetch_rte_data.py >> /chemin/vers/electricity_project/logs/fetch_rte_data.log 2>&1

# Redémarrer FastAPI à 9h50 (kill ancien + démarrage nouveau)
50 9 * * * /bin/bash /chemin/vers/electricity_project/scripts/start_api.sh >> /chemin/vers/electricity_project/logs/fastapi.log 2>&1

# Générer nos prédictions tous les jours à 10h
0 10 * * * cd /chemin/vers/electricity_project && /opt/anaconda3/envs/electricity_env/bin/python scripts/our_predictions_day_ahead.py >> /chemin/vers/electricity_project/logs/our_predictions_day_ahead.log 2>&1

# Récupérer les prévisions RTE jour J tous les jours à 20h
0 20 * * * cd /chemin/vers/electricity_project && /opt/anaconda3/envs/electricity_env/bin/python scripts/fetch_rte_forecast.py >> /chemin/vers/electricity_project/logs/fetch_rte_forecast.log 2>&1
```

> ⚠️ **Important (macOS)** : Pour que les cron jobs fonctionnent correctement sur macOS, il faut donner l'accès complet au disque à cron :
> 1. Ouvrir **Préférences Système** → **Confidentialité & Sécurité** → **Accès complet au disque**
> 2. Cliquer sur **+** et ajouter `/usr/sbin/cron`

### 🐍 Dépendances Python

| Package | Version | Usage |
|---------|---------|-------|
| torch | 2.2.2 | Backend deep learning |
| chronos-forecasting | latest | Modèle de fondation |
| transformers | 4.57.6 | Architecture du modèle |
| accelerate | 1.12.0 | Accélération entraînement |
| fastapi | 0.129.0 | API du modèle ML |
| uvicorn | 0.40.0 | Serveur ASGI |
| pandas | 2.3.3 | Manipulation des données |
| numpy | 1.26.4 | Calcul numérique |
| psycopg2-binary | 2.9.11 | Connexion PostgreSQL |
| scikit-learn | 1.7.2 | Utilitaires ML |
| requests | 2.32.5 | Appels API RTE |
| python-dotenv | 1.2.1 | Variables d'environnement |
| tqdm | 4.67.3 | Barres de progression |

### 📡 Endpoints API

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/api/data` | Données combinées (3 séries) |
| GET | `/api/data/real` | Consommation réelle uniquement |
| GET | `/api/data/predictions` | Nos prévisions |
| GET | `/api/data/rte-forecasts` | Prévisions officielles RTE |
| GET | `/api/status` | Statut du système |
| GET | `/api/health` | Santé de l'API |

### 🤖 Pipeline automatisé (Cron Jobs)

| Script | Planification | Description |
|--------|--------------|-------------|
| `start_api.sh` | Au démarrage + chaque jour à 9h50 | Redémarre FastAPI |
| `fetch_rte_data.py` | Chaque jour à 2h | Récupère la consommation réelle du jour D |
| `our_predictions_day_ahead.py` | Chaque jour à 10h | Génère nos prévisions via FastAPI |
| `fetch_rte_forecast.py` | Chaque jour à 20h | Récupère les prévisions RTE du jour J |

### 📄 Licence

Licence MIT — libre d'utilisation, de modification et de distribution.

### 🙏 Sources de données

- Données de consommation électrique : [API RTE France](https://data.rte-france.com)
- Modèle de prévision : [Chronos by Amazon](https://github.com/amazon-science/chronos-forecasting)

---


> This project was born from a simple conviction: to trade electricity markets effectively, you need to anticipate. Electricity consumption directly influences the spot price of energy — understanding and forecasting its trajectory is a decisive advantage.
>
> This dashboard was designed to centralize, visualize and forecast French electricity consumption in near real time. It combines official RTE France data with a state-of-the-art forecasting model (Chronos, developed by Amazon Research), fine-tuned specifically on French consumption data.
>
> The result: a fully autonomous, automated tool capable of generating daily J+1 forecasts and comparing them against RTE's official forecasts — all accessible from an interactive dashboard.

### 🎯 Overview

The dashboard displays and compares in real time:
- **Actual consumption** data from RTE France (updated daily at 2 a.m.)
- **RTE official forecasts** for day J (updated daily at 8 p.m.)
- **Our model forecasts** generated by a fine-tuned Chronos model via FastAPI (updated daily at 10 a.m.)

### 🏗️ Project Architecture
```
electricity_project/
│
├── backend/                        # Express.js REST API
│   ├── node_modules/
│   ├── index.js                    # Main API server (6 routes)
│   ├── package.json
│   └── .gitignore
│
├── frontend/                       # React.js dashboard
│   ├── node_modules/
│   ├── public/
│   ├── src/
│   │   ├── components/             # shadcn/ui components
│   │   ├── lib/                    # Utility functions
│   │   ├── assets/
│   │   ├── curves.tsx              # Main chart component
│   │   ├── App.tsx                 # Root component
│   │   ├── App.css
│   │   ├── main.tsx                # Entry point
│   │   └── index.css
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── scripts/                        # Python automation scripts
│   ├── fetch_rte_data.py           # Fetches actual consumption (cron: daily at 2 a.m.)
│   ├── fetch_rte_forecast.py       # Fetches RTE forecasts day J (cron: daily at 8 p.m.)
│   ├── our_predictions_day_ahead.py # Generates our forecasts via FastAPI (cron: 10 a.m.)
│   ├── predict_api.py              # FastAPI server exposing the Chronos model
│   └── start_api.sh                # Starts/restarts the FastAPI server
│
├── models/                         # Fine-tuned Chronos model (Git LFS)
│   └── run-0/                      # Model weights and config
│
├── .env.example                    # Environment variables template
├── .gitignore
├── requirements.txt                # Python dependencies
└── README.md
```

### 🔄 Data Flow
```
RTE France API
      │
      ▼
fetch_rte_data.py (2 a.m.)          ──► PostgreSQL (historical_data)
fetch_rte_forecast.py (8 p.m.)      ──► PostgreSQL (rte_forecasts)
      │
      ▼
our_predictions_day_ahead.py (10 a.m.)
      │
      ├── reads historical_data from PostgreSQL (504h)
      ├── reads rte_forecasts from PostgreSQL (24h)
      ├── POST http://localhost:8000/predict → FastAPI (predict_api.py)
      │         │
      │         └── Chronos model loaded in memory
      └── writes 24 predictions to PostgreSQL (predictions)
            │
            ▼
      Express.js API (port 3001)
            │
            ▼
      React Dashboard (port 5173)
```

### 🖥️ Dashboard Preview
```
┌─────────────────────────────────────────────────────────┐
│  ⚡ Electricity Consumption Dashboard          [🌙/☀️]  │
├─────────────────────────────────────────────────────────┤
│  France — Actual vs RTE Forecasts vs Our Forecasts      │
│                                        [Last 3 months ▼]│
│                                                         │
│  80k ┤                                                  │
│      │  ━━━━━━  Actual Consumption                      │
│  60k ┤  ──────  RTE Forecast                            │
│      │  ──────  Our Forecast (Chronos)                  │
│  40k ┤                                                  │
│      └──────────────────────────────────────────────    │
│      Dec 01        Jan 01        Feb 01                 │
│                                                         │
│  Actual consumption for day D is available on D+1 at 2am│
│  RTE forecasts for day J are generated at 8pm           │
│  Our forecasts for J+1 are generated at 10am            │
│                                                         │
│  © Actual consumption and RTE forecasts from RTE France │
└─────────────────────────────────────────────────────────┘
```

### 🛠️ Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | React.js | 19.x |
| Frontend | Vite | 7.x |
| Frontend | Recharts | 2.x |
| Frontend | shadcn/ui + Tailwind CSS | 4.x |
| Backend API | Express.js | 5.x |
| Backend API | Node.js + pg | 8.x |
| ML Model | Chronos (Amazon, fine-tuned) | - |
| Model API | FastAPI + Uvicorn | 0.129.x |
| Database | PostgreSQL (Docker) | 15 |
| Data Source | RTE France API (OAuth2) | - |
| Automation | Cron jobs | - |

### ⚙️ Installation & Setup

#### Prerequisites
- Node.js >= 18
- Python >= 3.10
- Docker

#### 1. Clone the repository
```bash
git clone https://github.com/adecholaA1/electricity_consumption_dashbord.git
cd electricity_consumption_dashbord
```

#### 2. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your RTE API credentials and PostgreSQL settings
```

#### 3. Start the database
```bash
docker run --name trading_pg_db \
  -e POSTGRES_DB=trading_data \
  -e POSTGRES_USER=dev_user \
  -e POSTGRES_PASSWORD=your_password \
  -v pg_data:/var/lib/postgresql/data \
  -p 5432:5432 \
  -d postgres:15-alpine
```

#### 4. Install Python dependencies
```bash
pip install -r requirements.txt
```

#### 5. Give execution permissions to the FastAPI script
```bash
chmod +x scripts/start_api.sh
```

#### 6. Start the ML model API
```bash
bash scripts/start_api.sh
```

#### 7. Start the backend
```bash
cd backend
npm install
node index.js
```

#### 8. Start the frontend
```bash
cd frontend
npm install
npm run dev
```

#### 9. Configure cron jobs
```bash
crontab -e
```
Add the following lines:
```bash
# Start FastAPI on system boot
@reboot /bin/bash /path/to/electricity_project/scripts/start_api.sh >> /path/to/electricity_project/logs/fastapi.log 2>&1

# Fetch actual RTE consumption daily at 2 a.m.
0 2 * * * cd /path/to/electricity_project && /opt/anaconda3/envs/electricity_env/bin/python scripts/fetch_rte_data.py >> /path/to/electricity_project/logs/fetch_rte_data.log 2>&1

# Restart FastAPI at 9:50 a.m. (kill old + start new)
50 9 * * * /bin/bash /path/to/electricity_project/scripts/start_api.sh >> /path/to/electricity_project/logs/fastapi.log 2>&1

# Generate our predictions daily at 10 a.m.
0 10 * * * cd /path/to/electricity_project && /opt/anaconda3/envs/electricity_env/bin/python scripts/our_predictions_day_ahead.py >> /path/to/electricity_project/logs/our_predictions_day_ahead.log 2>&1

# Fetch RTE forecasts for day J daily at 8 p.m.
0 20 * * * cd /path/to/electricity_project && /opt/anaconda3/envs/electricity_env/bin/python scripts/fetch_rte_forecast.py >> /path/to/electricity_project/logs/fetch_rte_forecast.log 2>&1
```

> ⚠️ **Important (macOS)** : For cron jobs to work correctly on macOS, you need to grant Full Disk Access to cron:
> 1. Open **System Preferences** → **Privacy & Security** → **Full Disk Access**
> 2. Click **+** and add `/usr/sbin/cron`

### 🐍 Python Dependencies

| Package | Version | Usage |
|---------|---------|-------|
| torch | 2.2.2 | Deep learning backend |
| chronos-forecasting | latest | Foundation model |
| transformers | 4.57.6 | Model architecture |
| accelerate | 1.12.0 | Training acceleration |
| fastapi | 0.129.0 | ML model API |
| uvicorn | 0.40.0 | ASGI server |
| pandas | 2.3.3 | Data manipulation |
| numpy | 1.26.4 | Numerical computing |
| psycopg2-binary | 2.9.11 | PostgreSQL connection |
| scikit-learn | 1.7.2 | ML utilities |
| requests | 2.32.5 | RTE API calls |
| python-dotenv | 1.2.1 | Environment variables |
| tqdm | 4.67.3 | Progress bars |

### 📡 API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/data` | Combined data (all 3 series) |
| GET | `/api/data/real` | Actual consumption only |
| GET | `/api/data/predictions` | Our model predictions |
| GET | `/api/data/rte-forecasts` | RTE official forecasts |
| GET | `/api/status` | System status & counts |
| GET | `/api/health` | API health check |

### 🤖 Automated Pipeline (Cron Jobs)

| Script | Schedule | Description |
|--------|----------|-------------|
| `start_api.sh` | On boot + daily at 9:50 a.m. | Restarts FastAPI |
| `fetch_rte_data.py` | Daily at 2 a.m. | Fetches actual consumption for day D |
| `our_predictions_day_ahead.py` | Daily at 10 a.m. | Generates our forecasts via FastAPI |
| `fetch_rte_forecast.py` | Daily at 8 p.m. | Fetches RTE forecasts for day J |

### 📄 License

MIT License — feel free to use, modify and distribute.

### 🙏 Data Sources

- Electricity consumption data: [RTE France API](https://data.rte-france.com)
- Forecasting model: [Chronos by Amazon](https://github.com/amazon-science/chronos-forecasting)
