import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engines.e5.cable_port_mapper import map_cables_and_ports
from app.engines.e5.calculated_sections import apply_calculated_sections
from app.engines.e5.models import DesignSection
from app.engines.e5.sizing_calculator import calculate_sizing
from app.engines.e5.vlan_ip_allocator import allocate_vlans
from app.schemas.pipeline import E5Component, E5ComponentArtifact


def _artifact() -> E5ComponentArtifact:
    return E5ComponentArtifact(
        components=[
            E5Component(description="48-port PoE+ access switch", quantity=2),
            E5Component(description="Distribution switch", quantity=2),
            E5Component(description="Layer 3 core switch", quantity=2),
        ]
    )


def test_sizing_calculator_returns_expected_capacity():
    results = calculate_sizing(_artifact())

    access = results[0]
    assert access.quantity == 2
    assert access.total_rack_units == 2
    assert access.total_power_watts == 1480
    assert access.total_ports == 96


def test_vlan_allocator_uses_configured_start_and_sequential_subnets():
    allocations = allocate_vlans(
        _artifact(),
        base_vlan=200,
        base_subnet="172.16.0.0/16",
    )

    assert [item.vlan_id for item in allocations] == [200, 201, 202]
    assert [item.subnet for item in allocations] == [
        "172.16.0.0/24",
        "172.16.1.0/24",
        "172.16.2.0/24",
    ]
    assert allocations[0].gateway == "172.16.0.1"


def test_cable_port_mapper_builds_access_distribution_core_uplinks():
    connections = map_cables_and_ports(_artifact())

    assert len(connections) == 8
    assert sum("Access-to-distribution" in item.purpose for item in connections) == 4
    assert sum("Distribution-to-core" in item.purpose for item in connections) == 4
    assert connections[0].source_device == "ACCESS-01"
    assert connections[0].destination_device == "DISTRIBUTION-01"


def test_calculated_outputs_replace_generated_section_prose():
    artifact = _artifact()
    hld = [
        DesignSection(
            id="HLD-004",
            title="Technology Stack",
            content="AI-generated sizing placeholder.",
            level="HLD",
            order=4,
        )
    ]
    lld = [
        DesignSection(
            id="LLD-001",
            title="IP Address Scheme",
            content="AI-generated IP placeholder.",
            level="LLD",
            order=1,
        ),
        DesignSection(
            id="LLD-007",
            title="VLAN Design",
            content="AI-generated VLAN placeholder.",
            level="LLD",
            order=7,
        ),
        DesignSection(
            id="LLD-019",
            title="Cable & Port Mapping",
            content="AI-generated cable placeholder.",
            level="LLD",
            order=19,
        ),
    ]

    apply_calculated_sections(
        hld,
        lld,
        calculate_sizing(artifact),
        allocate_vlans(artifact),
        map_cables_and_ports(artifact),
    )

    assert "Total Watts" in hld[0].content
    assert "10.0.0.0/24" in lld[0].content
    assert lld[0].content == lld[1].content
    assert "ACCESS-01" in lld[2].content
