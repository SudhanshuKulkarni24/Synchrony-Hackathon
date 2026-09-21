from app.features.builder import FEATURE_NAMES, FEATURE_SCHEMA_VERSION, build_features


def test_feature_builder_has_stable_schema_and_defaults() -> None:
    vector = build_features({})

    assert vector.schema_version == FEATURE_SCHEMA_VERSION
    assert tuple(vector.as_dict()) == FEATURE_NAMES
    assert vector.as_dict()["identity_match_score"] == 1.0
    assert vector.as_dict()["is_new_device"] == 0.0


def test_feature_builder_matches_live_request_fields() -> None:
    vector = build_features(
        {
            "applications_last_24h": 5,
            "is_new_device": True,
            "identity_match_score": 0.72,
            "device_account_count": 3,
            "payment_account_count": 2,
            "ip_risk_score": 0.4,
        }
    )

    assert vector.as_dict() == {
        "applications_last_24h": 5.0,
        "is_new_device": 1.0,
        "identity_match_score": 0.72,
        "device_account_count": 3.0,
        "payment_account_count": 2.0,
        "ip_risk_score": 0.4,
    }


def test_synthetic_dataset_is_reproducible_and_time_ordered() -> None:
    from ml.data.generate_dataset import generate_rows

    first_rows = generate_rows(row_count=20, seed=7)
    second_rows = generate_rows(row_count=20, seed=7)

    assert first_rows == second_rows
    assert [row["event_time"] for row in first_rows] == sorted(
        row["event_time"] for row in first_rows
    )
    assert {row["fraud_label"] for row in first_rows} == {0, 1}