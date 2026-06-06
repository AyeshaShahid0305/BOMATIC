import re

from app.schemas.pipeline import E5Component, E5ComponentArtifact

from .models import DesignSection

_COMPONENT_PATTERNS = [
    (r"\bfirewalls?\b", "Next-generation firewall", "security"),
    (r"\bcore switches?\b", "Layer 3 core switch", "network"),
    (r"\bdistribution switches?\b", "Distribution switch", "network"),
    (r"\baccess switches?\b", "48-port PoE+ access switch", "network"),
    (r"\brouters?\b", "Enterprise router", "network"),
    (r"\bwireless lan controllers?\b|\bwlan controllers?\b", "Wireless LAN controller", "network"),
    (r"\baccess points?\b|\baps?\b", "Wireless access point", "network"),
    (r"\bradius servers?\b", "RADIUS authentication server", "security"),
    (r"\bnetwork management\b|\bnms\b", "Network management server", "software"),
]


def _quantity_near_match(text: str, match: re.Match) -> float:
    prefix = text[max(0, match.start() - 20):match.start()]
    quantity_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:x|units?\s+of\s+)?\s*$", prefix, re.IGNORECASE)
    return float(quantity_match.group(1)) if quantity_match else 1.0


def extract_components(
    hld_sections: list[DesignSection],
    lld_sections: list[DesignSection],
) -> E5ComponentArtifact:
    found: dict[str, E5Component] = {}

    for section in [*hld_sections, *lld_sections]:
        for pattern, description, category in _COMPONENT_PATTERNS:
            match = re.search(pattern, section.content, re.IGNORECASE)
            if not match:
                continue
            component = found.get(description)
            if component is None:
                component = E5Component(
                    description=description,
                    quantity=_quantity_near_match(section.content, match),
                    category=category,
                    source_sections=[section.id],
                )
                found[description] = component
            elif section.id not in component.source_sections:
                component.source_sections.append(section.id)

    all_sections = [*hld_sections, *lld_sections]
    if not found and all_sections:
        found["Enterprise network switch"] = E5Component(
            description="Enterprise network switch",
            category="network",
            source_sections=[all_sections[0].id],
        )

    return E5ComponentArtifact(components=list(found.values()))
