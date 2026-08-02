from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator
import numpy as np

from src.data.collect_inference import collect_inference_data
from src.prediction.predict import predict_RainTomorrow, TARGET

app = FastAPI(title="Weather MLOps API")

# --- Prometheus : métriques HTTP automatiques + création de l'endpoint /metrics ---
Instrumentator().instrument(app).expose(app)

# --- Prometheus : métriques "métier" ---
step = 0.05
PROBA_BUCKETS = np.arange(0.0, 1.0 + step, step)

PREDICTION_CONFIDENCE = Histogram(
    "prediction_confidence",
    "Confidence de la prediction RainTomorrow (abs(proba-0.5)*2)",
    buckets=PROBA_BUCKETS,
)

PREDICTION_RAIN_PROBABILITY = Histogram(
    "prediction_rain_probability",
    "Probabilite de pluie predite",
    buckets=PROBA_BUCKETS,
)

PREDICTIONS_TOTAL = Counter(
    "predictions_total",
    "Nombre total de predictions reussies",
    ["outcome"],
)

class PredictRequest(BaseModel):
    city: str
    verbose: str = "INFO"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def predict(req: PredictRequest):
    try:
        inference_file = collect_inference_data(req.city)

        result = predict_RainTomorrow(
            inference_file=inference_file,
            target_col=TARGET,
        )

        # --- Prometheus : mise à jour des métriques métier ---
        outcome = "rain" if result["prediction"] == "Pluie demain" else "no_rain"
        PREDICTION_CONFIDENCE.observe(result["confidence"])
        PREDICTION_RAIN_PROBABILITY.observe(result["rain_probability"])
        PREDICTIONS_TOTAL.labels(outcome=outcome).inc()

        return {
            "status": "success",
            "city": req.city,
            "inference_file": inference_file,
            "result": result,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))