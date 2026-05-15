from .models import GBBResult

# Multipliers derived from playbook §7.5 midpoints:
#   Good  = 1.0      (baseline — meets RFP minimums)
#   Better = 1.325   (midpoint of 25–40% above Good)
#   Best   = 1.8     (midpoint of 60–100% above Good)
_TIERS: dict[str, tuple[float, str]] = {
    "good": (
        1.0,
        "Meets RFP minimums. Entry-level devices, standard support tier.",
    ),
    "better": (
        1.325,
        "Adds resilience, advanced features, and a higher support tier. "
        "Recommended option.",
    ),
    "best": (
        1.8,
        "Full-stack with automation, zero-trust, and premium multi-year support. "
        "Highest lifecycle TCO benefit.",
    ),
}


def calculate_gbb(base_price: float, tier: str) -> GBBResult:
    tier = tier.lower()
    if tier not in _TIERS:
        raise ValueError(f"Unknown tier '{tier}'. Must be one of: {list(_TIERS)}")
    multiplier, description = _TIERS[tier]
    return GBBResult(
        tier=tier,
        multiplier=multiplier,
        adjusted_price=round(base_price * multiplier, 2),
        description=description,
    )


if __name__ == "__main__":
    base = 100_000.0
    print(f"Base price: {base:,.2f}\n")
    for tier in ("good", "better", "best"):
        r = calculate_gbb(base, tier)
        print(f"[{r.tier.upper()}]")
        print(f"  Multiplier:     {r.multiplier}")
        print(f"  Adjusted price: {r.adjusted_price:,.2f}")
        print(f"  Description:    {r.description}")
        print()
