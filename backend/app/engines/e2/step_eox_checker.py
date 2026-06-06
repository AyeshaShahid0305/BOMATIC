"""
EoX (End-of-Life/End-of-Sale) checker for matched SKUs.

check_eox(matched_skus) -> list[dict]

Returns a list of EoX warning dicts for any matched SKU found in the EoX list.
"""

from datetime import date
from pathlib import Path

from app.config import get_settings

from .data_sources import load_records

_EOX_PATH = Path(__file__).parent / "data" / "eox.json"


def _load_eox() -> dict[str, dict]:
    """Load EoX data as a dict keyed by SKU (uppercase)."""
    try:
        records = load_records(Path(get_settings().eox_data_source))
        return {r["sku"].upper(): r for r in records}
    except Exception:
        return {}


def check_eox(matched_skus: list[str]) -> list[dict]:
    """
    Check a list of SKUs against the EoX database.

    Args:
        matched_skus: list of SKU strings from the catalog match results.

    Returns:
        list of dicts, one per EoX hit:
        {
            "sku": str,
            "product_name": str,
            "end_of_sale": str,
            "end_of_support": str,
            "replacement_sku": str,
            "is_end_of_sale": bool,
            "is_end_of_support": bool
        }
    """
    eox_db = _load_eox()
    today = date.today().isoformat()
    warnings = []

    for sku in matched_skus:
        record = eox_db.get(sku.upper())
        if not record:
            continue

        eos = record.get("end_of_sale", "")
        eol = record.get("end_of_support", "")

        warnings.append({
            "sku": sku,
            "product_name": record.get("product_name", ""),
            "end_of_sale": eos,
            "end_of_support": eol,
            "replacement_sku": record.get("replacement_sku", ""),
            "is_end_of_sale": bool(eos and eos <= today),
            "is_end_of_support": bool(eol and eol <= today),
        })

    return warnings
