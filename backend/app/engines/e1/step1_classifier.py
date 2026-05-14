import re
from pathlib import Path

from .extractors import extract_text
from .models import Classification

# Extensions that cannot be opened or parsed — classify from filename only.
CANNOT_AUTO_PROCESS = {".dwg", ".vsdx", ".rvt", ".nwc", ".ifc", ".msg", ".eml"}

# ---------------------------------------------------------------------------
# All patterns compiled at module load time from RFP_Compliance_Patterns.md
# ---------------------------------------------------------------------------

PATTERNS: dict = {

    # §3 — Filename classification patterns
    # Each entry: type, subtype, confidence, patterns (list of compiled re)
    "filename": [
        {
            "type": "compliance", "subtype": "cybersecurity_standard", "confidence": 0.97,
            "patterns": [re.compile(r"SACS-|SAES-|CAP-\d|GI-\d", re.IGNORECASE)],
        },
        {
            "type": "commercial", "subtype": "boq_template", "confidence": 0.93,
            "patterns": [re.compile(r"\bBOQ\b|BoQ|pricing|bill.of.quantities", re.IGNORECASE)],
        },
        {
            "type": "legal", "subtype": "nda", "confidence": 0.92,
            "patterns": [re.compile(r"\bNDA\b|confidential|non.disclosure", re.IGNORECASE)],
        },
        {
            "type": "legal", "subtype": "bid_bond", "confidence": 0.95,
            "patterns": [re.compile(r"bid.bond|bank.guarantee|performance.bond", re.IGNORECASE)],
        },
        {
            "type": "admin", "subtype": "certificate", "confidence": 0.88,
            "patterns": [re.compile(r"\bCR\b|commercial.registr|ZATCA|\bVAT\b", re.IGNORECASE)],
        },
        {
            "type": "commercial", "subtype": "evaluation_criteria", "confidence": 0.90,
            "patterns": [re.compile(r"evaluation|questionnaire|scoring|\bTEQ\b", re.IGNORECASE)],
        },
        {
            "type": "legal", "subtype": "terms", "confidence": 0.93,
            "patterns": [re.compile(r"T&C|terms.and.conditions|\bGTC\b", re.IGNORECASE)],
        },
        {
            "type": "technical", "subtype": "requirements", "confidence": 0.85,
            "patterns": [re.compile(r"(?<![a-zA-Z])scope(?![a-zA-Z])|\bSOW\b|requirements|specification", re.IGNORECASE)],
        },
        {
            "type": "technical", "subtype": "engineering_drawing", "confidence": 0.91,
            "patterns": [re.compile(r"drawing|\.dwg|\.vsdx|riser|layout|floor.plan", re.IGNORECASE)],
        },
        {
            "type": "compliance", "subtype": "local_content", "confidence": 0.94,
            "patterns": [re.compile(r"local.content|IKTVA|Saudization", re.IGNORECASE)],
        },
        {
            "type": "correspondence", "subtype": "email", "confidence": 0.85,
            "patterns": [re.compile(r"\.msg$|\.eml$|clarification|addendum|amendment", re.IGNORECASE)],
        },
    ],

    # §6 — Folder classification patterns
    # Evaluated in order; first match wins. "technical" is last (catch-all).
    "folder": [
        {
            "type": "commercial", "subtype": "", "confidence": 0.78,
            "patterns": [re.compile(r"BOQ|pricing|commercial|financial", re.IGNORECASE)],
        },
        {
            "type": "legal", "subtype": "", "confidence": 0.80,
            "patterns": [re.compile(r"legal|NDA|contract|agreement", re.IGNORECASE)],
        },
        {
            "type": "compliance", "subtype": "", "confidence": 0.80,
            "patterns": [re.compile(r"compliance|security|standards|cybersecurity", re.IGNORECASE)],
        },
        {
            "type": "admin", "subtype": "", "confidence": 0.75,
            "patterns": [re.compile(r"submittal|certificate|admin", re.IGNORECASE)],
        },
        {
            "type": "technical", "subtype": "", "confidence": 0.72,
            "patterns": [re.compile(r"RFQ|RFP|document|tender", re.IGNORECASE)],
        },
    ],

    # §7 — Content keyword patterns
    # keywords: list of individually compiled patterns; each match counts +1.
    # Scoring per §9.3: each matched keyword adds 0.2; min_matches gates return.
    "content": [
        {
            "type": "technical", "subtype": "requirements",
            "keywords": [
                re.compile(r"shall comply", re.IGNORECASE),
                re.compile(r"mandatory", re.IGNORECASE),
                re.compile(r"disqualif", re.IGNORECASE),
                re.compile(r"failure to", re.IGNORECASE),
                re.compile(r"required", re.IGNORECASE),
            ],
            "min_matches": 2, "confidence": 0.70,
        },
        {
            "type": "commercial", "subtype": "pricing",
            "keywords": [
                re.compile(r"unit price", re.IGNORECASE),
                re.compile(r"total price", re.IGNORECASE),
                re.compile(r"\bqty\b", re.IGNORECASE),
                re.compile(r"amount.{0,20}(?:SAR|USD)", re.IGNORECASE),
                re.compile(r"\bSAR\b.{0,20}total", re.IGNORECASE),
            ],
            "min_matches": 2, "confidence": 0.72,
        },
        {
            "type": "legal", "subtype": "general",
            "keywords": [
                re.compile(r"whereas", re.IGNORECASE),
                re.compile(r"hereby agrees", re.IGNORECASE),
                re.compile(r"indemnify", re.IGNORECASE),
                re.compile(r"\bliability\b", re.IGNORECASE),
                re.compile(r"jurisdiction", re.IGNORECASE),
                re.compile(r"governing law", re.IGNORECASE),
            ],
            "min_matches": 2, "confidence": 0.75,
        },
        {
            "type": "compliance", "subtype": "cybersecurity",
            "keywords": [
                re.compile(r"cybersecurity", re.IGNORECASE),
                re.compile(r"access control", re.IGNORECASE),
                re.compile(r"encryption", re.IGNORECASE),
                re.compile(r"vulnerability", re.IGNORECASE),
                re.compile(r"\bNCA\b", re.IGNORECASE),
                re.compile(r"ISO 27001", re.IGNORECASE),
            ],
            "min_matches": 2, "confidence": 0.72,
        },
        {
            "type": "admin", "subtype": "certificate",
            "keywords": [
                re.compile(r"authorized signatory", re.IGNORECASE),
                re.compile(r"chamber of commerce", re.IGNORECASE),
                re.compile(r"registration number", re.IGNORECASE),
                re.compile(r"ZATCA", re.IGNORECASE),
            ],
            "min_matches": 2, "confidence": 0.75,
        },
    ],
}


# ---------------------------------------------------------------------------
# Stage functions
# ---------------------------------------------------------------------------

def _stage1_filename(filename: str) -> Classification | None:
    stem = Path(filename).name  # strip any folder prefix
    for entry in PATTERNS["filename"]:
        if any(p.search(stem) for p in entry["patterns"]):
            if entry["confidence"] >= 0.8:
                return Classification(
                    type=entry["type"],
                    subtype=entry["subtype"],
                    confidence=entry["confidence"],
                    stage_used="filename",
                )
    return None


def _stage2_folder(folder_path: str) -> Classification | None:
    folder_lower = folder_path.lower()
    for entry in PATTERNS["folder"]:
        if any(p.search(folder_lower) for p in entry["patterns"]):
            if entry["confidence"] >= 0.7:
                return Classification(
                    type=entry["type"],
                    subtype=entry["subtype"],
                    confidence=entry["confidence"],
                    stage_used="folder",
                )
    return None


def _stage3_content(file_path: str | Path, filename: str) -> Classification:
    result = extract_text(file_path)

    if result.get("error") == "cannot_auto_process":
        return Classification(
            type="unknown",
            subtype="",
            confidence=0.0,
            stage_used="content",
            needs_human_review=True,
            can_auto_process=False,
        )

    text = result.get("text", "")[:2000]

    best: Classification | None = None
    for entry in PATTERNS["content"]:
        count = sum(1 for kw in entry["keywords"] if kw.search(text))
        if count >= entry["min_matches"]:
            candidate = Classification(
                type=entry["type"],
                subtype=entry["subtype"],
                confidence=entry["confidence"],
                stage_used="content",
            )
            if best is None or candidate.confidence > best.confidence:
                best = candidate

    if best is not None:
        return best

    return Classification(
        type="unknown",
        subtype="unclassified",
        confidence=0.3,
        stage_used="content",
        needs_human_review=True,
        can_auto_process=True,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def classify_file(
    filename: str,
    folder_path: str = "",
    file_path: str | Path | None = None,
) -> Classification:
    ext = Path(filename).suffix.lower()

    # CANNOT_AUTO_PROCESS: classify from filename only, mark unprocessable
    if ext in CANNOT_AUTO_PROCESS:
        result = _stage1_filename(filename)
        if result:
            result.can_auto_process = False
            return result
        if ext in {".msg", ".eml"}:
            return Classification(
                type="correspondence",
                subtype="email",
                confidence=0.70,
                stage_used="filename",
                can_auto_process=False,
                needs_human_review=True,
            )
        subtype = "engineering_drawing" if ext in {".dwg", ".vsdx"} else "unknown"
        return Classification(
            type="technical",
            subtype=subtype,
            confidence=0.85,
            stage_used="filename",
            can_auto_process=False,
        )

    # Stage 1 — filename
    result = _stage1_filename(filename)
    if result and result.confidence >= 0.8:
        return result

    # Stage 2 — folder
    if folder_path:
        result = _stage2_folder(folder_path)
        if result and result.confidence >= 0.7:
            return result

    # Stage 3 — content
    if file_path:
        return _stage3_content(file_path, filename)

    # No file_path provided; stages 1 and 2 both fell below threshold
    return Classification(
        type="unknown",
        subtype="unclassified",
        confidence=0.4,
        stage_used="filename",
        needs_human_review=True,
    )
