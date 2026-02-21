import torch
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from chronos import ChronosPipeline
import logging

# ─── Configuration du logging ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ─── Chemin du modèle ─────────────────────────────────────────────────────────
MODEL_PATH = "/Users/kouande/Desktop/Dev_logiciel/electricity_project/models/run-0/checkpoint-final"

# ─── Initialisation de l'app FastAPI ──────────────────────────────────────────
app = FastAPI(title="Chronos Prediction API", version="1.0.0")

# ─── Chargement du modèle au démarrage ────────────────────────────────────────
pipeline = None

@app.on_event("startup")
async def load_model():
    global pipeline
    logger.info(f"Chargement du modèle depuis {MODEL_PATH}...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Device utilisé : {device}")
    pipeline = ChronosPipeline.from_pretrained(
        MODEL_PATH,
        device_map=device,
        torch_dtype=torch.bfloat16,
    )
    logger.info("✓ Modèle Chronos chargé en mémoire.")

# ─── Schéma de la requête ─────────────────────────────────────────────────────
class PredictRequest(BaseModel):
    context: list[float]        # Les 528 valeurs de contexte
    prediction_length: int = 24 # Nombre d'heures à prédire
    num_samples: int = 50       # Nombre d'échantillons Monte Carlo

# ─── Schéma de la réponse ─────────────────────────────────────────────────────
class PredictResponse(BaseModel):
    predictions: list[float]    # Les 24 valeurs prédites (médiane)
    mean: float
    min: float
    max: float

# ─── Route de santé ───────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model_loaded": pipeline is not None
    }

# ─── Route de prédiction ──────────────────────────────────────────────────────
@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Modèle non chargé")
    
    if len(request.context) == 0:
        raise HTTPException(status_code=400, detail="Le contexte est vide")
    
    logger.info(f"Prédiction reçue : {len(request.context)} valeurs de contexte")
    
    try:
        # Préparer le contexte
        context = torch.tensor(request.context, dtype=torch.float32)
        
        # Générer la prédiction
        forecast = pipeline.predict(
            context,
            request.prediction_length,
            num_samples=request.num_samples
        )
        
        # Calculer la médiane
        median = np.quantile(forecast[0].numpy(), 0.5, axis=0)
        predictions = [round(float(v), 2) for v in median]
        
        logger.info(f"✓ Prédiction générée : {len(predictions)} valeurs")
        logger.info(f"  Moyenne : {np.mean(predictions):.2f} MW")
        
        return PredictResponse(
            predictions=predictions,
            mean=round(float(np.mean(predictions)), 2),
            min=round(float(np.min(predictions)), 2),
            max=round(float(np.max(predictions)), 2)
        )
    
    except Exception as e:
        logger.error(f"Erreur prédiction : {e}")
        raise HTTPException(status_code=500, detail=str(e))
