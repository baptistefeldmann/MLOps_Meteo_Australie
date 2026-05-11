import os
import os.path as osp
import json, logging, sys, glob, argparse, time
import pandas as pd
import numpy as np
from tqdm import tqdm
from sklearn.metrics import (
    accuracy_score,
    roc_auc_score,
    recall_score,
    f1_score,
    log_loss,
    brier_score_loss,
    precision_recall_curve,
    auc
)
import xgboost as xgb
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
RANDOM_SEED = 42

logger = get_logger()
logger.debug(PROJECT_ROOT)

def evaluate(model, X, y, name="set", threshold=None):
    proba = model.predict_proba(X)[:, 1]

    if threshold is None:
        best_threshold, best_f1_score = optimize_threshold(y,proba)
    else:
        best_threshold = threshold
        best_f1_score = None

    pred = (proba >= best_threshold).astype(int)

    # métriques classiques
    acc = accuracy_score(y, pred)
    roc_auc = roc_auc_score(y, proba)
    recall = recall_score(y, pred)
    f1 = f1_score(y, pred)
    logloss = log_loss(y, proba)
    brier = brier_score_loss(y, proba)

    # PR AUC
    precision, recall_curve, _ = precision_recall_curve(y, proba)
    pr_auc = auc(recall_curve, precision)

    print(f"\n📊 {name}")
    print(f"Best Threshold : {best_threshold:.3f}")
    if best_f1_score is not None:
        print(f"Best F1-score : {best_f1_score:.3f}")
    print(f"Accuracy  : {acc:.4f}")
    print(f"ROC AUC   : {roc_auc:.4f}")
    print(f"PR AUC    : {pr_auc:.4f}")
    print(f"Recall    : {recall:.4f}")
    print(f"F1-score  : {f1:.4f}")
    print(f"LogLoss   : {logloss:.4f}")
    print(f"Brier     : {brier:.4f}")

    dict_metrics = {
        'best_threshold': best_threshold,
        'accuracy': acc,
        'roc_auc': roc_auc,
        'pr_auc': pr_auc,
        'recall': recall,
        'best_f1_score': best_f1_score,
        'f1_score': f1,
        'logloss': logloss,
        'brier': brier
    }

    return dict_metrics

def optimize_threshold(y_true, proba):
    best_t = 0.5
    best_f1 = 0

    for t in np.linspace(0.3, 0.8, 100):
        pred = (proba >= t).astype(int)
        f1 = f1_score(y_true, pred)

        if f1 > best_f1:
            best_f1 = f1
            best_t = t

    return best_t, best_f1

def create_datasets(data_train_path:str, data_test_path:str, data_valid_path:str,
                    train_ratio:float=0.75, test_ratio:float=0.2):
    logger.info('Create datasets')
    list_data_files = glob.glob(osp.join(DATA_FOLDER, 'features', '*.parquet'))
    list_train_df = []
    list_test_df = []
    list_valid_df = []

    for filepath in tqdm(list_data_files):
        df = pd.read_parquet(filepath)
        df.drop(['Date'], inplace=True, axis=1)
        idx_train = int(len(df) * train_ratio)
        idx_test = idx_train + int(len(df) * test_ratio)

        X_train, X_test, X_valid  = df.iloc[:idx_train], df.iloc[idx_train:idx_test], df.iloc[idx_test:]
        list_train_df.append(X_train)
        list_test_df.append(X_test)
        list_valid_df.append(X_valid)

    data_train_df = pd.concat(list_train_df, ignore_index=True)
    data_test_df = pd.concat(list_test_df, ignore_index=True)
    data_valid_df = pd.concat(list_valid_df, ignore_index=True)

    data_train_df.to_parquet(data_train_path, index=False)
    data_test_df.to_parquet(data_test_path, index=False)
    data_valid_df.to_parquet(data_valid_path, index=False)
    logger.info('Completed !')

def train_xgboost_pipeline(train_path:str, test_path:str, valid_path:str, target_col:str="RainTomorrow"):
    logger.info('Training model')
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

    model = xgb.XGBClassifier(
        n_estimators=2000,
        learning_rate=0.03,
        max_depth=5,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=15,
        reg_alpha=0.3,
        reg_lambda=1.0,
        eval_metric="logloss",
        scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum(),
        random_state=RANDOM_SEED
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )

    metrics = evaluate(model, X_val, y_val, "VALIDATION")
    logger.info('Completed !')
    return model, metrics

def main(kwargs):
    train_path = osp.join(DATA_FOLDER, 'datasets', 'data_train.parquet')
    test_path = osp.join(DATA_FOLDER, 'datasets', 'data_test.parquet')
    valid_path = osp.join(DATA_FOLDER, 'datasets', 'data_valid.parquet')
    model_folder = osp.join(DATA_FOLDER, 'models', kwargs.model_name)
    os.makedirs(model_folder, exist_ok=True)

    if kwargs.mode in ['datasets','ALL']:
        create_datasets(train_path, test_path, valid_path,
                        kwargs.train_ratio, kwargs.test_ratio)
        time.sleep(0.5)
    
    if kwargs.mode in ['training','ALL']:
        model,metrics = train_xgboost_pipeline(train_path, test_path, valid_path, kwargs.target)

        logger.info('Save Model + metrics')
        model_path = osp.join(model_folder, 'xgboost_model.joblib')
        metrics_path = osp.join(model_folder, 'xgboost_metrics.json')
        features_path = osp.join(model_folder, 'xgboost_features_names.npy')

        joblib.dump(model, model_path)

        with open(metrics_path, "w") as dst:
            json.dump(metrics, dst, indent=2)
        
        np.save(features_path, model.feature_names_in_)

##############
_description = f""" 
Entrainement du modèle à partir des données météos par station
"""

parser = argparse.ArgumentParser(description='\n'.join([_description]))
parser.add_argument('--mode', type=str, required=False, default='ALL', choices=['datasets','training','ALL'], help="Training mode")
parser.add_argument('--train_ratio', type=float, required=False, default=0.75, help="Split train ratio")
parser.add_argument('--test_ratio', type=float, required=False, default=0.2, help="Split test ratio")
parser.add_argument('--model_name', type=str, required=False, default='v1', help="Version model")
parser.add_argument('--target', type=str, required=False, default='RainTomorrow', help="Target column name")
parser.add_argument('--verbose', type=str, required=False, default='INFO', choices=['WARNING','INFO','DEBUG'], help="Logger level")

if __name__ == '__main__':
    kwargs = parser.parse_args()
    print(json.dumps(vars(kwargs), indent=1)) # Pretty print dictionary
    print()

    logger.setLevel(getattr(logging,kwargs.verbose))

    main(kwargs)
    
    logger.info('Finished !')


