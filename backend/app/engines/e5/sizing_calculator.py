import math
from dataclasses import asdict, dataclass

from app.schemas.pipeline import E5ComponentArtifact


@dataclass(frozen=True)
class SizingResult:
    component: str
    quantity: int
    rack_units_each: int
    total_rack_units: int
    power_watts_each: int
    total_power_watts: int
    ports_each: int
    total_ports: int


_PROFILES = [
    ("access switch", (1, 740, 48)),
    ("distribution switch", (1, 350, 48)),
    ("core switch", (2, 500, 48)),
    ("firewall", (1, 250, 16)),
    ("router", (1, 200, 8)),
    ("wireless lan controller", (1, 150, 8)),
    ("access point", (0, 30, 2)),
    ("server", (2, 600, 4)),
]
_DEFAULT_PROFILE = (1, 200, 24)


def _profile_for(description: str) -> tuple[int, int, int]:
    normalized = description.lower()
    for marker, profile in _PROFILES:
        if marker in normalized:
            return profile
    return _DEFAULT_PROFILE


def calculate_sizing(artifact: E5ComponentArtifact) -> list[SizingResult]:
    results = []
    for component in artifact.components:
        quantity = math.ceil(component.quantity)
        rack_units, power_watts, ports = _profile_for(component.description)
        results.append(
            SizingResult(
                component=component.description,
                quantity=quantity,
                rack_units_each=rack_units,
                total_rack_units=rack_units * quantity,
                power_watts_each=power_watts,
                total_power_watts=power_watts * quantity,
                ports_each=ports,
                total_ports=ports * quantity,
            )
        )
    return results


def sizing_as_dicts(results: list[SizingResult]) -> list[dict]:
    return [asdict(result) for result in results]
