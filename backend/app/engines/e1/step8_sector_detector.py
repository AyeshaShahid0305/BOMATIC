import re

# Method A: client name substring → sector
_CLIENT_NAME_MAP: list[tuple[str, str]] = [
    # Banking / Finance
    ("bank", "banking"),
    ("finance", "banking"),
    ("financial", "banking"),
    ("investment", "banking"),
    ("capital", "banking"),
    ("insurance", "banking"),
    ("riyad", "banking"),
    ("rajhi", "banking"),
    ("al rajhi", "banking"),
    ("samba", "banking"),
    ("bsf", "banking"),
    ("alinma", "banking"),
    ("snb", "banking"),
    # Oil & Gas / Energy
    ("aramco", "oil_and_gas"),
    ("saudi aramco", "oil_and_gas"),
    ("sabic", "petrochemical"),
    ("chemanol", "petrochemical"),
    ("yanbu", "petrochemical"),
    ("petrochemical", "petrochemical"),
    ("refinery", "oil_and_gas"),
    ("upstream", "oil_and_gas"),
    ("downstream", "oil_and_gas"),
    ("aramco digital", "oil_and_gas"),
    # Government
    ("ministry", "government"),
    ("وزارة", "government"),
    ("emara", "government"),
    ("municipality", "government"),
    ("national center", "government"),
    ("national centre", "government"),
    ("directorate", "government"),
    ("authority", "government"),
    ("general authority", "government"),
    ("ncd", "government"),
    ("sdaia", "government"),
    ("zatca", "government"),
    ("nca", "government"),
    # Healthcare
    ("hospital", "healthcare"),
    ("clinic", "healthcare"),
    ("health", "healthcare"),
    ("medical", "healthcare"),
    ("kfshrc", "healthcare"),
    ("ngha", "healthcare"),
    ("moh", "healthcare"),
    # Hospitality / Real Estate
    ("hotel", "hospitality"),
    ("resort", "hospitality"),
    ("hospitality", "hospitality"),
    ("diriyah", "hospitality"),
    ("neom", "hospitality"),
    ("red sea", "hospitality"),
    ("sindalah", "hospitality"),
    ("roshn", "hospitality"),
    # Telecom
    ("stc", "telecom"),
    ("mobily", "telecom"),
    ("zain", "telecom"),
    ("telecom", "telecom"),
    ("telecommunications", "telecom"),
    ("mvno", "telecom"),
    # Education
    ("university", "education"),
    ("college", "education"),
    ("school", "education"),
    ("education", "education"),
    ("kau", "education"),
    ("ksu", "education"),
    ("kfupm", "education"),
]

# Method B: text keyword regex → sector (pattern, sector, weight)
_TEXT_PATTERNS: list[tuple[re.Pattern, str, float]] = [
    (re.compile(r"\b(core\s+banking|ATM|swift|pci\s+dss|card\s+processing|payment\s+gateway|retail\s+banking|credit\s+facility)\b", re.IGNORECASE), "banking", 0.85),
    (re.compile(r"\b(upstream|downstream|refinery|drilling|pipeline|FEED|EPC|brownfield|greenfield|wellhead|reservoir|SCADA\s+oil|gas\s+plant)\b", re.IGNORECASE), "oil_and_gas", 0.85),
    (re.compile(r"\b(petrochemical|polymer|ethylene|methanol|olefin|cracker|fertilizer)\b", re.IGNORECASE), "petrochemical", 0.85),
    (re.compile(r"\b(e-government|etimad|government\s+portal|citizen\s+service|national\s+portal|ministry\s+of|musaned|absher)\b", re.IGNORECASE), "government", 0.80),
    (re.compile(r"\b(hospital|clinic|PACS|HIS|EMR|patient\s+record|healthcare|medical\s+device|radiology|pharmacy\s+system)\b", re.IGNORECASE), "healthcare", 0.85),
    (re.compile(r"\b(hotel|resort|guest\s+room|IPTV|PMS|key\s+card|property\s+management|hospitality\s+system|front\s+desk)\b", re.IGNORECASE), "hospitality", 0.85),
    (re.compile(r"\b(BSS|OSS|core\s+network|RAN|5G|spectrum|subscriber|MVNO|roaming|billing\s+system|telecom)\b", re.IGNORECASE), "telecom", 0.85),
    (re.compile(r"\b(learning\s+management|LMS|student\s+information|campus\s+network|e-learning|academic)\b", re.IGNORECASE), "education", 0.80),
]

# Method C: referenced standard → sector
_STANDARD_SECTOR_MAP: dict[str, tuple[str, float]] = {
    "SAMA":     ("banking",     0.95),
    "SAMA CSF": ("banking",     0.95),
    "CBAHI":    ("healthcare",  0.95),
    "CBAHI SFS":("healthcare",  0.95),
    "CITC":     ("telecom",     0.95),
    "SACS":     ("oil_and_gas", 0.90),
    "SAES":     ("oil_and_gas", 0.90),
    "SAEP":     ("oil_and_gas", 0.90),
    "GI-":      ("oil_and_gas", 0.90),
    "CAP-":     ("oil_and_gas", 0.90),
    "NCA":      ("government",  0.80),
    "NCA ECC":  ("government",  0.85),
    "PDPL":     ("government",  0.70),
    "ADHICS":   ("healthcare",  0.90),
    "MOH":      ("healthcare",  0.85),
    "NESA":     ("government",  0.75),
}


def detect_sector(client_name: str, texts: dict[str, str]) -> dict:
    combined_text = " ".join(texts.values())
    client_lower = client_name.lower()

    # Method A: client name lookup
    for substring, sector in _CLIENT_NAME_MAP:
        if substring in client_lower:
            return {
                "sector": sector,
                "confidence": 0.92,
                "method": "client_lookup",
                "evidence": [f"client name contains '{substring}'"],
            }

    # Method C: standard reference in text (run before text keyword scan — higher precision)
    for standard, (sector, confidence) in _STANDARD_SECTOR_MAP.items():
        if standard.lower() in combined_text.lower():
            return {
                "sector": sector,
                "confidence": confidence,
                "method": "standard_reference",
                "evidence": [f"referenced standard '{standard}' implies {sector}"],
            }

    # Method B: content keyword regex scan — collect all hits and pick highest-scoring sector
    sector_scores: dict[str, tuple[float, list[str]]] = {}
    for pattern, sector, weight in _TEXT_PATTERNS:
        matches = pattern.findall(combined_text)
        if matches:
            current_score, current_evidence = sector_scores.get(sector, (0.0, []))
            # More hits → higher confidence, capped at 0.88
            new_score = min(0.88, weight + len(matches) * 0.01)
            sector_scores[sector] = (
                max(current_score, new_score),
                current_evidence + [m if isinstance(m, str) else m[0] for m in matches[:3]],
            )

    if sector_scores:
        best_sector = max(sector_scores, key=lambda s: sector_scores[s][0])
        score, evidence = sector_scores[best_sector]
        return {
            "sector": best_sector,
            "confidence": round(score, 2),
            "method": "content_keywords",
            "evidence": evidence,
        }

    return {
        "sector": "general",
        "confidence": 0.3,
        "method": "default",
        "evidence": [],
    }
