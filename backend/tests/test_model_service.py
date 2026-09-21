from pathlib import Path

from app.features.builder import build_features
from app.model_service import FraudModel


def test_missing_model_artifact_uses_safe_fallback(tmp_path: Path) -> None:
    model = FraudModel(tmp_path / "missing.joblib")

    evidence = model.predict(build_features({}))

    assert evidence.used_fallback is True
    assert evidence.model_version == "fallback-0.1.0"
    assert evidence.supervised_risk == 0.0


def test_trained_model_returns_risk_evidence() -> None:
    model = FraudModel(Path("ml/artifacts/fraud_models.joblib"))

    evidence = model.predict(
        build_features(
            {
                "applications_last_24h": 8,
                "is_new_device": True,
                "identity_match_score": 0.5,
                "device_account_count": 5,
                "payment_account_count": 5,
                "ip_risk_score": 0.95,
            }
        )
    )

    assert evidence.used_fallback is False
    assert evidence.model_version == "fraud-model-0.1.0"
    assert 0.0 <= evidence.supervised_risk <= 1.0
    assert 0.0 <= evidence.anomaly_risk <= 1.0