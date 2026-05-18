from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from .step1_context_reader import read_context
from .step2_question_generator import generate_questions
from .step3_assembler import assemble_questionnaire
from .step4_xlsx_writer import write_questionnaire


def run_e4_pipeline(session_id: Optional[str], db: Session) -> dict:
    context = read_context(session_id, db)
    questions = generate_questions(context)
    questionnaire = assemble_questionnaire(questions, context)
    output_path = write_questionnaire(questionnaire)

    return {
        "output_file": Path(output_path).name,
        "project_name": questionnaire.project_name,
        "total_questions": questionnaire.total_questions,
        "categories": questionnaire.categories,
        "generated_from": questionnaire.generated_from,
        "must_have_count": sum(1 for q in questionnaire.questions if q.priority == "must_have"),
        "nice_to_have_count": sum(1 for q in questionnaire.questions if q.priority == "nice_to_have"),
    }
