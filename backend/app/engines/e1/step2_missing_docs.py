import re

from .models import MissingDocument

# ---------------------------------------------------------------------------
# Pattern groups compiled at module load time — RFP_Compliance_Patterns.md §4
# Each entry: (compiled_re, severity)
# ---------------------------------------------------------------------------

# §4.1 Internal cross-references
# Annex/Appendix → critical (may contain mandatory technical scope)
# Schedule/Attachment/Exhibit → high (commercial terms)
# Section/clause → high (may reference a separately-delivered annex)
INTERNAL_REF_PATTERNS: list[tuple] = [
    (re.compile(r"(?:refer\s+to|as\s+per|see|in\s+accordance\s+with)\s+(?:Annex|Appendix)\s+[A-Z0-9]+", re.IGNORECASE), "critical"),
    (re.compile(r"(?:refer\s+to|as\s+per|see|in\s+accordance\s+with)\s+(?:Attachment|Schedule|Exhibit)\s+[A-Z0-9]+", re.IGNORECASE), "high"),
    (re.compile(r"(?:paragraph|section|clause)\s+\d+[\.\d]*", re.IGNORECASE), "high"),
]

# §4.2 Aramco engineering standards — always critical
ARAMCO_STD_PATTERNS: list[tuple] = [
    (re.compile(r"SACS-\d{3}",       re.IGNORECASE), "critical"),
    (re.compile(r"SAES-[A-Z]-\d{3}", re.IGNORECASE), "critical"),
    (re.compile(r"SAEP-\d+",         re.IGNORECASE), "critical"),
    (re.compile(r"GI-\d+\.\d+",      re.IGNORECASE), "critical"),
    (re.compile(r"CAP-\d+",          re.IGNORECASE), "critical"),
    (re.compile(r"SAMSS-\d+",        re.IGNORECASE), "critical"),
]

# §4.3 International / external standards — medium (can be sourced publicly)
INTL_STD_PATTERNS: list[tuple] = [
    (re.compile(r"ISO\s+\d{4,5}(?:[-:]\d{4})?", re.IGNORECASE), "medium"),
    (re.compile(r"NIST\s+(?:SP\s+)?800-\d+",     re.IGNORECASE), "medium"),
    (re.compile(r"NCA\s+ECC",                     re.IGNORECASE), "medium"),
    (re.compile(r"NFPA\s+\d+",                    re.IGNORECASE), "medium"),
    (re.compile(r"API\s+\d+",                     re.IGNORECASE), "medium"),
    (re.compile(r"SAMA\s+CSF",                    re.IGNORECASE), "medium"),
    (re.compile(r"IEC\s+\d{5}",                   re.IGNORECASE), "medium"),
    (re.compile(r"TIA-\d+",                       re.IGNORECASE), "medium"),
]

# §4.4 Generic reference language — low (may be informational)
GENERIC_REF_PATTERNS: list[tuple] = [
    (re.compile(r"(?:the\s+attached|enclosed\s+herewith|accompanying\s+document)", re.IGNORECASE), "low"),
    (re.compile(r"(?:as\s+defined\s+in|pursuant\s+to|subject\s+to\s+the\s+provisions\s+of)", re.IGNORECASE), "low"),
]

_ALL_GROUPS = [
    ARAMCO_STD_PATTERNS,    # highest severity first so dedup keeps critical over lower
    INTERNAL_REF_PATTERNS,
    INTL_STD_PATTERNS,
    GENERIC_REF_PATTERNS,
]

_SEVERITY_RANK = {"critical": 3, "high": 2, "medium": 1, "low": 0}
_SEVERITY_SORT = {"critical": 0, "high": 1, "medium": 2, "low": 3}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_ref(ref: str) -> str:
    ref = ref.lower().strip()
    ref = re.sub(r"[^\w\s-]", "", ref)   # keep word chars, spaces, hyphens
    return " ".join(ref.split())


def _ref_present_in_package(ref: str, available_files: list[str]) -> bool:
    norm = _normalize_ref(ref)
    normalized_files = [_normalize_ref(f) for f in available_files]

    for fname in normalized_files:
        if norm in fname:
            return True

    # Try compact variations: "annex a" → "annexa", "annex_a", "annex-a"
    words = norm.split()
    if len(words) >= 2:
        variants = ["".join(words), "_".join(words), "-".join(words)]
        for fname in normalized_files:
            if any(v in fname for v in variants):
                return True

    return False


def _suggest_action(severity: str) -> str:
    return {
        "critical": "Request from client before proceeding",
        "high":     "Request from client or verify scope is not affected",
        "medium":   "Source publicly if not received within 48 hours",
        "low":      "Verify if document is required or informational",
    }[severity]


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def _extract_references(text: str, source_file: str) -> list[dict]:
    seen: dict[str, dict] = {}  # normalized_ref -> best entry so far

    for group in _ALL_GROUPS:
        for pattern, severity in group:
            for match in pattern.finditer(text):
                matched = match.group(0).strip()
                norm = _normalize_ref(matched)

                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end].replace("\n", " ").strip()

                if norm not in seen or _SEVERITY_RANK[severity] > _SEVERITY_RANK[seen[norm]["severity"]]:
                    seen[norm] = {
                        "ref": matched,
                        "source_file": source_file,
                        "severity": severity,
                        "context": context,
                    }

    return list(seen.values())


def detect_missing_documents(
    classified_files: list[dict],
    extracted_texts: dict[str, str],
) -> list[MissingDocument]:
    available_filenames = [f["filename"] for f in classified_files]
    seen: dict[tuple, MissingDocument] = {}  # (norm_ref, source_file) -> best entry

    for filename, text in extracted_texts.items():
        for ref in _extract_references(text, filename):
            if _ref_present_in_package(ref["ref"], available_filenames):
                continue
            key = (_normalize_ref(ref["ref"]), filename)
            if key not in seen or _SEVERITY_RANK[ref["severity"]] > _SEVERITY_RANK[seen[key].severity]:
                seen[key] = MissingDocument(
                    referenced_doc=ref["ref"],
                    referenced_in=filename,
                    page=0,
                    line=ref["context"],
                    severity=ref["severity"],
                    action=_suggest_action(ref["severity"]),
                )

    results = list(seen.values())
    results.sort(key=lambda m: _SEVERITY_SORT[m.severity])
    return results
