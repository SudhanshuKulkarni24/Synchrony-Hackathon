from dataclasses import dataclass
from typing import Mapping


FEATURE_SCHEMA_VERSION = "features-1.0.0"
FEATURE_NAMES = (
    "applications_last_24h",
    "is_new_device",
    "identity_match_score",
    "device_account_count",
    "payment_account_count",
    "ip_risk_score",
)


@dataclass(frozen=True)
class FeatureVector:
    values: tuple[float, ...]
    schema_version: str = FEATURE_SCHEMA_VERSION

    def as_dict(self) -> dict[str, float]:
        return dict(zip(FEATURE_NAMES, self.values, strict=True))


def build_features(signals: Mapping[str, object]) -> FeatureVector:
    values = (
        float(signals.get("applications_last_24h", 0)),
        float(bool(signals.get("is_new_device", False))),
        float(signals.get("identity_match_score", 1.0)),
        float(signals.get("device_account_count", 1)),
        float(signals.get("payment_account_count", 1)),
        float(signals.get("ip_risk_score", 0.0)),
    )
    return FeatureVector(values=values)