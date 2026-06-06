from .cable_port_mapper import PortConnection
from .models import DesignSection
from .sizing_calculator import SizingResult
from .vlan_ip_allocator import VlanAllocation


def _table(headers: list[str], rows: list[list[object]]) -> str:
    if not rows:
        return "No applicable components were identified."
    lines = [" | ".join(headers), " | ".join("---" for _ in headers)]
    lines.extend(" | ".join(str(value) for value in row) for row in rows)
    return "\n".join(lines)


def _replace_content(
    sections: list[DesignSection],
    titles: set[str],
    content: str,
) -> None:
    for section in sections:
        if section.title in titles:
            section.content = content


def apply_calculated_sections(
    hld_sections: list[DesignSection],
    lld_sections: list[DesignSection],
    sizing: list[SizingResult],
    vlans: list[VlanAllocation],
    connections: list[PortConnection],
) -> None:
    sizing_table = _table(
        ["Component", "Qty", "RU Each", "Total RU", "Watts Each", "Total Watts", "Ports Each", "Total Ports"],
        [
            [
                row.component,
                row.quantity,
                row.rack_units_each,
                row.total_rack_units,
                row.power_watts_each,
                row.total_power_watts,
                row.ports_each,
                row.total_ports,
            ]
            for row in sizing
        ],
    )
    totals = (
        f"\n\nCalculated totals: {sum(row.total_rack_units for row in sizing)} rack units, "
        f"{sum(row.total_power_watts for row in sizing)} watts, "
        f"{sum(row.total_ports for row in sizing)} ports."
    )
    _replace_content(
        hld_sections,
        {"Technology Stack", "Capacity & Sizing", "Sizing"},
        sizing_table + totals,
    )

    vlan_table = _table(
        ["Component", "VLAN", "Name", "Subnet", "Gateway"],
        [
            [row.component, row.vlan_id, row.vlan_name, row.subnet, row.gateway]
            for row in vlans
        ],
    )
    _replace_content(lld_sections, {"IP Address Scheme", "VLAN Design"}, vlan_table)

    port_table = _table(
        ["Source", "Source Port", "Destination", "Destination Port", "Cable", "Purpose"],
        [
            [
                row.source_device,
                row.source_port,
                row.destination_device,
                row.destination_port,
                row.cable_type,
                row.purpose,
            ]
            for row in connections
        ],
    )
    _replace_content(lld_sections, {"Cable & Port Mapping"}, port_table)
