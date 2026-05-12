import os
import os.path as osp
import json, logging, sys, argparse
import pandas as pd
import xgboost as xgb
import dagshub
import mlflow
from mlflow.models import infer_signature

# Local modules
import utils

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
RANDOM_SEED = 42
REPO_OWNER = 'EveAngelion'
REPO_NAME = 'MLOps_Meteo_Australie'
EXPERIMENT_NAME = "Weather_AUS_Models"
TARGET_NAME = 'RainTomorrow'
REGISTERED_NAME = 'XGBoost_WeatherAUS'

logger = get_logger()
logger.debug(PROJECT_ROOT)

def train_xgboost_pipeline(train_path:str, test_path:str, valid_path:str, target_col:str="RainTomorrow"):
    logger.info('Training model')

    # Config MLFlow
    dagshub.init(repo_owner=REPO_OWNER, repo_name=REPO_NAME, mlflow=True)
    weather_experiment = mlflow.set_experiment(EXPERIMENT_NAME)
    run_name = utils.get_next_run_name(EXPERIMENT_NAME)
    registered_name = REGISTERED_NAME

    train_df = pd.read_parquet(train_path)
    test_df = pd.read_parquet(test_path)
    valid_df = pd.read_parquet(valid_path)

    # --- séparation target
    y_train = train_df[target_col].astype(int)
    y_val   = valid_df[target_col].astype(int)
    y_test  = test_df[target_col].astype(int)

    X_train = train_df.drop(columns=target_col)
    X_val   = valid_df.drop(columns=target_col)
    X_test  = test_df.drop(columns=target_col)

    params = {
        'n_estimators': 2000,
        'learning_rate': 0.03,
        'max_depth': 5,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'min_child_weight': 15,
        'reg_alpha': 0.3,
        'reg_lambda': 1.0,
        'eval_metric': "logloss",
        'scale_pos_weight': (y_train == 0).sum() / (y_train == 1).sum(),
        'random_state': RANDOM_SEED
    }

    model = xgb.XGBClassifier(**params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )

    metrics = utils.evaluate(model, X_val, y_val, "VALIDATION")

    signature = infer_signature(X_train, model.predict(X_train))
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        mlflow.xgboost.log_model(
            xgb_model=model, input_example=X_val,
            name='model', signature=signature,
            registered_model_name=registered_name
        )
    
    logger.info('Completed !')

##############
_description = f""" 
Entrainement du modèle à partir des données météos par station
"""

parser = argparse.ArgumentParser(description='\n'.join([_description]))
parser.add_argument('--verbose', type=str, required=False, default='INFO', choices=['WARNING','INFO','DEBUG'], help="Logger level")

if __name__ == '__main__':
    kwargs = parser.parse_args()
    print(json.dumps(vars(kwargs), indent=1)) # Pretty print dictionary
    print()

    logger.setLevel(getattr(logging,kwargs.verbose))

    train_path = osp.join(DATA_FOLDER, 'datasets', 'data_train.parquet')
    test_path = osp.join(DATA_FOLDER, 'datasets', 'data_test.parquet')
    valid_path = osp.join(DATA_FOLDER, 'datasets', 'data_valid.parquet')
    train_xgboost_pipeline(train_path, test_path, valid_path, TARGET_NAME)
    
    logger.info('Finished !')


