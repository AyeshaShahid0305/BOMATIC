import math
from dataclasses import asdict, dataclass

from app.schemas.pipeline import E5ComponentArtifact


@dataclass(frozen=True)
class PortConnection:
    source_device: str
    source_port: str
    destination_device: str
    destination_port: str
    cable_type: str
    purpose: str


def _tier(description: str) -> str | None:
    normalized = description.lower()
    if "access switch" in normalized:
        return "ACCESS"
    if "distribution switch" in normalized:
        return "DISTRIBUTION"
    if "core switch" in normalized:
        return "CORE"
    return None


def _devices(artifact: E5ComponentArtifact) -> dict[str, list[str]]:
    tiers = {"ACCESS": [], "DISTRIBUTION": [], "CORE": []}
    counters = {tier: 0 for tier in tiers}
    for component in artifact.components:
        tier = _tier(component.description)
        if not tier:
            continue
        for _ in range(math.ceil(component.quantity)):
            counters[tier] += 1
            tiers[tier].append(f"{tier}-{counters[tier]:02d}")
    return tiers


def _connect_tiers(
    sources: list[str],
    destinations: list[str],
    purpose: str,
) -> list[PortConnection]:
    if not sources or not destinations:
        return []

    connections = []
    destination_port_counts = {device: 0 for device in destinations}
    links_per_source = min(2, len(destinations))
    for source_index, source in enumerate(sources):
        for link_index in range(links_per_source):
            destination = destinations[(source_index + link_index) % len(destinations)]
            destination_port_counts[destination] += 1
            connections.append(
                PortConnection(
                    source_device=source,
                    source_port=f"TenGigabitEthernet1/1/{link_index + 1}",
                    destination_device=destination,
                    destination_port=(
                        f"TenGigabitEthernet1/0/{destination_port_counts[destination]}"
                    ),
                    cable_type="OM4 multimode fiber",
                    purpose=purpose,
                )
            )
    return connections


def map_cables_and_ports(artifact: E5ComponentArtifact) -> list[PortConnection]:
    tiers = _devices(artifact)
    return [
        *_connect_tiers(
            tiers["ACCESS"],
            tiers["DISTRIBUTION"],
            "Access-to-distribution uplink",
        ),
        *_connect_tiers(
            tiers["DISTRIBUTION"],
            tiers["CORE"],
            "Distribution-to-core uplink",
        ),
    ]


def connections_as_dicts(connections: list[PortConnection]) -> list[dict]:
    return [asdict(connection) for connection in connections]
