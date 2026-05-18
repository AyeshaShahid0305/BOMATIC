from .models import RFIQuestion, RFIQuestionnaire

_PRIORITY_ORDER = {"must_have": 0, "nice_to_have": 1}


def assemble_questionnaire(questions: list[RFIQuestion], context: dict) -> RFIQuestionnaire:
    sorted_questions = sorted(
        questions,
        key=lambda q: (_PRIORITY_ORDER.get(q.priority, 99), q.category),
    )

    categories = sorted({q.category for q in sorted_questions})

    return RFIQuestionnaire(
        project_name=context["project_name"],
        generated_from="rfp_gaps" if context["has_e1_data"] else "blank",
        questions=sorted_questions,
        total_questions=len(sorted_questions),
        categories=categories,
    )
