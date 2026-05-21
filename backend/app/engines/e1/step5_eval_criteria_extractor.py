import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

_WEIGHT_RE = re.compile(r'(\d{1,3})\s*%')

_CRITERIA_KEYWORDS = [
    'evaluation criteria', 'scoring criteria', 'award criteria', 'selection criteria',
    'evaluation factor', 'weighted criteria', 'technical score', 'commercial score',
    'price weight', 'quality weight', 'pass/fail', 'pass or fail', 'mandatory pass',
    'minimum score', 'qualifying criteria', 'evaluation methodology',
    'معايير التقييم', 'معايير الترسية', 'نقاط التقييم',
]

_SECTION_HEADERS = re.compile(
    r'(evaluation\s+criter|scoring\s+criter|award\s+criter|selection\s+criter'
    r'|evaluation\s+factor|weighted\s+scoring|technical\s+evaluation)',
    re.IGNORECASE,
)


def _extract_weight(text: str) -> Optional[float]:
    match = _WEIGHT_RE.search(text)
    if match:
        val = float(match.group(1))
        if 0 < val <= 100:
            return val
    return None


def extract_evaluation_criteria(texts: dict[str, str]) -> list[dict]:
    criteria: list[dict] = []
    seen: set[str] = set()
    for filename, text in texts.items():
        lines = text.splitlines()
        in_criteria_section = False
        section_buffer: list[str] = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            if _SECTION_HEADERS.search(stripped):
                in_criteria_section = True
                section_buffer = []
                continue
            if in_criteria_section:
                if len(section_buffer) > 30:
                    in_criteria_section = False
                    section_buffer = []
                    continue
                section_buffer.append(stripped)
                weight = _extract_weight(stripped)
                key = stripped[:80].lower()
                if weight is not None and key not in seen:
                    seen.add(key)
                    criteria.append({
                        'criterion': stripped,
                        'weight': weight,
                        'category': _classify_criterion(stripped),
                        'pass_fail': _is_pass_fail(stripped),
                        'source_file': filename,
                    })
                continue
            lower = stripped.lower()
            if any(kw in lower for kw in _CRITERIA_KEYWORDS):
                weight = _extract_weight(stripped)
                key = stripped[:80].lower()
                if key not in seen:
                    seen.add(key)
                    criteria.append({
                        'criterion': stripped,
                        'weight': weight,
                        'category': _classify_criterion(stripped),
                        'pass_fail': _is_pass_fail(stripped),
                        'source_file': filename,
                    })
    total_weight = sum(c['weight'] for c in criteria if c['weight'] is not None)
    if criteria:
        logger.info('Extracted %d evaluation criteria; total declared weight: %.0f%%', len(criteria), total_weight)
    return criteria


def _classify_criterion(text: str) -> str:
    lower = text.lower()
    if any(w in lower for w in ['technical', 'solution', 'architecture', 'design', 'approach']):
        return 'technical'
    if any(w in lower for w in ['commercial', 'price', 'cost', 'financial', 'pricing']):
        return 'commercial'
    if any(w in lower for w in ['compliance', 'standard', 'certification', 'iso', 'nca']):
        return 'compliance'
    if any(w in lower for w in ['experience', 'reference', 'past', 'track record']):
        return 'experience'
    return 'general'


def _is_pass_fail(text: str) -> bool:
    lower = text.lower()
    return any(w in lower for w in ['pass/fail', 'pass or fail', 'mandatory pass', 'qualifying', 'go/no-go'])
