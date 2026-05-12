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
        logger.setLevel(logging.INFO)

        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Set rasterio log level
    logger.propagate = False
    return logger

# Define ENV variables
# They will soon be defined directly in the Dockerfile
try:
    PROJECT_ROOT = osp.join(osp.dirname(__file__))
except:
    PROJECT_ROOT = os.getcwd()

DATA_FOLDER = osp.abspath(osp.join(PROJECT_ROOT,'..','..','data'))
REGISTERED_NAME = 'XGBoost_WeatherAUS'
TARGET = 'RainTomorrow'
REPO_OWNER = 'EveAngelion'
REPO_NAME = 'MLOps_Meteo_Australie'
THRESHOLD = 0.63

logger = get_logger()
logger.debug(PROJECT_ROOT)

def predict_RainTomorrow(inference_file:str, target_col:str='RainTomorrow'):
    logger.info('Load Model + data')
    # Config MLFlow
    dagshub.init(repo_owner=REPO_OWNER, repo_name=REPO_NAME, mlflow=True)
    model_name = f'models:/{REGISTERED_NAME}/latest'
    model = mlflow.xgboost.load_model(model_name)

    model_info = mlflow.models.get_model_info(model_name)
    input_schema = model_info.signature.inputs.input_names()
   
    with open(inference_file) as src:
        inference_df = pd.DataFrame([json.load(src)])
    
    inference_df.drop(columns=[target_col], inplace=True)
    inference_df = inference_df[input_schema]
    
    proba = model.predict_proba(inference_df)[0, 1]

    prediction = "Pluie demain" if proba >= THRESHOLD else "Pas de pluie demain"
    confidence = abs(proba - 0.5) * 2

    result = {
        "prediction": prediction,
        "rain_probability": float(proba),
        "confidence": float(confidence)
    }
    
    print(json.dumps(result, indent=2))
    return result

###########
_description = f""" 
Prédiction du modèle à partir des données météos
"""

parser = argparse.ArgumentParser(description='\n'.join([_description]))
parser.add_argument('--city', type=str, required=True, help="City name")
parser.add_argument('--verbose', type=str, required=False, default='INFO', choices=['WARNING','INFO','DEBUG'], help="Logger level")

if __name__ == '__main__':
    kwargs = parser.parse_args()
    print(json.dumps(vars(kwargs), indent=1)) # Pretty print dictionary
    print()

    logger.setLevel(getattr(logging,kwargs.verbose))

    list_city_files = glob.glob(osp.join(DATA_FOLDER, 'inference', f'{kwargs.city}_*.json'))
    data_file = max(list_city_files, key=osp.getctime)

    _ = predict_RainTomorrow(data_file, target_col=TARGET)
    print('Finished !')

