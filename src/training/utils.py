import mlflow
from mlflow.tracking import MlflowClient
from datetime import datetime
import numpy as np
import logging, sys
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

logger = get_logger()

def get_next_run_name(experiment_name):
    client = MlflowClient()
    
    # 1. Récupérer l'ID de l'expérience
    exp = client.get_experiment_by_name(experiment_name)
    if not exp:
        return f"{datetime.now().strftime('%Y-%m-%d')}_1"
    
    # 2. Définir le préfixe de date (ex: 2024-05-27)
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # 3. Rechercher les runs de cette expérience
    # On utilise une requête de filtrage pour gagner en performance
    runs = client.search_runs(
        experiment_ids=[exp.experiment_id],
        filter_string=f"attributes.run_name LIKE '{today_str}%'"
    )
    
    # 4. Calculer l'ID suivant
    next_id = len(runs) + 1
    return f"{today_str}_{next_id}"

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

def models_comparison(model_name, current_run_id, metrics, eps=0.001):
    client = MlflowClient()

    current_pr_auc = metrics['pr_auc']
    current_logloss = metrics['logloss']

    all_versions = client.search_model_versions(f"name='{model_name}'")
    current_version_obj = next((v for v in all_versions if v.run_id == current_run_id), None)
    current_version = current_version_obj.version

    try:
        champion_version = client.get_model_version_by_alias(model_name, "best_model")
        has_champion = True
    except Exception as e:
        logger.warning(f"Best_model version not found : {e}")
        has_champion = False
    
    if not has_champion:
        logger.info("No current best_model. Current model becomes best_mode version !")
        # On lui attribue l'alias 'best_model'
        client.set_registered_model_alias(model_name, "best_model", str(current_version))
        return True

    # Si un champion existe, on récupère ses métriques pour comparer
    champion_run = client.get_run(champion_version.run_id)
    champion_metrics = champion_run.data.metrics
    
    champion_pr_auc = champion_metrics.get('pr_auc', 0)
    champion_logloss = champion_metrics.get('logloss', float('inf'))
    
    logger.info(f"Actual Best_model (Run: {champion_version.run_id}) -> PR_AUC: {champion_pr_auc:.4f} | LogLoss: {champion_logloss:.4f}")
    logger.info(f"Challenger training model (Run: {current_run_id}) -> PR_AUC: {current_pr_auc:.4f} | LogLoss: {current_logloss:.4f}")
    
    # Logique de décision : Le modèle est-il meilleur ?
    # Condition principale : PR_AUC supérieur d'au moins un micro-seuil (ex: 0.001) pour éviter les changements inutiles
    is_better = False
    if current_pr_auc > champion_pr_auc + eps:
        is_better = True
    elif abs(current_pr_auc - champion_pr_auc) <= eps:
        # En cas d'égalité sur le PR_AUC, on départage avec la LogLoss (la plus basse est la meilleure)
        if current_logloss < champion_logloss:
            is_better = True

    # Action de remplacement si le modèle est meilleur
    if is_better:
        logger.info("🎉 Challenger model is BETTER !!")
        # On déplace l'alias 'champion' sur cette nouvelle version (MLflow gère le retrait sur l'ancienne auto)
        client.set_registered_model_alias(model_name, "best_model", str(current_version))
        
        logger.info(f"New Best_model successfully registered (Version {current_version})")
        return True
    else:
        logger.info("❌ Challenger model is not the best. Keeping actual Best_model.")
        return False
