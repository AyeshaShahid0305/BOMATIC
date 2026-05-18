from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DesignSection:
    id: str
    title: str
    content: str
    level: str   # "HLD" or "LLD"
    order: int


@dataclass
class DesignDocument:
    project_name: str
    hld_sections: List[DesignSection] = field(default_factory=list)
    lld_sections: List[DesignSection] = field(default_factory=list)
    topology_description: str = ""
    generated_from: str = "e1"   # "e1" or "e4"
