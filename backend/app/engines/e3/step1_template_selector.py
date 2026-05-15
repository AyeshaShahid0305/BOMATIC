from .models import ProposalSection

# 15-entry TP structure from playbook §6.1.
# required=False: sections that are conditional (managed services, RFP-only, optional appendices).
# ai_generated=True: executive summary, understanding of requirements, proposed solution —
#   the three Opus narrative calls defined in the runtime architecture.
_SECTIONS: list[ProposalSection] = [
    ProposalSection(id=0,  title="Cover Page",                              required=True,  ai_generated=False),
    ProposalSection(id=1,  title="Cover Letter / Introduction",             required=True,  ai_generated=False),
    ProposalSection(id=2,  title="Executive Summary",                       required=True,  ai_generated=True),
    ProposalSection(id=3,  title="Understanding of Customer Requirements",  required=True,  ai_generated=True),
    ProposalSection(id=4,  title="Proposed Solution",                       required=True,  ai_generated=True),
    ProposalSection(id=5,  title="Technical Specifications",                required=True,  ai_generated=False),
    ProposalSection(id=6,  title="Implementation Approach",                 required=True,  ai_generated=False),
    ProposalSection(id=7,  title="Service Levels & Support",                required=False, ai_generated=False),
    ProposalSection(id=8,  title="Commercial Proposal",                     required=True,  ai_generated=False),
    ProposalSection(id=9,  title="Scope, Assumptions, Exclusions, Dependencies", required=True, ai_generated=False),
    ProposalSection(id=10, title="Compliance Matrix",                       required=False, ai_generated=False),
    ProposalSection(id=11, title="References / Case Studies",               required=False, ai_generated=False),
    ProposalSection(id=12, title="Company Profile",                         required=True,  ai_generated=False),
    ProposalSection(id=13, title="Appendices",                              required=False, ai_generated=False),
    ProposalSection(id=14, title="Signature Page",                          required=True,  ai_generated=False),
]


def select_template(project_type: str) -> list[ProposalSection]:
    return list(_SECTIONS)


if __name__ == "__main__":
    sections = select_template("rfp")
    for s in sections:
        ai_tag = " [AI]" if s.ai_generated else ""
        req_tag = "" if s.required else " [optional]"
        print(f"  {s.id:>2}. {s.title}{ai_tag}{req_tag}")
