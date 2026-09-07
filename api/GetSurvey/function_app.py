import azure.functions as func
import json
import logging
import os
import sys

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.fabric_connector import FabricLakehouseConnector

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get survey questions from Fabric Lakehouse
    GET /api/survey
    """
    logging.info('GetSurvey function triggered')
    
    try:
        # Initialize Fabric connector with service principal
        connector = FabricLakehouseConnector(
            server=os.getenv('FABRIC_SQL_SERVER'),
            database=os.getenv('FABRIC_LAKEHOUSE_NAME'),
            username=os.getenv('FABRIC_SQL_USER'),
            password=os.getenv('FABRIC_SQL_PASSWORD'),
            tenant_id=os.getenv('FABRIC_TENANT_ID')
        )
        
        if not connector.connect():
            return func.HttpResponse(
                json.dumps({'error': 'Cannot connect to Lakehouse'}),
                status_code=500,
                mimetype="application/json"
            )
        
        # Load questions from survey_questions table
        questions = connector.load_survey_questions('survey_questions')
        connector.disconnect()
        
        return func.HttpResponse(
            json.dumps({
                'questions': questions,
                'total': len(questions)
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error loading survey: {e}")
        return func.HttpResponse(
            json.dumps({'error': str(e)}),
            status_code=500,
            mimetype="application/json"
        )
