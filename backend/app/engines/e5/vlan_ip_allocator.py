import ipaddress
import re
from dataclasses import asdict, dataclass

from app.schemas.pipeline import E5ComponentArtifact


@dataclass(frozen=True)
class VlanAllocation:
    component: str
    vlan_id: int
    vlan_name: str
    subnet: str
    gateway: str


def _vlan_name(description: str) -> str:
    name = re.sub(r"[^A-Z0-9]+", "-", description.upper()).strip("-")
    return name[:32] or "COMPONENT"


def allocate_vlans(
    artifact: E5ComponentArtifact,
    base_vlan: int = 100,
    base_subnet: str = "10.0.0.0/8",
) -> list[VlanAllocation]:
    if not 1 <= base_vlan <= 4094:
        raise ValueError("base_vlan must be between 1 and 4094")

    network = ipaddress.ip_network(base_subnet, strict=False)
    if network.version != 4 or network.prefixlen > 24:
        raise ValueError("base_subnet must be an IPv4 network with /24 or larger capacity")

    allocations = []
    subnets = network.subnets(new_prefix=24)
    for index, component in enumerate(artifact.components):
        vlan_id = base_vlan + index
        if vlan_id > 4094:
            raise ValueError("component count exceeds the available VLAN ID range")
        try:
            subnet = next(subnets)
        except StopIteration as exc:
            raise ValueError("component count exceeds the available subnet range") from exc
        allocations.append(
            VlanAllocation(
                component=component.description,
                vlan_id=vlan_id,
                vlan_name=_vlan_name(component.description),
                subnet=str(subnet),
                gateway=str(subnet.network_address + 1),
            )
        )
    return allocations


def allocations_as_dicts(allocations: list[VlanAllocation]) -> list[dict]:
    return [asdict(allocation) for allocation in allocations]
