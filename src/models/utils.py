import mlflow
from mlflow.tracking import MlflowClient
from datetime import datetime
import numpy as np
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


