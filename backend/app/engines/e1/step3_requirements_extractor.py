import json
import os
import re

import anthropic

from .models import Requirement
from .step2_missing_docs import ARAMCO_STD_PATTERNS, INTL_STD_PATTERNS

# ---------------------------------------------------------------------------
# Patterns compiled at module load time — RFP_Compliance_Patterns.md §1
# ---------------------------------------------------------------------------

# §1.1 Mandatory indicators
MANDATORY_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bshall\b(?!\s+(?:not|neither))",          re.IGNORECASE),  # M1
    re.compile(r"\bmust\b(?!\s+(?:not|neither))",           re.IGNORECASE),  # M2
    re.compile(r"\b(?:is|are)\s+required\b",                re.IGNORECASE),  # M3a
    re.compile(r"\brequired\s+to\b",                        re.IGNORECASE),  # M3b
    re.compile(r"\b(?:mandatory|obligatory)\b",             re.IGNORECASE),  # M4
    re.compile(r"\bwill\s+be\s+disqualified\b",             re.IGNORECASE),  # M5a
    re.compile(r"\bfailure\s+to\s+comply\b",                re.IGNORECASE),  # M5b
    re.compile(r"\bshall\s+not\b",                          re.IGNORECASE),  # M6a
    re.compile(r"\bmust\s+not\b",                           re.IGNORECASE),  # M6b
    re.compile(r"\bis\s+prohibited\b",                      re.IGNORECASE),  # M6c
]

# §1.2 Optional indicators
OPTIONAL_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bshould\b",                               re.IGNORECASE),  # O1a
    re.compile(r"\bmay\b",                                  re.IGNORECASE),  # O1b
    re.compile(r"\b(?:recommended|preferred|desirable|optional)\b", re.IGNORECASE),  # O2
    re.compile(r"\bwhere\s+possible\b",                     re.IGNORECASE),  # O4a
    re.compile(r"\bif\s+feasible\b",                        re.IGNORECASE),  # O4b
    re.compile(r"\bwhen\s+practicable\b",                   re.IGNORECASE),  # O4c
]

# §1.3 Conditional indicators
CONDITIONAL_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bif\s+applicable\b",                      re.IGNORECASE),  # C1a
    re.compile(r"\bwhere\s+required\b",                     re.IGNORECASE),  # C1b
    re.compile(r"\bas\s+needed\b",                          re.IGNORECASE),  # C1c
    re.compile(r"\bat\b.{1,50}?\bdiscretion\b",            re.IGNORECASE),  # C2
    re.compile(r"\bunless\s+otherwise\b",                   re.IGNORECASE),  # C3
    re.compile(r"\bsubject\s+to\b",                         re.IGNORECASE),  # C4a
    re.compile(r"\bcontingent\s+upon\b",                    re.IGNORECASE),  # C4b
    re.compile(r"\bprovided\s+that\b",                      re.IGNORECASE),  # C4c
]

# §1.4 Compound sentence splitters (defined for future use; see §9.3 known limitations)
COMPOUND_SPLITTERS: list[re.Pattern] = [
    re.compile(r",?\s+\b(?:and|but|while|whereas|although|though|however)\b\s+",
               re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Part B — Pure-code extraction (~80% of requirements)
# ---------------------------------------------------------------------------

def _split_into_sentences(text: str) -> list[str]:
    sentences: list[str] = []

    # Split on newlines (handles numbered items, bullets, paragraph breaks)
    for line in re.split(r"\n+", text):
        line = line.strip()
        if not line:
            continue
        # Further split on sentence boundaries (. + space + capital)
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", line)
        for part in parts:
            part = part.strip()
            if len(part) >= 15:
                sentences.append(part)

    return sentences


def _score_sentence(sentence: str) -> dict:
    mandatory_hits = 0
    optional_hits = 0
    conditional_hits = 0
    indicators: list[str] = []

    for pattern in MANDATORY_PATTERNS:
        for match in pattern.finditer(sentence):
            mandatory_hits += 1
            indicators.append(match.group().lower().strip())

    for pattern in OPTIONAL_PATTERNS:
        for match in pattern.finditer(sentence):
            optional_hits += 1
            indicators.append(match.group().lower().strip())

    for pattern in CONDITIONAL_PATTERNS:
        for match in pattern.finditer(sentence):
            conditional_hits += 1
            indicators.append(match.group().lower().strip())

    # Deduplicate indicators, preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for ind in indicators:
        if ind not in seen:
            seen.add(ind)
            deduped.append(ind)

    return {
        "mandatory_hits": mandatory_hits,
        "optional_hits": optional_hits,
        "conditional_hits": conditional_hits,
        "indicators": deduped,
    }


def _classify_sentence(scores: dict) -> tuple[str, float] | None:
    if scores["mandatory_hits"] > 0:
        confidence = min(0.95, 0.7 + scores["mandatory_hits"] * 0.1)
        return ("mandatory", confidence)
    if scores["conditional_hits"] > 0:
        return ("conditional", 0.75)
    if scores["optional_hits"] > 0:
        return ("optional", 0.70)
    return None


def _extract_standard_refs(sentence: str) -> list[str]:
    found: set[str] = set()
    for pattern, _ in ARAMCO_STD_PATTERNS + INTL_STD_PATTERNS:
        for match in pattern.finditer(sentence):
            found.add(match.group().strip())
    return list(found)


def extract_requirements_from_text(
    text: str,
    source_file: str,
    opportunity_id: str,
) -> tuple[list[Requirement], list[str]]:
    high_conf: list[Requirement] = []
    ambiguous: list[str] = []
    counter = 1

    for sentence in _split_into_sentences(text):
        scores = _score_sentence(sentence)
        result = _classify_sentence(scores)
        if result is None:
            continue
        classification, confidence = result
        if confidence >= 0.70:
            high_conf.append(Requirement(
                id=f"R-{str(counter).zfill(3)}",
                text=sentence,
                classification=classification,
                confidence=confidence,
                source_file=source_file,
                page=0,
                indicators=scores["indicators"],
                section="",
                related_standards=_extract_standard_refs(sentence),
            ))
            counter += 1
        else:
            ambiguous.append(sentence)

    return high_conf, ambiguous


# ---------------------------------------------------------------------------
# Part C — AI call for ambiguous sentences (~20%)
# ---------------------------------------------------------------------------

def _classify_ambiguous_with_ai(
    sentences: list[str],
) -> list[tuple[str, str, float]]:
    if not sentences:
        return []

    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        prompt = (
            "You are classifying sentences from a MENA procurement RFP.\n"
            "Classify each sentence as: mandatory, optional, conditional, or not_a_requirement.\n\n"
            "Rules:\n"
            "- mandatory: vendor MUST do this, non-compliance risks disqualification\n"
            "- optional: vendor may do this, no penalty for not doing it\n"
            "- conditional: depends on context or client election\n"
            "- not_a_requirement: descriptive, informational, or about the client\n\n"
            "Return ONLY valid JSON array, no explanation:\n"
            '[{"sentence": "...", "classification": "mandatory", "confidence": 0.85}, ...]\n\n'
            f"Sentences to classify:\n{json.dumps(sentences, indent=2)}"
        )
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        items = json.loads(response.content[0].text)
        return [(item["classification"], item["sentence"], float(item["confidence"]))
                for item in items]
    except Exception as e:
        print(f"Warning: AI classification failed ({type(e).__name__}): {e}")
        return [("optional", s, 0.50) for s in sentences]


# ---------------------------------------------------------------------------
# Part D — Main orchestration
# ---------------------------------------------------------------------------

def extract_requirements(
    texts: dict[str, str],
    opportunity_id: str,
) -> list[Requirement]:
    all_requirements: list[Requirement] = []
    all_ambiguous: list[str] = []

    for filename, text in texts.items():
        high_conf, ambiguous = extract_requirements_from_text(
            text, filename, opportunity_id
        )
        all_requirements.extend(high_conf)
        all_ambiguous.extend(ambiguous)

    # Renumber IDs sequentially across all files
    for i, req in enumerate(all_requirements, 1):
        req.id = f"R-{str(i).zfill(3)}"

    # AI call for ambiguous sentences — one batched call across all files
    if all_ambiguous:
        ai_results = _classify_ambiguous_with_ai(all_ambiguous)
        for classification, sentence, confidence in ai_results:
            if classification == "not_a_requirement":
                continue
            counter = len(all_requirements) + 1
            all_requirements.append(Requirement(
                id=f"R-{str(counter).zfill(3)}",
                text=sentence,
                classification=classification,
                confidence=confidence,
                source_file="ai_classified",
                page=0,
                indicators=["ai_judgment"],
                section="",
                related_standards=_extract_standard_refs(sentence),
            ))

    return sorted(
        all_requirements,
        key=lambda r: (r.source_file, r.confidence),
        reverse=True,
    )
