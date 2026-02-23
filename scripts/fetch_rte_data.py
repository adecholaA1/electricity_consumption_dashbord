import os
import requests
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pytz
import logging
import time

# ─── Configuration du logging ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/fetch_historical.log"),
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


# ─── 2. Détection automatique du fuseau horaire ─────────────────────────────
def get_timezone_offset(dt):
    """
    Retourne le bon fuseau horaire pour une date donnée en France.
    +01:00 en hiver (UTC+1)
    +02:00 en été (UTC+2)
    """
    paris_tz = pytz.timezone('Europe/Paris')
    dt_paris = paris_tz.localize(dt)
    offset = dt_paris.strftime('%z')
    return f"+{offset[1:3]}:00"


# ─── 3. Récupération des données RTE pour J-1 ────────────────────────────────
def fetch_consumption(token):
    logger.info("Récupération des données de consommation J-1...")

    headers = {
        "Host": "digital.iservices.rte-france.com",
        "Authorization": f"Bearer {token}"
    }

    # CORRECTION 1 : Récupérer J-1 complet (de 00:00 à 23:59)
    # Aujourd'hui à 00:00
    today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Hier à 00:00
    yesterday_midnight = today_midnight - timedelta(days=1)
    
    # Dates de début et fin pour J-1
    start_date = yesterday_midnight
    end_date = today_midnight
    
    # CORRECTION 2 : Utiliser le bon fuseau horaire (détection automatique)
    start_tz = get_timezone_offset(start_date)
    end_tz = get_timezone_offset(end_date)
    
    logger.info(f"Période : {start_date.date()} 00:00 → {end_date.date()} 00:00 (J-1 complet)")
    logger.info(f"Fuseau horaire : {start_tz}")

    # Construction de l'URL
    url = (
        f"{BASE_URL}?type=REALISED"
        f"&start_date={start_date.strftime('%Y-%m-%dT%H:%M:%S')}{start_tz}"
        f"&end_date={end_date.strftime('%Y-%m-%dT%H:%M:%S')}{end_tz}"
    )
    
    logger.info(f"Requête : {url}")

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        
        # Vérifier que les données existent
        if "short_term" not in data or not data["short_term"]:
            logger.warning("Aucune donnée 'short_term' dans la réponse.")
            return [], []
        
        values = data["short_term"][0]["values"]
        all_start_dates = [entry["start_date"] for entry in values]
        all_values      = [entry["value"] for entry in values]
        
        logger.info(f"✓ {len(values)} enregistrements récupérés (granularité 15 min)")
        
        # CORRECTION 3 : Vérifier qu'on a bien ~96 enregistrements (24h × 4 quarts d'heure)
        expected_records = 96  # 24 heures × 4 quarts d'heure
        if len(values) < expected_records * 0.9:  # Tolérance de 10%
            logger.warning(f"⚠ Seulement {len(values)} enregistrements reçus (attendu: ~{expected_records})")
        
        return all_start_dates, all_values
    else:
        logger.error(f"✗ Échec requête RTE. Statut : {response.status_code}")
        logger.error(f"Message : {response.text[:500]}")
        return [], []


# ─── 4. Nettoyage et agrégation horaire ──────────────────────────────────────
def clean_data(all_start_dates, all_values):
    logger.info("Nettoyage et agrégation horaire des données...")

    df = pd.DataFrame({
        "start_date": all_start_dates,
        "value":      all_values
    })

    if df.empty:
        logger.warning("⚠ Aucune donnée reçue.")
        return df

    logger.info(f"  Données brutes : {len(df)} lignes")

    # CORRECTION 4 : Extraction date, heure, minutes avec gestion des fuseaux
    df["date_column"]    = df["start_date"].apply(lambda x: datetime.fromisoformat(x).date().isoformat())
    df["hour_column"]    = df["start_date"].apply(lambda x: datetime.fromisoformat(x).hour)
    df["minutes_column"] = df["start_date"].apply(lambda x: datetime.fromisoformat(x).minute)

    # Agrégation horaire (moyenne des 4 quarts d'heure)
    mean_value = df.groupby(["date_column", "hour_column"]).apply(
        lambda g: g["value"].sum() / len(g), include_groups=False
    ).reset_index(name="mean_value_hourly")

    logger.info(f"  Après agrégation : {len(mean_value)} heures")

    # CORRECTION 5 : Sélection intelligente des lignes (priorité à minutes==0)
    df_inter = pd.merge(mean_value, df, on=["date_column", "hour_column"], how="inner")
    
    # Trier par date, heure, minutes
    df_inter = df_inter.sort_values(['date_column', 'hour_column', 'minutes_column'])
    
    # Pour chaque (date, heure), prendre la ligne où minutes == 0 si elle existe, sinon la première
    def select_best_minute(group):
        zero_min = group[group['minutes_column'] == 0]
        if len(zero_min) > 0:
            return zero_min.iloc[0]
        return group.iloc[0]
    
    df_final = df_inter.groupby(['date_column', 'hour_column'], as_index=False).apply(
        select_best_minute, include_groups=False
    ).reset_index(drop=True)
    
    df_final = df_final[["start_date", "date_column", "hour_column", "mean_value_hourly"]]
    df_final = df_final.drop_duplicates(subset=['start_date'], keep='first')
    df_final = df_final.dropna()

    logger.info(f"✓ {len(df_final)} enregistrements après nettoyage (attendu: 24)")
    
    # CORRECTION 6 : Vérifier qu'on a bien 24 heures
    if len(df_final) != 24:
        logger.warning(f"⚠ Attention : {len(df_final)} heures au lieu de 24 !")
        missing_hours = set(range(24)) - set(df_final['hour_column'])
        if missing_hours:
            logger.warning(f"  Heures manquantes : {sorted(missing_hours)}")

    return df_final


# ─── 5. Insertion dans PostgreSQL ────────────────────────────────────────────
def insert_into_db(df):
    if df.empty:
        logger.warning("⚠ Aucune donnée à insérer.")
        return

    logger.info("Insertion dans PostgreSQL...")
    
    try:
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
                    INSERT INTO historical_data (timestamp, value, source)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (timestamp) DO NOTHING
                """, (row["start_date"], row["mean_value_hourly"], "RTE"))
                
                if cursor.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1
                    
            except Exception as e:
                logger.error(f"✗ Erreur insertion ligne : {e}")
                skipped += 1

        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✓ Insertion terminée : {inserted} nouvelles lignes, {skipped} ignorées (déjà existantes)")
        
    except Exception as e:
        logger.error(f"✗ Erreur connexion PostgreSQL : {e}")
        raise


# ─── 6. Fonction principale ───────────────────────────────────────────────────
def main():
    print("\n\n\n")
    logger.info("═══════════════════════════════════════════════════════════")
    logger.info("  Récupération des données historiques RTE (J-1)")
    logger.info("═══════════════════════════════════════════════════════════")

    MAX_RETRIES = 3
    RETRY_DELAY = 30 * 60  # 30 minutes en secondes

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Tentative {attempt}/{MAX_RETRIES}...")

            token = get_rte_token()
            all_start_dates, all_values = fetch_consumption(token)
            df = clean_data(all_start_dates, all_values)

            if df.empty:
                raise ValueError("Aucune donnée récupérée depuis RTE.")

            insert_into_db(df)

            logger.info("═══════════════════════════════════════════════════════════")
            logger.info("  ✓ Pipeline terminé avec succès")
            logger.info("═══════════════════════════════════════════════════════════")
            return

        except Exception as e:
            logger.error(f"✗ Erreur tentative {attempt}/{MAX_RETRIES} : {e}", exc_info=True)
            if attempt < MAX_RETRIES:
                logger.info(f"⏳ Nouvelle tentative dans 30 minutes...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error("✗ Toutes les tentatives ont échoué.")
                raise

if __name__ == "__main__":
    main()