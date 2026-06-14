import os
import os.path as osp
import json, logging, argparse, time
import pandas as pd
import xgboost as xgb
import dagshub
import mlflow
from mlflow.models import infer_signature

# Local modules
from src.training import utils
# import utils

# Define ENV variables
# They will soon be defined directly in the Dockerfile
try:
    PROJECT_ROOT = osp.join(osp.dirname(__file__))
except:
    PROJECT_ROOT = os.getcwd()

DATA_FOLDER = osp.abspath(osp.join(PROJECT_ROOT,'..','..','data'))
RANDOM_SEED = 42
MLFLOW_PARAMS = {
    'repo_owner': 'EveAngelion',
    'repo_name': 'MLOps_Meteo_Australie',
    'experiment_name': "Weather_AUS_Models",
    'registered_name': 'XGBoost_WeatherAUS',
    'target_name': 'RainTomorrow'
}

# Config MLFlow
dagshub.init(repo_owner=MLFLOW_PARAMS['repo_owner'],
                repo_name=MLFLOW_PARAMS['repo_name'],
                mlflow=True)

logger = utils.get_logger()
logger.debug(PROJECT_ROOT)

def train_xgboost_pipeline(train_path:str, test_path:str, valid_path:str, target_col:str="RainTomorrow"):
    logger.info('Training model')
    weather_experiment = mlflow.set_experiment(MLFLOW_PARAMS['experiment_name'])
    run_name = utils.get_next_run_name(MLFLOW_PARAMS['experiment_name'])
    registered_name = MLFLOW_PARAMS['registered_name']

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
        'n_estimators': 3000,
        'learning_rate': 0.03,
        'max_depth': 5,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'min_child_weight': 15,
        'reg_alpha': 0.3,
        'reg_lambda': 1.0,
        'eval_metric': "logloss",
        'scale_pos_weight': (y_train == 0).sum() / (y_train == 1).sum(),
        'early_stopping_rounds': 50,
        'random_state': RANDOM_SEED
    }

    model = xgb.XGBClassifier(**params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=100
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

        time.sleep(2)
        utils.models_comparison(
            registered_name,
            current_run_id=run.info.run_id,
            metrics=metrics
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
    train_xgboost_pipeline(train_path, test_path, valid_path, MLFLOW_PARAMS['target_name'])
    
    logger.info('Finished !')


