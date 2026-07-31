from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.data.collect_inference import collect_inference_data
from src.prediction.predict import predict_RainTomorrow, TARGET

app = FastAPI(title="Weather MLOps API")


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