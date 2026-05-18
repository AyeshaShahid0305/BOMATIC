from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RFIQuestion:
    id: str                    # e.g. "RFI-001"
    category: str              # e.g. "Network", "Security", "Commercial"
    question: str
    rationale: str             # why this question is being asked
    priority: str              # "must_have", "nice_to_have"
    expected_answer_type: str  # "text", "number", "yes_no", "attachment"


@dataclass
class RFIQuestionnaire:
    project_name: str
    generated_from: str        # "rfp_gaps" or "blank"
    questions: List[RFIQuestion] = field(default_factory=list)
    total_questions: int = 0
    categories: List[str] = field(default_factory=list)
