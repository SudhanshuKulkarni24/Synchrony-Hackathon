from dataclasses import dataclass
from pathlib import Path

import joblib

from .features.builder import FEATURE_NAMES, FEATURE_SCHEMA_VERSION, FeatureVector


DEFAULT_ARTIFACT_PATH = (
    Path(__file__).resolve().parents[2] / "ml" / "artifacts" / "fraud_models.joblib"
)


@dataclass(frozen=True)
class ModelEvidence:
    supervised_risk: float
    anomaly_risk: float
    model_version: str
    used_fallback: bool


class FraudModel:
    def __init__(self, artifact_path: Path = DEFAULT_ARTIFACT_PATH) -> None:
        self.artifact_path = artifact_path
        self.artifact: dict[str, object] | None = None
        self.load_error: str | None = None
        self._load()

    def _load(self) -> None:
        try:
            artifact = joblib.load(self.artifact_path)
            if artifact.get("feature_schema_version") != FEATURE_SCHEMA_VERSION:
                raise ValueError("Model feature schema version does not match the API")
            if tuple(artifact.get("feature_names", ())) != FEATURE_NAMES:
                raise ValueError("Model feature names do not match the API")
            self.artifact = artifact
        except (FileNotFoundError, OSError, ValueError, AttributeError) as error:
            self.load_error = str(error)

    def predict(self, vector: FeatureVector) -> ModelEvidence:
        if self.artifact is None:
            return ModelEvidence(0.0, 0.0, "fallback-0.1.0", True)

        values = [list(vector.values)]
        classifier = self.artifact["classifier"]
        anomaly_detector = self.artifact["anomaly_detector"]
        supervised_risk = float(classifier.predict_proba(values)[0][1])
        normality = float(anomaly_detector.decision_function(values)[0])
        anomaly_risk = max(0.0, min(1.0, 0.5 - normality))
        return ModelEvidence(
            supervised_risk=round(supervised_risk, 4),
            anomaly_risk=round(anomaly_risk, 4),
            model_version=str(self.artifact["model_version"]),
            used_fallback=False,
        )