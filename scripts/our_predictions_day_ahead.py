import os
import requests
import pandas as pd
import numpy as np
import psycopg2
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
import pytz

# ─── Configuration du logging ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("./logs/our_predictions_day_ahead.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ─── Chargement des variables d'environnement ────────────────────────────────
load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

FASTAPI_URL = "http://localhost:8000"

# ─── 1. Récupération du contexte hybride (504h réelles + 24h RTE) ────────────
def fetch_hybrid_context():
    logger.info("Récupération du contexte hybride (504h réelles + 24h RTE)...")
    conn = psycopg2.connect(**DB_CONFIG)
    
    # 1. Récupérer les 504 dernières heures de données RÉELLES
    query_real = """
        SELECT timestamp, value
        FROM historical_data
        ORDER BY timestamp DESC
        LIMIT 504
    """
    df_real = pd.read_sql(query_real, conn)
    df_real = df_real.sort_values('timestamp').reset_index(drop=True)
    logger.info(f" {len(df_real)} heures de données RÉELLES récupérées.")
    if len(df_real) > 0:
        logger.info(f"  [REAL] Première date : {df_real['timestamp'].iloc[0]}")
        logger.info(f"  [REAL] Dernière date : {df_real['timestamp'].iloc[-1]}")
    
    # 2. Récupérer les 24 dernières heures de prévisions RTE
    query_rte = """
        SELECT timestamp, forecast_value as value
        FROM rte_forecasts
        ORDER BY timestamp DESC
        LIMIT 24
    """
    df_rte = pd.read_sql(query_rte, conn)
    conn.close()
    df_rte = df_rte.sort_values('timestamp').reset_index(drop=True)
    logger.info(f"{len(df_rte)} heures de prévisions RTE récupérées.")
    if len(df_rte) > 0:
        logger.info(f"  [RTE]  Première date : {df_rte['timestamp'].iloc[0]}")
        logger.info(f"  [RTE]  Dernière date : {df_rte['timestamp'].iloc[-1]}")
    
    # 3. Vérification chevauchement
    if len(df_real) > 0 and len(df_rte) > 0:
        last_real = pd.to_datetime(df_real['timestamp'].iloc[-1])
        first_rte = pd.to_datetime(df_rte['timestamp'].iloc[0])
        if first_rte <= last_real:
            logger.warning(f"⚠ Chevauchement détecté !")
            logger.warning(f"  Dernière donnée réelle : {last_real}")
            logger.warning(f"  Première prévision RTE : {first_rte}")
    
    # 4. Combiner les deux dataframes
    df_combined = pd.concat([df_real, df_rte], ignore_index=True)
    df_combined = df_combined.sort_values('timestamp').reset_index(drop=True)
    
    total_hours = len(df_combined)
    logger.info("═══════════════════════════════════════════════════════════")
    logger.info("  CONTEXTE FINAL")
    logger.info("═══════════════════════════════════════════════════════════")
    logger.info(f"  Total : {total_hours} heures ({len(df_real)} réelles + {len(df_rte)} RTE)")
    logger.info(f"  Première date : {df_combined['timestamp'].iloc[0]}")
    logger.info(f"  Dernière date : {df_combined['timestamp'].iloc[-1]}")
    
    if total_hours != 528:
        logger.warning(f"{total_hours} heures au lieu de 528 attendues")
    
    return df_combined


# ─── 2. Génération des timestamps pour J+1 ───────────────────────────────────
def generate_j1_timestamps(last_timestamp):
    paris_tz = pytz.timezone('Europe/Paris')
    
    if isinstance(last_timestamp, str):
        last_dt = pd.to_datetime(last_timestamp)
    else:
        last_dt = last_timestamp
    
    if last_dt.tzinfo is None:
        last_dt = paris_tz.localize(last_dt)
    else:
        last_dt = last_dt.astimezone(paris_tz)
    
    current_date = last_dt.date()
    next_date = current_date + timedelta(days=1)
    midnight = datetime.combine(next_date, datetime.min.time())
    first_j1_dt = paris_tz.localize(midnight)
    
    logger.info(f"  Date cible J+1 : {next_date}")
    logger.info(f"  Premier timestamp : {first_j1_dt}")
    
    future_timestamps = [first_j1_dt + timedelta(hours=i) for i in range(24)]
    
    logger.info(f"  Premier timestamp prédit : {future_timestamps[0]}")
    logger.info(f"  Dernier timestamp prédit : {future_timestamps[-1]}")
    
    return future_timestamps


# ─── 3. Appel à l'API FastAPI pour la prédiction ─────────────────────────────
def call_fastapi(context_values):
    
    logger.info(f"Appel à l'API FastAPI ({FASTAPI_URL}/predict)...")
    
    # Vérifier que l'API est disponible
    try:
        health = requests.get(f"{FASTAPI_URL}/health", timeout=5)
        health_data = health.json()
        if not health_data.get("model_loaded"):
            raise Exception("Le modèle n'est pas chargé dans FastAPI !")
        logger.info("FastAPI est disponible et le modèle est chargé.")
    except requests.exceptions.ConnectionError:
        raise Exception(f"Impossible de contacter FastAPI sur {FASTAPI_URL}. Est-ce que start_api.sh est lancé ?")
    
    # Envoyer la requête de prédiction
    payload = {
        "context": context_values.tolist(),
        "prediction_length": 24,
        "num_samples": 50
    }
    
    response = requests.post(
        f"{FASTAPI_URL}/predict",
        json=payload,
        timeout=120  # 2 minutes max pour la prédiction
    )
    
    if response.status_code != 200:
        raise Exception(f"Erreur FastAPI : {response.status_code} - {response.text}")
    
    result = response.json()
    predictions = result["predictions"]
    
    logger.info(f"  Prédiction reçue : {len(predictions)} valeurs")
    logger.info(f"  Moyenne : {result['mean']:.2f} MW")
    logger.info(f"  Min : {result['min']:.2f} MW | Max : {result['max']:.2f} MW")
    
    return np.array(predictions)


# ─── 4. Préparation des données pour insertion ───────────────────────────────
def prepare_predictions(timestamps, values):
    logger.info("Préparation des prédictions pour insertion...")
    predictions = []
    for i, (ts, pred_val) in enumerate(zip(timestamps, values)):
        predictions.append({
            "timestamp": ts.isoformat(),
            "predicted_value": round(float(pred_val), 2),
            "horizon": f"H+{i+1}",
            "model_name": "chronos-fine-tuned-j1"
        })
    logger.info(f"{len(predictions)} prédictions J+1 préparées.")
    return predictions


# ─── 5. Insertion dans PostgreSQL ────────────────────────────────────────────
def insert_predictions(predictions):
    logger.info("Insertion des prédictions dans PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    inserted = 0
    
    logger.info("  Vérification des 3 premiers timestamps à insérer :")
    for i in range(min(3, len(predictions))):
        logger.info(f"    {predictions[i]['timestamp']} → {predictions[i]['predicted_value']:.2f} MW")
    
    for pred in predictions:
        try:
            ts = pd.to_datetime(pred["timestamp"])
            cursor.execute("""
                INSERT INTO predictions (timestamp, predicted_value, model_name, horizon)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (timestamp, model_name) 
                DO UPDATE SET 
                    predicted_value = EXCLUDED.predicted_value,
                    horizon = EXCLUDED.horizon
            """, (ts, pred["predicted_value"], pred["model_name"], pred["horizon"]))
            if cursor.rowcount > 0:
                inserted += 1
        except Exception as e:
            logger.error(f"Erreur insertion de {pred['timestamp']}: {e}")
            conn.rollback()
    
    conn.commit()
    cursor.close()
    conn.close()
    logger.info(f"{inserted} lignes insérées/mises à jour.")


# ─── 6. Fonction principale ───────────────────────────────────────────────────
def main():
    print("\n\n\n")
    logger.info("═══════════════════════════════════════════════════════════")
    logger.info("  Prédiction J+1 via FastAPI (504h réelles + 24h RTE)")
    logger.info("═══════════════════════════════════════════════════════════")
    
    try:
        # Étape 1 : Récupérer le contexte hybride
        df_context = fetch_hybrid_context()
        
        # Étape 2 : Appeler FastAPI pour la prédiction
        predicted_values = call_fastapi(df_context["value"].values)
        
        # Étape 3 : Générer les timestamps J+1
        future_timestamps = generate_j1_timestamps(df_context['timestamp'].iloc[-1])
        
        # Étape 4 : Préparer les données
        predictions = prepare_predictions(future_timestamps, predicted_values)
        
        # Aperçu
        logger.info("═══════════════════════════════════════════════════════════")
        logger.info("  APERÇU DES PRÉDICTIONS J+1")
        logger.info("═══════════════════════════════════════════════════════════")
        for pred in predictions[:5]:
            logger.info(f"  {pred['timestamp']} → {pred['predicted_value']:,.2f} MW")
        logger.info("  ...")
        for pred in predictions[-2:]:
            logger.info(f"  {pred['timestamp']} → {pred['predicted_value']:,.2f} MW")
        
        # Étape 5 : Insérer dans la base
        insert_predictions(predictions)
        
        logger.info("═══════════════════════════════════════════════════════════")
        logger.info(" Prédictions J+1 terminées avec succès via FastAPI")
        logger.info("═══════════════════════════════════════════════════════════")
        
    except Exception as e:
        logger.error(f"Erreur critique : {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
