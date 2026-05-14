from dataclasses import dataclass, field
from typing import List, Literal, Optional


@dataclass
class Classification:
    type: str
    subtype: str
    confidence: float
    stage_used: str
    needs_human_review: bool = False
    can_auto_process: bool = True


@dataclass
class MissingDocument:
    referenced_doc: str
    referenced_in: str
    page: int
    line: str
    severity: Literal["critical", "high", "medium", "low"]
    action: str


@dataclass
class Requirement:
    id: str
    text: str
    classification: Literal["mandatory", "optional", "conditional"]
    confidence: float
    source_file: str
    page: int
    indicators: List[str] = field(default_factory=list)
    section: str = ""
    related_standards: List[str] = field(default_factory=list)


@dataclass
class RiskFlag:
    flag: str
    severity: Literal["critical", "high", "medium"]
    source: str
    deadline: Optional[str] = None
    days_remaining: Optional[int] = None


@dataclass
class ComplianceRow:
    req_id: str
    req_text: str
    classification: str
    framework: str
    control_id: str
    control_name: str
    status: Literal["Compliant", "Partial", "Non-Compliant", "Alternative"]
    tp_section: str
    notes: str = ""
    gap_type: Literal["none", "coverage_gap", "orphan"] = "none"


@dataclass
class E1Output:
    opportunity_id: str
    total_requirements: int
    mandatory: int
    optional: int
    conditional: int
    sector: str
    frameworks: List[str] = field(default_factory=list)
    requirements: List[Requirement] = field(default_factory=list)
    missing_docs: List[MissingDocument] = field(default_factory=list)
    risk_flags: List[RiskFlag] = field(default_factory=list)
    compliance_rows: List[ComplianceRow] = field(default_factory=list)
