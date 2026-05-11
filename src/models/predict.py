import os
import os.path as osp
import json, logging, sys, argparse, glob
import pandas as pd
import numpy as np
# from tqdm import tqdm
# from sklearn.metrics import (
#     accuracy_score,
#     roc_auc_score,
#     recall_score,
#     f1_score,
#     log_loss,
#     brier_score_loss,
#     precision_recall_curve,
#     auc
# )
# import xgboost as xgb
import joblib

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

logger = get_logger()
logger.debug(PROJECT_ROOT)

def predict_RainTomorrow(inference_file:str, model_file:str, metrics_file:str, features_file:str):
    target = 'RainTomorrow'

    logger.info('Load Model + data')
    model = joblib.load(model_file)
    with open(metrics_file) as src:
        model_metrics = json.load(src)

    with open(inference_file) as src:
        inference_df = pd.DataFrame([json.load(src)])
    
    features_columns = np.load(features_file)
    
    inference_df.drop(columns=[target], inplace=True)
    inference_df = inference_df[features_columns] #Re-organize columns names

    threshold = model_metrics['best_threshold']
    proba = model.predict_proba(inference_df)[0, 1]

    prediction = "Pluie demain" if proba >= threshold else "Pas de pluie demain"
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
parser.add_argument('--data_name', type=str, required=True, help="JSON file name")
parser.add_argument('--model', type=str, required=False, default='v1', help="Model folder name")
parser.add_argument('--verbose', type=str, required=False, default='INFO', choices=['WARNING','INFO','DEBUG'], help="Logger level")

if __name__ == '__main__':
    kwargs = parser.parse_args()
    print(json.dumps(vars(kwargs), indent=1)) # Pretty print dictionary
    print()

    logger.setLevel(getattr(logging,kwargs.verbose))

    data_file = osp.join(DATA_FOLDER, 'inference', kwargs.data_name)
    model_file = glob.glob(osp.join(DATA_FOLDER, 'models', kwargs.model, '*.joblib'))[0]
    metrics_file = glob.glob(osp.join(DATA_FOLDER, 'models', kwargs.model, '*_metrics.json'))[0]
    features_file = glob.glob(osp.join(DATA_FOLDER, 'models', kwargs.model, '*_features_names.npy'))[0]

    _ = predict_RainTomorrow(data_file, model_file, metrics_file, features_file)
    print('Finished !')

