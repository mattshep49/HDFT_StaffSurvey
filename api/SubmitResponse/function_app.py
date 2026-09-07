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
    Submit survey responses
    POST /api/submit-response
    Body: {token: string, responses: object}
    """
    logging.info('SubmitResponse function triggered')
    
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({'error': 'Invalid request body'}),
            status_code=400,
            mimetype="application/json"
        )
    
    token = req_body.get('token')
    responses = req_body.get('responses')
    
    if not token or not responses:
        return func.HttpResponse(
            json.dumps({'error': 'Token and responses required'}),
            status_code=400,
            mimetype="application/json"
        )
    
    # Handle test token for development
    if token == 'test':
        token_data = {
            'token_id': 1,
            'assignment_number': 'TEST-001',
            'staff_id': 'test-staff',
            'staff_name': 'Test User',
            'department': 'Testing'
        }
    else:
        # For non-test tokens, reject for now (token database not implemented)
        return func.HttpResponse(
            json.dumps({'error': 'Invalid or expired token. Use token=test for development.'}),
            status_code=401,
            mimetype="application/json"
        )
    
    try:
        # Save to Fabric Lakehouse
        connector = FabricLakehouseConnector(
            server=os.getenv('FABRIC_SQL_SERVER'),
            database=os.getenv('FABRIC_LAKEHOUSE_NAME'),
            username=os.getenv('FABRIC_SQL_USER'),
            password=os.getenv('FABRIC_SQL_PASSWORD'),
            tenant_id=os.getenv('FABRIC_TENANT_ID')
        )
        
        if connector.connect():
            response_id = connector.save_survey_response(
                token_id=token_data.get('token_id'),
                assignment_number=token_data.get('assignment_number'),
                staff_id=token_data.get('staff_id'),
                responses=responses
            )
            connector.disconnect()
            
            logging.info(f"Response submitted for {token_data.get('assignment_number')}")
            
            return func.HttpResponse(
                json.dumps({
                    'success': True,
                    'message': 'Thank you for completing the survey',
                    'response_id': response_id
                }),
                status_code=200,
                mimetype="application/json"
            )
        else:
            return func.HttpResponse(
                json.dumps({'error': 'Cannot save response'}),
                status_code=500,
                mimetype="application/json"
            )
            
    except Exception as e:
        logging.error(f"Error submitting response: {e}")
        return func.HttpResponse(
            json.dumps({'error': str(e)}),
            status_code=500,
            mimetype="application/json"
        )
