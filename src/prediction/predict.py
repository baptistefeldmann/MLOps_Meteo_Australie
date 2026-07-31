import os
import os.path as osp
import json, logging, sys, argparse, glob
import pandas as pd
import dagshub
import mlflow


def get_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    logger.propagate = False
    return logger


logger = get_logger()


def get_model():
    logger.info("Load model")

    dagshub.init(
        repo_owner="EveAngelion",
        repo_name="MLOps_Meteo_Australie",
        mlflow=True
    )

    model_name = "models:/XGBoost_WeatherAUS@best_model"
    model = mlflow.xgboost.load_model(model_name)

    model_info = mlflow.models.get_model_info(model_name)
    input_schema = model_info.signature.inputs.input_names()

    return model, input_schema


try:
    PROJECT_ROOT = osp.join(osp.dirname(__file__))
except Exception:
    PROJECT_ROOT = os.getcwd()


DATA_FOLDER = osp.abspath(osp.join(PROJECT_ROOT, "..", "..", "data"))
TARGET = "RainTomorrow"
THRESHOLD = 0.60

logger.debug(PROJECT_ROOT)

MODEL, INPUT_SCHEMA = get_model()


def predict_RainTomorrow(inference_file: str, target_col: str = "RainTomorrow"):
    logger.info("Load data")

    with open(inference_file) as src:
        inference_df = pd.DataFrame([json.load(src)])

    inference_df.drop(columns=[target_col], inplace=True, errors="ignore")
    inference_df = inference_df[INPUT_SCHEMA]

    proba = MODEL.predict_proba(inference_df)[0, 1]

    prediction = "Pluie demain" if proba >= THRESHOLD else "Pas de pluie demain"
    confidence = abs(proba - 0.5) * 2

    result = {
        "prediction": prediction,
        "rain_probability": float(proba),
        "confidence": float(confidence)
    }

    print(json.dumps(result, indent=2))
    return result


_description = """
Prédiction du modèle à partir des données météos
"""

parser = argparse.ArgumentParser(description=_description)
parser.add_argument("--city", type=str, required=True, help="City name")
parser.add_argument(
    "--verbose",
    type=str,
    required=False,
    default="INFO",
    choices=["WARNING", "INFO", "DEBUG"],
    help="Logger level"
)


if __name__ == "__main__":
    kwargs = parser.parse_args()

    print(json.dumps(vars(kwargs), indent=1))
    print()

    logger.setLevel(getattr(logging, kwargs.verbose))

    list_city_files = glob.glob(
        osp.join(DATA_FOLDER, "inference", f"{kwargs.city}_*.json")
    )

    if not list_city_files:
        raise FileNotFoundError(
            f"No inference file found for city={kwargs.city} in {osp.join(DATA_FOLDER, 'inference')}"
        )

    data_file = max(list_city_files, key=osp.getctime)

    _ = predict_RainTomorrow(data_file, target_col=TARGET)

    print("Finished !")