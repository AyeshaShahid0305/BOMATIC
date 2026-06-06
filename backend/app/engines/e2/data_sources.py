import csv
import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)
_MAX_DATA_AGE_DAYS = 30


def load_records(path: Path) -> list[dict]:
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as source:
            return list(csv.DictReader(source))
    with path.open(encoding="utf-8") as source:
        data = json.load(source)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {path}.")
    return data


def load_mapping(path: Path) -> dict:
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as source:
            rows = list(csv.DictReader(source))
        rates = {
            str(row.get("currency") or row.get("code") or "").upper(): float(row["rate"])
            for row in rows
            if (row.get("currency") or row.get("code")) and row.get("rate")
        }
        return {"base_currency": "USD", "rates": rates}
    with path.open(encoding="utf-8") as source:
        data = json.load(source)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}.")
    return data


def warn_if_stale(path: Path, label: str, metadata: dict | None = None) -> None:
    timestamp = _metadata_timestamp(metadata or {})
    if timestamp is None:
        timestamp = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)

    age_days = (datetime.now(timezone.utc) - timestamp).days
    if age_days > _MAX_DATA_AGE_DAYS:
        logger.warning(
            "%s data source is stale: %s is %d days old (maximum %d days).",
            label,
            path,
            age_days,
            _MAX_DATA_AGE_DAYS,
        )


def _metadata_timestamp(metadata: dict) -> datetime | None:
    raw = metadata.get("updated") or metadata.get("last_updated")
    if not raw:
        return None
    try:
        parsed = date.fromisoformat(str(raw))
    except ValueError:
        return None
    return datetime(parsed.year, parsed.month, parsed.day, tzinfo=timezone.utc)
