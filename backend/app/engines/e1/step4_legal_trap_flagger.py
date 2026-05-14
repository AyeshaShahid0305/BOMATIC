import re

from .models import RiskFlag

# ---------------------------------------------------------------------------
# Date / time patterns — §8.1 and §8.2
# ---------------------------------------------------------------------------

DATE_PATTERNS: list[re.Pattern] = [
    # DD-Mon-YYYY abbreviated (e.g. 15-Jun-2026)
    re.compile(
        r"\b\d{1,2}[-\s](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[-\s]\d{4}\b",
        re.IGNORECASE,
    ),
    # DD-Month-YYYY full (e.g. 15-March-2026)
    re.compile(
        r"\b\d{1,2}[-\s](?:January|February|March|April|May|June|July|August"
        r"|September|October|November|December)[-\s]\d{4}\b",
        re.IGNORECASE,
    ),
    # DD/MM/YYYY
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b"),
    # Month DD YYYY (e.g. March 15 2026 or March 15th 2026)
    re.compile(
        r"\b(?:January|February|March|April|May|June|July|August|September"
        r"|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4}\b",
        re.IGNORECASE,
    ),
]

_TIME_PATTERN: re.Pattern = re.compile(
    r"\b\d{1,2}:\d{2}\s*(?:AST|GST|GMT|UTC(?:[+-]\d+)?|AM|PM)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# §5.1 — CRITICAL: Automatic disqualification triggers (9 patterns)
# ---------------------------------------------------------------------------

CRITICAL_PATTERNS: list[tuple] = [
    (
        re.compile(
            r"\b(?:bid\s+bond|bank\s+guarantee|performance\s+bond)\b"
            r".*(?:required\b|mandatory\b|shall\s+submit|disqualif)",
            re.IGNORECASE,
        ),
        "bid_bond",
    ),
    (
        re.compile(
            r"\b(?:closing\s+date|submission\s+deadline|latest\s+date\s+for\s+submission)\b",
            re.IGNORECASE,
        ),
        "submission_deadline",
    ),
    (
        re.compile(
            r"\b(?:sealed\s+envelope|original\s+and\s+\d+\s+copies|hardcopy\s+submission)\b",
            re.IGNORECASE,
        ),
        "sealed_submission",
    ),
    (
        re.compile(
            r"\b(?:naming\s+convention|file\s+format|shall\s+be\s+submitted\s+in)\b",
            re.IGNORECASE,
        ),
        "naming_convention",
    ),
    (
        re.compile(
            r"\b(?:prequalified\s+vendors?\s+only|restricted\s+to|eligible\s+bidders?)\b",
            re.IGNORECASE,
        ),
        "bidder_eligibility",
    ),
    (
        re.compile(
            r"\b(?:conflict\s+of\s+interest\s+declaration|anti-bribery|non-collusion)\b",
            re.IGNORECASE,
        ),
        "conflict_of_interest",
    ),
    (
        re.compile(
            r"\b(?:bid\s+(?:validity|shall\s+remain\s+valid)"
            r"|validity\s+period\s+of\s+(?:the\s+)?(?:bid|offer|proposal))\b"
            r".*\b\d+\s+(?:day|week|month)s?\b",
            re.IGNORECASE,
        ),
        "bid_validity",
    ),
    (
        re.compile(
            r"\b(?:(?:all\s+)?(?:documents?|documentation|bids?)\s+(?:shall|must)\s+be"
            r"\s+(?:submitted\s+)?in\s+(?:English|Arabic)"
            r"|language\s+of\s+(?:the\s+)?(?:bid|submission|proposal|contract)\s+shall\s+be)\b",
            re.IGNORECASE,
        ),
        "language_requirement",
    ),
    (
        re.compile(
            r"\b(?:power\s+of\s+attorney|authorized\s+signatory|notarized)\b"
            r".*\b(?:required|mandatory|shall)\b",
            re.IGNORECASE,
        ),
        "authorized_signatory",
    ),
]

# ---------------------------------------------------------------------------
# §5.2 — HIGH: Discretionary rejection triggers (9 patterns)
# ---------------------------------------------------------------------------

HIGH_PATTERNS: list[tuple] = [
    (
        re.compile(
            r"\b(?:incomplete\s+submission|missing\s+document|partial\s+response)\b"
            r".*\b(?:may\s+be\s+rejected|reserves?\s+the\s+right)\b",
            re.IGNORECASE,
        ),
        "incomplete_submission",
    ),
    (
        re.compile(
            r"\b(?:minimum\s+score|threshold|passing\s+mark)\b.*\b(?:\d+%|\d+\s+points)\b",
            re.IGNORECASE,
        ),
        "min_technical_score",
    ),
    (
        re.compile(
            r"\bminimum\s+\d+\s+years?\s+(?:of\s+)?experience"
            r"|\bdemonstrated\s+track\s+record"
            r"|\bsimilar\s+projects?\s+required\b",
            re.IGNORECASE,
        ),
        "min_experience",
    ),
    (
        re.compile(
            r"\b(?:reference\s+(?:project|letter|site|list)"
            r"|similar\s+(?:project|scope|work))\b"
            r".*\b(?:shall\s+(?:be\s+)?provid|required|mandatory)\b",
            re.IGNORECASE,
        ),
        "similar_project_refs",
    ),
    (
        re.compile(
            r"\b(?:annual\s+turnover|financial\s+capability|audited\s+financial\s+statements?)\b",
            re.IGNORECASE,
        ),
        "financial_capability",
    ),
    (
        re.compile(
            r"\b(?:insurance\s+(?:certificate|policy|coverage|requirement)"
            r"|professional\s+indemnity|public\s+liability)\b"
            r".*\b(?:required|mandatory|shall\s+(?:be\s+)?(?:submit|provid|maintain))\b",
            re.IGNORECASE,
        ),
        "insurance_requirement",
    ),
    (
        re.compile(
            r"\b(?:local\s+(?:partner|agent|representative|presence)"
            r"|in-kingdom\s+(?:office|presence)|Saudi\s+agent)\b"
            r".*\b(?:required|mandatory|shall)\b",
            re.IGNORECASE,
        ),
        "local_presence",
    ),
    (
        re.compile(
            r"\b(?:ISO\s+\d{4,5}|certif(?:ied|ication)\s+(?:required|mandatory))\b"
            r".*\b(?:hold|possess|maintain|current|valid)\b",
            re.IGNORECASE,
        ),
        "certification_required",
    ),
    (
        re.compile(
            r"\b(?:Saudization\s+(?:ratio|percentage|requirement|target)"
            r"|Saudi\s+nationals?\s+(?:ratio|percentage|employed|requirement))\b"
            r".*\b(?:\d+%|required|mandatory|minimum)\b",
            re.IGNORECASE,
        ),
        "saudization_ratio",
    ),
]

# ---------------------------------------------------------------------------
# §5.3 — MEDIUM: Contract risk / post-award triggers (9 patterns)
# ---------------------------------------------------------------------------

MEDIUM_PATTERNS: list[tuple] = [
    (
        re.compile(
            r"\b(?:liquidated\s+damages|penalty\s+clause|delay\s+penalty)\b"
            r".*\b(?:\d+%|SAR|USD)\b",
            re.IGNORECASE,
        ),
        "liquidated_damages",
    ),
    (
        re.compile(
            r"\b(?:liability\s+(?:shall\s+be\s+)?(?:capped?\s+at|limited\s+to)"
            r"|cap\s+on\s+(?:total\s+)?liability|maximum\s+liability)\b"
            r".*\b(?:\d+%|SAR|USD|times?)\b",
            re.IGNORECASE,
        ),
        "liability_cap",
    ),
    (
        re.compile(
            r"\b(?:unlimited\s+liability|no\s+cap\s+on\s+liability|full\s+liability)\b",
            re.IGNORECASE,
        ),
        "unlimited_liability",
    ),
    (
        re.compile(
            r"\b(?:terminate\s+for\s+convenience|without\s+cause|at\s+any\s+time)\b",
            re.IGNORECASE,
        ),
        "termination_convenience",
    ),
    (
        re.compile(
            r"\b(?:all\s+intellectual\s+property|work\s+product\s+shall\s+belong"
            r"|assigns?\s+all\s+rights)\b",
            re.IGNORECASE,
        ),
        "ip_assignment",
    ),
    (
        re.compile(
            r"\b(?:payment\s+(?:milestone|schedule|upon\s+completion)"
            r"|progress\s+payment|milestone\s+payment)\b"
            r".*\b(?:\d+%|SAR|USD)\b",
            re.IGNORECASE,
        ),
        "payment_milestone",
    ),
    (
        re.compile(
            r"\b(?:warranty|defect(?:s)?\s+liability\s+period|guarantee\s+period)\b"
            r".*\b\d+\s+(?:year|month)s?\b",
            re.IGNORECASE,
        ),
        "warranty_period",
    ),
    (
        re.compile(
            r"\b(?:force\s+majeure|act\s+of\s+(?:God|nature)"
            r"|beyond\s+(?:(?:the\s+)?(?:reasonable\s+)?control))\b",
            re.IGNORECASE,
        ),
        "force_majeure",
    ),
    (
        re.compile(
            r"\b(?:right\s+to\s+audit|audit\s+rights?"
            r"|(?:client|company)\s+(?:shall\s+have\s+the\s+right\s+to\s+(?:audit|inspect)"
            r"|may\s+audit))\b",
            re.IGNORECASE,
        ),
        "audit_rights",
    ),
]


# ---------------------------------------------------------------------------
# Part B — Core functions
# ---------------------------------------------------------------------------

def _extract_dates(text: str) -> list[str]:
    date_matches: list[tuple[int, int, str]] = []
    for pattern in DATE_PATTERNS:
        for m in pattern.finditer(text):
            date_matches.append((m.start(), m.end(), m.group()))

    time_matches: list[tuple[int, int, str]] = [
        (m.start(), m.end(), m.group())
        for m in _TIME_PATTERN.finditer(text)
    ]

    used_time_indices: set[int] = set()
    seen: set[str] = set()
    results: list[str] = []

    for dstart, dend, dtext in date_matches:
        combined = dtext
        for ti, (tstart, tend, ttext) in enumerate(time_matches):
            if ti in used_time_indices:
                continue
            gap = min(abs(tstart - dend), abs(dstart - tend))
            if gap <= 30:
                combined = f"{dtext} {ttext}"
                used_time_indices.add(ti)
                break
        if combined not in seen:
            seen.add(combined)
            results.append(combined)

    return results


def _scan_pattern_group(
    text: str,
    patterns: list[tuple],
    severity: str,
) -> list[RiskFlag]:
    flags: list[RiskFlag] = []
    for compiled_re, label in patterns:
        match = compiled_re.search(text)
        if match:
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 80)
            context = text[start:end].strip()

            deadline = None
            if severity == "critical":
                dates = _extract_dates(context)
                deadline = dates[0] if dates else None

            flags.append(RiskFlag(
                flag=label,
                severity=severity,
                source=context,
                deadline=deadline,
                days_remaining=None,
            ))
    return flags


def detect_legal_traps(texts: dict[str, str]) -> list[RiskFlag]:
    all_flags: list[RiskFlag] = []
    for filename, text in texts.items():
        all_flags.extend(_scan_pattern_group(text, CRITICAL_PATTERNS, "critical"))
        all_flags.extend(_scan_pattern_group(text, HIGH_PATTERNS, "high"))
        all_flags.extend(_scan_pattern_group(text, MEDIUM_PATTERNS, "medium"))

    SEVERITY_RANK = {"critical": 3, "high": 2, "medium": 1}
    seen: dict[str, RiskFlag] = {}
    for flag in all_flags:
        if flag.flag not in seen or \
           SEVERITY_RANK[flag.severity] > SEVERITY_RANK[seen[flag.flag].severity]:
            seen[flag.flag] = flag

    return sorted(seen.values(), key=lambda f: SEVERITY_RANK[f.severity], reverse=True)
