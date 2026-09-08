import azure.functions as func
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock survey data for testing
MOCK_QUESTIONS = [
    {"question_id": "Q1", "question_text": "How satisfied are you with your job?", "answer_type": "likert", "answer_options": "[\"Very Dissatisfied\", \"Dissatisfied\", \"Neutral\", \"Satisfied\", \"Very Satisfied\"]", "is_required": True, "section": "Job Satisfaction", "sequence": 1, "created_at": "2024-01-01", "is_active": True, "parent_question_id": None, "show_if_answer": None, "branch_type": "parent"},
    {"question_id": "Q2", "question_text": "Do you have the tools you need to do your job?", "answer_type": "multiple_choice", "answer_options": "[\"Yes\", \"No\"]", "is_required": True, "section": "Resources", "sequence": 2, "created_at": "2024-01-01", "is_active": True, "parent_question_id": None, "show_if_answer": None, "branch_type": "parent"},
    {"question_id": "Q2a", "question_text": "What tools are missing?", "answer_type": "textarea", "answer_options": "[]", "is_required": False, "section": "Resources", "sequence": 3, "created_at": "2024-01-01", "is_active": True, "parent_question_id": "Q2", "show_if_answer": "No", "branch_type": "conditional"},
    {"question_id": "Q18", "question_text": "Have you experienced any workplace issues?", "answer_type": "multiple_choice", "answer_options": "[\"Yes\", \"No\"]", "is_required": True, "section": "Workplace Safety", "sequence": 10, "created_at": "2024-01-01", "is_active": True, "parent_question_id": None, "show_if_answer": None, "branch_type": "parent"},
    {"question_id": "Q18a", "question_text": "Describe the harassment or bullying:", "answer_type": "textarea", "answer_options": "[]", "is_required": False, "section": "Workplace Safety", "sequence": 11, "created_at": "2024-01-01", "is_active": True, "parent_question_id": "Q18", "show_if_answer": None, "branch_type": "always_show"},
    {"question_id": "Q18b", "question_text": "When did this occur?", "answer_type": "text", "answer_options": "[]", "is_required": False, "section": "Workplace Safety", "sequence": 12, "created_at": "2024-01-01", "is_active": True, "parent_question_id": "Q18", "show_if_answer": None, "branch_type": "always_show"},
    {"question_id": "Q18c", "question_text": "Who was involved?", "answer_type": "text", "answer_options": "[]", "is_required": False, "section": "Workplace Safety", "sequence": 13, "created_at": "2024-01-01", "is_active": True, "parent_question_id": "Q18", "show_if_answer": None, "branch_type": "always_show"},
    {"question_id": "Q22", "question_text": "Have you personally experienced physical violence at work?", "answer_type": "multiple_choice", "answer_options": "[\"Yes\", \"No\"]", "is_required": True, "section": "Workplace Safety", "sequence": 14, "created_at": "2024-01-01", "is_active": True, "parent_question_id": None, "show_if_answer": None, "branch_type": "parent"},
    {"question_id": "Q22a", "question_text": "When did this occur?", "answer_type": "text", "answer_options": "[]", "is_required": False, "section": "Workplace Safety", "sequence": 15, "created_at": "2024-01-01", "is_active": True, "parent_question_id": "Q22", "show_if_answer": "Yes", "branch_type": "conditional"},
    {"question_id": "Q22b", "question_text": "Where did this occur?", "answer_type": "text", "answer_options": "[]", "is_required": False, "section": "Workplace Safety", "sequence": 16, "created_at": "2024-01-01", "is_active": True, "parent_question_id": "Q22", "show_if_answer": "Yes", "branch_type": "conditional"},
]

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('GetSurvey function triggered')

    fabric_error = None

    try:
        from app.onelake_connector import OneLakeConnector
        connector = OneLakeConnector()

        if connector.is_configured():
            logging.info("OneLake configured — fetching survey_questions.json")
            questions = connector.load_survey_questions('survey_questions.json')
            if questions:
                logging.info(f"Loaded {len(questions)} questions from OneLake")
                return func.HttpResponse(
                    json.dumps({'questions': questions, 'total': len(questions), 'source': 'onelake'}),
                    status_code=200,
                    mimetype="application/json"
                )
            fabric_error = "OneLake returned 0 questions — check survey_questions.json exists in Lakehouse Files"
            logging.warning(fabric_error)
        else:
            fabric_error = "FABRIC_WORKSPACE_ID not set — add it in Azure portal environment variables"
            logging.info(fabric_error)

    except Exception as e:
        fabric_error = str(e)
        logging.warning(f"OneLake error: {e}")

    # Fallback: return mock data so the UI still works during setup
    logging.info(f"Using mock data. Reason: {fabric_error}")
    return func.HttpResponse(
        json.dumps({
            'questions': MOCK_QUESTIONS,
            'total': len(MOCK_QUESTIONS),
            'source': 'mock',
            'connection_error': fabric_error
        }),
        status_code=200,
        mimetype="application/json"
    )
