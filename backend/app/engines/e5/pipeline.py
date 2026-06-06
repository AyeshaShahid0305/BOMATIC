from typing import Optional

from sqlalchemy.orm import Session

from app.config import get_settings

from .calculated_sections import apply_calculated_sections
from .cable_port_mapper import connections_as_dicts, map_cables_and_ports
from .models import DesignDocument
from .component_extractor import extract_components
from .sizing_calculator import calculate_sizing, sizing_as_dicts
from .step1_context_reader import read_context
from .step2_hld_generator import generate_hld
from .step3_lld_generator import generate_lld
from .step4_docx_writer import write_design_document
from .vlan_ip_allocator import allocate_vlans, allocations_as_dicts


def run_e5_pipeline(session_id: Optional[str], db: Session) -> dict:
    context = read_context(session_id, db)
    hld_sections = generate_hld(context)
    lld_sections = generate_lld(context, hld_sections)
    component_artifact = extract_components(hld_sections, lld_sections)
    settings = get_settings()
    sizing = calculate_sizing(component_artifact)
    vlan_allocations = allocate_vlans(
        component_artifact,
        base_vlan=settings.e5_base_vlan,
        base_subnet=settings.e5_base_subnet,
    )
    port_connections = map_cables_and_ports(component_artifact)
    apply_calculated_sections(
        hld_sections,
        lld_sections,
        sizing,
        vlan_allocations,
        port_connections,
    )

    doc = DesignDocument(
        project_name=context["project_name"],
        hld_sections=hld_sections,
        lld_sections=lld_sections,
        generated_from="e1" if context["has_e1_data"] else "blank",
    )

    output_path = write_design_document(doc)

    return {
        "output_file": output_path.name,
        "project_name": context["project_name"],
        "hld_section_count": len(hld_sections),
        "lld_section_count": len(lld_sections),
        "generated_from": doc.generated_from,
        "total_sections": len(hld_sections) + len(lld_sections),
        "component_artifact": component_artifact.model_dump(mode="json"),
        "components": component_artifact.model_dump(mode="json")["components"],
        "sizing": sizing_as_dicts(sizing),
        "vlan_allocations": allocations_as_dicts(vlan_allocations),
        "port_connections": connections_as_dicts(port_connections),
    }
