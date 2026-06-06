# Sector → ordered list of applicable framework names.
# NCA_ECC2 and ISO_27001 are always present as the minimum baseline.
_SECTOR_FRAMEWORK_MAP: dict[str, list[str]] = {
    "banking":       ["SAMA_CSF", "NCA_ECC2", "ISO_27001"],
    "oil_and_gas":   ["SACS", "NCA_ECC2", "ISO_27001"],
    "petrochemical": ["SACS", "NCA_ECC2", "ISO_27001"],
    "government":    ["DGCL", "NCA_ECC2", "ISO_27001"],
    "healthcare":    ["NCA_ECC2", "ISO_27001"],
    "telecom":       ["NCA_ECC2", "ISO_27001"],
    "hospitality":   ["NCA_ECC2", "ISO_27001"],
    "education":     ["NCA_ECC2", "ISO_27001"],
    "general":       ["NCA_ECC2", "ISO_27001"],
}

_ARABIC_LANGUAGE_FRAMEWORKS: dict[str, list[str]] = {
    "government": ["DGCL"],
    "oil_and_gas": ["SACS"],
    "petrochemical": ["SACS"],
    "general": ["DGCL", "SACS"],
}

# Substrings found in related_standards → canonical framework name
_STANDARD_TO_FRAMEWORK: list[tuple[str, str]] = [
    ("SAMA",     "SAMA_CSF"),
    ("DGCL",     "DGCL"),
    ("SACS",     "SACS"),
    ("NCA ECC",  "NCA_ECC2"),
    ("NCA",      "NCA_ECC2"),
    ("ISO 27001", "ISO_27001"),
    ("ISO27001",  "ISO_27001"),
]

_BASELINE = {"NCA_ECC2", "ISO_27001"}


def select_frameworks(
    sector: str,
    related_standards: list[str],
    language: str = "english",
) -> list[str]:
    base = list(_SECTOR_FRAMEWORK_MAP.get(sector, list(_BASELINE)))

    seen: set[str] = set(base)
    result: list[str] = list(base)

    # Add any framework implied by explicitly referenced standards
    for standard in related_standards:
        for substring, framework in _STANDARD_TO_FRAMEWORK:
            if substring.lower() in standard.lower() and framework not in seen:
                result.append(framework)
                seen.add(framework)
                break

    if language.lower().startswith("ar"):
        for framework in _ARABIC_LANGUAGE_FRAMEWORKS.get(sector, _ARABIC_LANGUAGE_FRAMEWORKS["general"]):
            if framework not in seen:
                result.append(framework)
                seen.add(framework)

    # Guarantee baseline is always present
    for fw in _BASELINE:
        if fw not in seen:
            result.append(fw)

    return result
