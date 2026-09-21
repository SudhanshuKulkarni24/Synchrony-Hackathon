from pathlib import Path

from ml.training.train_models import train_and_evaluate


def test_training_creates_versioned_artifact_and_metrics(tmp_path: Path) -> None:
    dataset_path = Path("ml/data/fraud_events.csv")
    artifact_path = tmp_path / "fraud_models.joblib"
    evaluation_path = tmp_path / "model_metrics.json"

    metrics = train_and_evaluate(dataset_path, artifact_path, evaluation_path)

    assert artifact_path.exists()
    assert evaluation_path.exists()
    assert metrics["feature_schema_version"] == "features-1.0.0"
    assert metrics["model_type"] == "RandomForestClassifier"
    assert 0.0 <= metrics["precision"] <= 1.0
    assert 0.0 <= metrics["recall"] <= 1.0
    assert 0.0 <= metrics["pr_auc"] <= 1.0