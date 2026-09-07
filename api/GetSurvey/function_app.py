import azure.functions as func
import json
import logging
import os
import sys

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

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
    """
    Get survey questions from Fabric Lakehouse (or mock data for testing)
    GET /api/survey
    """
    logging.info('GetSurvey function triggered')
    
    try:
        # Log environment variable status
        has_fabric_server = bool(os.getenv('FABRIC_SQL_SERVER'))
        logging.info(f"Fabric SQL Server configured: {has_fabric_server}")
        
        # Check if Fabric connection is available
        if has_fabric_server:
            try:
                logging.info("Attempting Fabric connection...")
                from app.fabric_connector import FabricLakehouseConnector
                
                server = os.getenv('FABRIC_SQL_SERVER')
                database = os.getenv('FABRIC_LAKEHOUSE_NAME')
                username = os.getenv('FABRIC_SQL_USER')
                tenant_id = os.getenv('FABRIC_TENANT_ID')
                
                logging.info(f"Connecting to Fabric: {server}/{database}")
                
                connector = FabricLakehouseConnector(
                    server=server,
                    database=database,
                    username=username,
                    password=os.getenv('FABRIC_SQL_PASSWORD'),
                    tenant_id=tenant_id
                )
                
                if connector.connect():
                    logging.info("Successfully connected to Fabric")
                    questions = connector.load_survey_questions('survey_questions')
                    connector.disconnect()
                    logging.info(f"Loaded {len(questions)} questions from Fabric")
                    
                    return func.HttpResponse(
                        json.dumps({
                            'questions': questions,
                            'total': len(questions),
                            'source': 'fabric'
                        }),
                        status_code=200,
                        mimetype="application/json"
                    )
                else:
                    logging.warning("Failed to connect to Fabric, using mock data")
            except ImportError as e:
                logging.warning(f"Could not import FabricLakehouseConnector: {e}")
            except Exception as e:
                logging.warning(f"Fabric connection error: {e}")
        else:
            logging.info("Fabric SQL Server not configured")
        
        # Return mock data for testing
        logging.info(f"Using mock survey data ({len(MOCK_QUESTIONS)} questions)")
        return func.HttpResponse(
            json.dumps({
                'questions': MOCK_QUESTIONS,
                'total': len(MOCK_QUESTIONS),
                'source': 'mock'
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Unexpected error loading survey: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({'error': str(e)}),
            status_code=500,
            mimetype="application/json"
        )
