import json
import re
from pathlib import Path

from .models import CatalogMatch, RFPLineItem

_CATALOG_PATH = Path(__file__).parent / "data" / "catalog.json"
_FUZZY_THRESHOLD = 0.30
_CATEGORY_BONUS = 0.15


def _tokens(text: str) -> set[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return set(text.split())


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _load_catalog() -> list[dict]:
    with open(_CATALOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def _score(rfp_item: RFPLineItem, product: dict) -> tuple[float, str]:
    # Exact: SKU found verbatim in the RFP description
    if product["sku"].lower() in rfp_item.description.lower():
        return 1.0, "exact"

    # Fuzzy: Jaccard over description tokens + catalog keywords
    rfp_tokens = _tokens(rfp_item.description)
    catalog_tokens = _tokens(product["product_name"])
    for kw in product.get("keywords", []):
        catalog_tokens |= _tokens(kw)

    score = _jaccard(rfp_tokens, catalog_tokens)

    # Small bonus when categories align
    if product.get("category", "").lower() == rfp_item.category.lower():
        score = min(1.0, score + _CATEGORY_BONUS)

    return score, "fuzzy"


def match_catalog(
    rfp_items: list[RFPLineItem],
    catalog_path: Path = _CATALOG_PATH,
) -> list[CatalogMatch]:
    catalog = _load_catalog() if catalog_path == _CATALOG_PATH else json.loads(catalog_path.read_text(encoding="utf-8"))
    results: list[CatalogMatch] = []

    for rfp_item in rfp_items:
        best_score = 0.0
        best_product: dict | None = None
        best_method = "unmatched"

        for product in catalog:
            score, method = _score(rfp_item, product)
            if score > best_score:
                best_score = score
                best_product = product
                best_method = method

        if best_product and best_score >= _FUZZY_THRESHOLD:
            results.append(CatalogMatch(
                rfp_item=rfp_item,
                sku=best_product["sku"],
                product_name=best_product["product_name"],
                vendor=best_product["vendor"],
                unit_price=best_product["unit_price"],
                match_score=round(best_score, 4),
                match_method=best_method,
            ))
        else:
            results.append(CatalogMatch(
                rfp_item=rfp_item,
                sku="",
                product_name="",
                vendor="",
                unit_price=0.0,
                match_score=0.0,
                match_method="unmatched",
            ))

    return results


if __name__ == "__main__":
    from app.engines.e2.models import RFPLineItem

    samples = [
        RFPLineItem(description="Cisco ASA 5516-X firewall with FirePOWER", quantity=2, unit="units", category="security", raw_text="", confidence=0.9),
        RFPLineItem(description="48-port PoE+ switch with 10G uplinks", quantity=10, unit="units", category="network", raw_text="", confidence=0.85),
        RFPLineItem(description="DNA Advantage license 3-year subscription", quantity=10, unit="licenses", category="license", raw_text="", confidence=0.8),
        RFPLineItem(description="unmanaged desktop hub", quantity=1, unit="units", category="hardware", raw_text="", confidence=0.6),
    ]

    for match in match_catalog(samples):
        print(f"[{match.match_method:<10}] {match.rfp_item.description[:45]:<45} -> {match.sku or '(no match)'}  score={match.match_score}")
