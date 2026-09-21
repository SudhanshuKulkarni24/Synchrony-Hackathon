import csv
import json
from pathlib import Path

import joblib
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    precision_score,
    recall_score,
)

from backend.app.features.builder import FEATURE_NAMES, FEATURE_SCHEMA_VERSION


DATASET_PATH = Path("ml/data/fraud_events.csv")
ARTIFACT_PATH = Path("ml/artifacts/fraud_models.joblib")
EVALUATION_PATH = Path("ml/evaluation/model_metrics.json")


def load_rows(dataset_path: Path) -> tuple[list[list[float]], list[int]]:
    with dataset_path.open(encoding="utf-8", newline="") as dataset_file:
        rows = list(csv.DictReader(dataset_file))
    features = [
        [float(row[name]) for name in FEATURE_NAMES]
        for row in rows
    ]
    labels = [int(row["fraud_label"]) for row in rows]
    return features, labels


def train_and_evaluate(
    dataset_path: Path = DATASET_PATH,
    artifact_path: Path = ARTIFACT_PATH,
    evaluation_path: Path = EVALUATION_PATH,
) -> dict[str, object]:
    features, labels = load_rows(dataset_path)
    split_index = int(len(features) * 0.8)
    validation_index = int(len(features) * 0.9)
    train_features = features[:split_index]
    train_labels = labels[:split_index]
    test_features = features[validation_index:]
    test_labels = labels[validation_index:]

    classifier = RandomForestClassifier(
        n_estimators=150,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    classifier.fit(train_features, train_labels)

    anomaly_detector = IsolationForest(
        n_estimators=100,
        contamination="auto",
        random_state=42,
    )
    anomaly_detector.fit(train_features)

    probabilities = classifier.predict_proba(test_features)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    metrics = {
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "model_type": "RandomForestClassifier",
        "anomaly_model_type": "IsolationForest",
        "dataset_rows": len(features),
        "train_rows": len(train_features),
        "test_rows": len(test_features),
        "fraud_rows": sum(labels),
        "fraud_rate": round(sum(labels) / len(labels), 4),
        "precision": round(precision_score(test_labels, predictions, zero_division=0), 4),
        "recall": round(recall_score(test_labels, predictions, zero_division=0), 4),
        "pr_auc": round(average_precision_score(test_labels, probabilities), 4),
        "confusion_matrix": confusion_matrix(test_labels, predictions).tolist(),
        "threshold": 0.5,
    }
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    evaluation_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "classifier": classifier,
            "anomaly_detector": anomaly_detector,
            "feature_names": FEATURE_NAMES,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "model_version": "fraud-model-0.1.0",
        },
        artifact_path,
    )
    evaluation_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    print(json.dumps(train_and_evaluate(), indent=2))