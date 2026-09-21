import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


OUTPUT_COLUMNS = (
    "event_time",
    "applications_last_24h",
    "is_new_device",
    "identity_match_score",
    "device_account_count",
    "payment_account_count",
    "ip_risk_score",
    "fraud_label",
)


def generate_rows(row_count: int = 500, seed: int = 42) -> list[dict[str, object]]:
    generator = random.Random(seed)
    start_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows: list[dict[str, object]] = []

    for row_number in range(row_count):
        is_new_device = generator.random() < 0.25
        applications_last_24h = generator.randint(0, 8)
        identity_match_score = round(generator.uniform(0.45, 1.0), 3)
        device_account_count = generator.randint(1, 6)
        payment_account_count = generator.randint(1, 5)
        ip_risk_score = round(generator.uniform(0.0, 1.0), 3)
        fraud_label = int(
            applications_last_24h >= 5
            or (is_new_device and identity_match_score < 0.8)
            or device_account_count >= 4
            or payment_account_count >= 4
            or ip_risk_score >= 0.9
        )
        rows.append(
            {
                "event_time": (start_time + timedelta(hours=row_number)).isoformat(),
                "applications_last_24h": applications_last_24h,
                "is_new_device": int(is_new_device),
                "identity_match_score": identity_match_score,
                "device_account_count": device_account_count,
                "payment_account_count": payment_account_count,
                "ip_risk_score": ip_risk_score,
                "fraud_label": fraud_label,
            }
        )
    return rows


def write_dataset(output_path: Path, row_count: int = 500, seed: int = 42) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as dataset_file:
        writer = csv.DictWriter(dataset_file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(generate_rows(row_count=row_count, seed=seed))


if __name__ == "__main__":
    write_dataset(Path("ml/data/fraud_events.csv"))