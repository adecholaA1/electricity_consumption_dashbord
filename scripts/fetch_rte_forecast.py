import os
import requests
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timedelta
import logging

# ─── Configuration du logging ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("./logs/fetch_forecast.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ─── Chargement des variables d'environnement ────────────────────────────────
load_dotenv()

RTE_CLIENT_ID     = os.getenv("RTE_CLIENT_ID")
RTE_CLIENT_SECRET = os.getenv("RTE_CLIENT_SECRET")
DB_HOST           = os.getenv("DB_HOST")
DB_PORT           = os.getenv("DB_PORT")
DB_NAME           = os.getenv("DB_NAME")
DB_USER           = os.getenv("DB_USER")
DB_PASSWORD       = os.getenv("DB_PASSWORD")

BASE_URL = "https://digital.iservices.rte-france.com/open_api/consumption/v1/short_term"


# ─── 1. Authentification OAuth2 RTE ──────────────────────────────────────────
def get_rte_token():
    logger.info("Authentification auprès de l'API RTE...")
    url_token = "https://digital.iservices.rte-france.com/token/oauth/"
    response  = requests.post(
        url_token,
        data={"grant_type": "client_credentials"},
        auth=(RTE_CLIENT_ID, RTE_CLIENT_SECRET)
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    logger.info("Token RTE obtenu avec succès.")
    return token


# ─── 2. Récupération des prévisions RTE D-1 ──────────────────────────────────
def fetch_rte_forecast(token):
    logger.info("Récupération des prévisions RTE D-1...")

    headers = {
        "Host": "digital.iservices.rte-france.com",
        "Authorization": f"Bearer {token}"
    }

    # Demain : période complète de 24h
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    end_date   = start_date + timedelta(days=1)

    url = f"{BASE_URL}?type=D-1&start_date={start_date.strftime('%Y-%m-%dT%H:%M:%S')}%2B01:00&end_date={end_date.strftime('%Y-%m-%dT%H:%M:%S')}%2B01:00"
    logger.info(f"URL : {url}")

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        values = response.json()["short_term"][0]["values"]
        all_start_dates = [entry["start_date"] for entry in values]
        all_values      = [entry["value"] for entry in values]
        logger.info(f"{len(values)} prévisions récupérées.")
        return all_start_dates, all_values
    else:
        logger.error(f"Échec requête RTE. Statut : {response.status_code} - {response.text[:200]}")
        return [], []


# ─── 3. Nettoyage et agrégation horaire ──────────────────────────────────────
def clean_data(all_start_dates, all_values):
    logger.info("Nettoyage et transformation des données...")

    df = pd.DataFrame({
        "start_date": all_start_dates,
        "value":      all_values
    })

    if df.empty:
        logger.warning("Aucune donnée reçue.")
        return df

    # Extraction date, heure, minutes
    df["date_column"]    = df["start_date"].apply(lambda x: datetime.fromisoformat(x).date().isoformat())
    df["hour_column"]    = df["start_date"].apply(lambda x: datetime.fromisoformat(x).hour)
    df["minutes_column"] = df["start_date"].apply(lambda x: datetime.fromisoformat(x).minute)

    # Agrégation horaire (moyenne des quarts d'heure)
    mean_value = df.groupby(["date_column", "hour_column"]).apply(
        lambda g: g["value"].sum() / len(g), include_groups=False
    ).reset_index(name="mean_value_hourly")

    df_inter = pd.merge(mean_value, df, on=["date_column", "hour_column"], how="inner")
    df_final = df_inter[df_inter["minutes_column"] == 0]
    df_final = df_final[["start_date", "date_column", "hour_column", "mean_value_hourly"]]
    df_final = df_final.drop_duplicates()
    df_final = df_final.dropna()

    logger.info(f"{len(df_final)} enregistrements après nettoyage.")
    return df_final


# ─── 4. Insertion dans PostgreSQL ────────────────────────────────────────────
def insert_into_db(df):
    if df.empty:
        logger.warning("Aucune donnée à insérer.")
        return

    logger.info("Connexion à PostgreSQL...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor  = conn.cursor()
    inserted = 0
    skipped  = 0

    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO rte_forecasts (timestamp, forecast_value)
                VALUES (%s, %s)
                ON CONFLICT (timestamp) DO NOTHING
            """, (row["start_date"], row["mean_value_hourly"]))
            if cursor.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            logger.error(f"Erreur insertion : {e}")
            skipped += 1

    conn.commit()
    cursor.close()
    conn.close()
    logger.info(f"Insertion terminée : {inserted} lignes insérées, {skipped} ignorées.")


# ─── 5. Fonction principale ───────────────────────────────────────────────────
def main():
    print("\n\n\n")
    logger.info("═══ Démarrage récupération prévisions RTE D-1 ═══")
    try:
        token                       = get_rte_token()
        all_start_dates, all_values = fetch_rte_forecast(token)
        df                          = clean_data(all_start_dates, all_values)
        insert_into_db(df)
        logger.info("═══ Pipeline terminé avec succès ═══")
    except Exception as e:
        logger.error(f"Erreur critique : {e}")

    print("\n")

if __name__ == "__main__":
    main()