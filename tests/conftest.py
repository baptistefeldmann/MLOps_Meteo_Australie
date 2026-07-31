import sys
from unittest.mock import MagicMock

# Block heavy ML imports before any project module is loaded.
# dagshub.init() and mlflow model loading are called at module level
# in src/models/predict.py, which would fail in CI without real credentials.
for _mod in ["dagshub", "mlflow", "mlflow.xgboost", "mlflow.models", "xgboost", "sklearn"]:
    sys.modules.setdefault(_mod, MagicMock())
